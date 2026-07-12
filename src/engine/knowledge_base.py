"""
Base de conocimiento en memoria — carga toda la configuración de clasificación
al arrancar y la mantiene en RAM con refresco periódico.

Con 1250 proveedores y 500+ facturas/día, hacer queries a BD por cada clasificación
es el principal cuello de botella. Esta clase carga todo una vez y sirve desde RAM.

Memoria estimada: ~5-15 MB para toda la configuración (insignificante en 8GB RAM).
"""
import logging
import threading
import time
import psycopg2.extras
from typing import Dict, List, Optional, Set, Tuple
from ..database import db

logger = logging.getLogger(__name__)

# Refresco automático cada 10 minutos
REFRESH_INTERVAL_SECONDS = 600


class KnowledgeBase:
    """
    Singleton que mantiene en RAM toda la configuración de clasificación.
    Thread-safe con RLock para lecturas concurrentes.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def initialize(self):
        """Carga inicial desde BD. Llamar una vez al arrancar la app."""
        if self._initialized:
            return
        self._rlock = threading.RLock()
        self._load_all()
        self._initialized = True
        self._start_refresh_thread()
        logger.info("KnowledgeBase inicializada correctamente")

    # ─────────────────────────────────────────────────────────────────────────
    # ACCESO A DATOS (thread-safe, desde RAM)
    # ─────────────────────────────────────────────────────────────────────────

    def get_proveedor_config(self, proveedor_id: int) -> Optional[Dict]:
        """Retorna config OCR del proveedor desde RAM."""
        with self._rlock:
            return self._proveedor_config.get(proveedor_id)

    def get_proveedor_by_nit(self, nit: str) -> Optional[Dict]:
        """Busca proveedor por NIT (limpio, solo dígitos)."""
        nit_limpio = ''.join(c for c in str(nit) if c.isdigit())
        with self._rlock:
            return self._proveedores_by_nit.get(nit_limpio)

    def get_unidad_keywords(self, unidad_id: int) -> List[Tuple[str, float]]:
        """Retorna lista de (keyword, peso) para una unidad funcional."""
        with self._rlock:
            return self._unidad_keywords.get(unidad_id, [])

    def get_sucursal_keywords(self, sucursal_id: int) -> List[Tuple[str, float]]:
        """Retorna lista de (keyword, peso) para una sucursal."""
        with self._rlock:
            return self._sucursal_keywords.get(sucursal_id, [])

    def get_all_unidad_keywords(self) -> Dict[int, List[Tuple[str, float]]]:
        """Retorna todas las keywords de todas las unidades."""
        with self._rlock:
            return dict(self._unidad_keywords)

    def get_all_sucursal_keywords(self) -> Dict[int, List[Tuple[str, float]]]:
        """Retorna todas las keywords de todas las sucursales."""
        with self._rlock:
            return dict(self._sucursal_keywords)

    def get_sucursal(self, sucursal_id: int) -> Optional[Dict]:
        with self._rlock:
            return self._sucursales.get(sucursal_id)

    def get_sucursal_by_codigo(self, codigo: str) -> Optional[Dict]:
        with self._rlock:
            return self._sucursales_by_codigo.get(codigo.upper())

    def get_unidad(self, unidad_id: int) -> Optional[Dict]:
        with self._rlock:
            return self._unidades.get(unidad_id)

    def get_unidades_by_sucursal(self, sucursal_id: int) -> List[Dict]:
        with self._rlock:
            return self._unidades_by_sucursal.get(sucursal_id, [])

    def get_all_unidades(self) -> List[Dict]:
        with self._rlock:
            return list(self._unidades.values())

    def get_unidades_by_empresa(self, empresa_id: int) -> List[Dict]:
        """Retorna solo las UFs de una empresa específica."""
        with self._rlock:
            return [u for u in self._unidades.values() if u.get('empresa_id') == empresa_id]

    def get_sucursales_by_empresa(self, empresa_id: int) -> List[Dict]:
        """Retorna solo las sucursales de una empresa específica."""
        with self._rlock:
            return [s for s in self._sucursales.values() if s.get('empresa_id') == empresa_id]

    def get_unidad_keywords_by_empresa(self, empresa_id: int) -> Dict[int, List]:
        """Retorna keywords solo de las UFs que pertenecen a una empresa."""
        with self._rlock:
            ufs_empresa = {u['id'] for u in self._unidades.values() if u.get('empresa_id') == empresa_id}
            return {uid: kws for uid, kws in self._unidad_keywords.items() if uid in ufs_empresa}

    def get_reglas(self, sucursal_id: Optional[int] = None, empresa_id: Optional[int] = None) -> List[Dict]:
        """
        Retorna reglas de clasificación filtradas por sucursal y/o empresa.
        
        Lógica multi-empresa:
        - empresa_id=None → devuelve todas las reglas (globales + específicas)
        - empresa_id=1    → devuelve reglas globales (empresa_id IS NULL) + reglas de empresa 1
        - Las reglas específicas de empresa tienen prioridad sobre las globales
        """
        with self._rlock:
            reglas = list(self._reglas)
            
            # Filtrar por empresa: incluir globales (NULL) + las de la empresa específica
            if empresa_id is not None:
                reglas = [
                    r for r in reglas
                    if r.get('empresa_id') is None or r.get('empresa_id') == empresa_id
                ]
                # Ordenar: reglas específicas de empresa primero, luego globales
                reglas.sort(key=lambda r: (
                    0 if r.get('empresa_id') == empresa_id else 1,
                    -(r.get('prioridad') or 0)
                ))
            
            # Filtrar por sucursal si se especifica
            if sucursal_id:
                reglas = [r for r in reglas if r.get('sucursal_id') == sucursal_id or not r.get('sucursal_id')]
            
            return reglas

    def get_sinonimos(self) -> List[Dict]:
        with self._rlock:
            return list(self._sinonimos)

    def get_stats(self) -> Dict:
        with self._rlock:
            return {
                'proveedores': len(self._proveedores_by_nit),
                'proveedores_con_config': len(self._proveedor_config),
                'sucursales': len(self._sucursales),
                'unidades': len(self._unidades),
                'unidad_keywords_total': sum(len(v) for v in self._unidad_keywords.values()),
                'sucursal_keywords_total': sum(len(v) for v in self._sucursal_keywords.values()),
                'reglas': len(self._reglas),
                'sinonimos': len(self._sinonimos),
                'last_refresh': self._last_refresh,
            }

    def invalidate(self):
        """Fuerza recarga inmediata (llamar después de aprender nuevas keywords)."""
        logger.info("KnowledgeBase: invalidación forzada")
        self._load_all()

    # ─────────────────────────────────────────────────────────────────────────
    # CARGA DESDE BD
    # ─────────────────────────────────────────────────────────────────────────

    def _load_all(self):
        """Carga todo desde BD en una sola transacción."""
        try:
            with db.get_connection() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                sucursales = self._load_sucursales(cur)
                unidades = self._load_unidades(cur)
                unidad_kw = self._load_unidad_keywords(cur)
                sucursal_kw = self._load_sucursal_keywords(cur)
                proveedores, prov_nit = self._load_proveedores(cur)
                prov_config = self._load_proveedor_config(cur)
                reglas = self._load_reglas(cur)
                sinonimos = self._load_sinonimos(cur)
                cur.close()

            with self._rlock if hasattr(self, '_rlock') else threading.RLock():
                self._sucursales = sucursales['by_id']
                self._sucursales_by_codigo = sucursales['by_codigo']
                self._unidades = unidades['by_id']
                self._unidades_by_sucursal = unidades['by_sucursal']
                self._unidad_keywords = unidad_kw
                self._sucursal_keywords = sucursal_kw
                self._proveedores_by_nit = prov_nit
                self._proveedor_config = prov_config
                self._reglas = reglas
                self._sinonimos = sinonimos
                self._last_refresh = time.strftime('%Y-%m-%d %H:%M:%S')

            stats = self.get_stats()
            logger.info(
                f"KnowledgeBase cargada: {stats['proveedores']} proveedores, "
                f"{stats['unidades']} unidades, "
                f"{stats['unidad_keywords_total']} keywords unidad, "
                f"{stats['reglas']} reglas"
            )
        except Exception as e:
            logger.error(f"Error cargando KnowledgeBase: {e}")
            # Inicializar vacío para no romper la app
            if not hasattr(self, '_sucursales'):
                self._sucursales = {}
                self._sucursales_by_codigo = {}
                self._unidades = {}
                self._unidades_by_sucursal = {}
                self._unidad_keywords = {}
                self._sucursal_keywords = {}
                self._proveedores_by_nit = {}
                self._proveedor_config = {}
                self._reglas = []
                self._sinonimos = []
                self._last_refresh = 'error'

    def _load_sucursales(self, cur) -> Dict:
        cur.execute("""
            SELECT id, nombre, codigo, empresa_id, activo
            FROM sucursales WHERE activo = TRUE
        """)
        by_id, by_codigo = {}, {}
        for row in cur.fetchall():
            d = dict(row)
            by_id[d['id']] = d
            by_codigo[d['codigo'].upper()] = d
        return {'by_id': by_id, 'by_codigo': by_codigo}

    def _load_unidades(self, cur) -> Dict:
        cur.execute("""
            SELECT id, nombre, codigo, sucursal_id, empresa_id, activo
            FROM unidades_funcionales WHERE activo = TRUE
        """)
        by_id, by_sucursal = {}, {}
        for row in cur.fetchall():
            d = dict(row)
            by_id[d['id']] = d
            by_sucursal.setdefault(d['sucursal_id'], []).append(d)
        return {'by_id': by_id, 'by_sucursal': by_sucursal}

    def _load_unidad_keywords(self, cur) -> Dict[int, List[Tuple[str, float]]]:
        cur.execute("""
            SELECT unidad_funcional_id, keyword, peso
            FROM ocr_unidad_keywords
            WHERE activo = TRUE
            ORDER BY peso DESC
        """)
        result: Dict[int, List] = {}
        for row in cur.fetchall():
            uid = row['unidad_funcional_id']
            result.setdefault(uid, []).append((row['keyword'].upper(), float(row['peso'])))
        return result

    def _load_sucursal_keywords(self, cur) -> Dict[int, List[Tuple[str, float]]]:
        cur.execute("""
            SELECT sucursal_id, keyword, peso
            FROM ocr_sucursal_keywords
            WHERE activo = TRUE
            ORDER BY peso DESC
        """)
        result: Dict[int, List] = {}
        for row in cur.fetchall():
            sid = row['sucursal_id']
            result.setdefault(sid, []).append((row['keyword'].upper(), float(row['peso'])))
        return result

    def _load_proveedores(self, cur) -> Tuple[Dict, Dict]:
        cur.execute("""
            SELECT id, nit, razon_social, nombre_comercial, activo
            FROM proveedores WHERE activo = TRUE
        """)
        by_nit = {}
        by_id = {}
        for row in cur.fetchall():
            d = dict(row)
            nit_limpio = ''.join(c for c in str(d['nit'] or '') if c.isdigit())
            if nit_limpio:
                by_nit[nit_limpio] = d
            by_id[d['id']] = d
        return by_id, by_nit

    def _load_proveedor_config(self, cur) -> Dict[int, Dict]:
        try:
            cur.execute("""
                SELECT proveedor_id, tipo_clasificacion, prioridad_clasificacion,
                       unidades_funcionales_ids, alias, activo
                FROM ocr_proveedor_config WHERE activo = TRUE
            """)
            result = {}
            for row in cur.fetchall():
                result[row['proveedor_id']] = dict(row)
            return result
        except Exception as e:
            logger.warning(f"No se pudo cargar ocr_proveedor_config: {e}")
            return {}

    def _load_reglas(self, cur) -> List[Dict]:
        try:
            cur.execute("""
                SELECT r.id, r.nombre, r.tipo_regla, r.condicion, r.accion,
                       r.prioridad, r.activo,
                       r.empresa_id,
                       uf.id   AS unidad_funcional_id,
                       uf.nombre AS unidad_nombre,
                       uf.codigo AS unidad_codigo,
                       s.id    AS sucursal_id,
                       s.nombre AS sucursal_nombre
                FROM ocr_reglas_clasificacion r
                LEFT JOIN unidades_funcionales uf
                       ON uf.id = (r.accion->>'unidad_funcional_id')::int
                LEFT JOIN sucursales s
                       ON s.id = (r.accion->>'sucursal_id')::int
                WHERE r.activo = TRUE
                ORDER BY r.prioridad DESC
            """)
            return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.warning(f"No se pudo cargar ocr_reglas_clasificacion: {e}")
            return []

    def _load_sinonimos(self, cur) -> List[Dict]:
        try:
            cur.execute("""
                SELECT tipo, palabra_original, sinonimo, peso
                FROM ocr_sinonimos WHERE activo = TRUE
            """)
            return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.warning(f"No se pudo cargar ocr_sinonimos: {e}")
            return []

    def _start_refresh_thread(self):
        """Hilo daemon que refresca la KB cada REFRESH_INTERVAL_SECONDS."""
        def _refresh_loop():
            while True:
                time.sleep(REFRESH_INTERVAL_SECONDS)
                try:
                    logger.debug("KnowledgeBase: refresco automático")
                    self._load_all()
                except Exception as e:
                    logger.error(f"Error en refresco automático: {e}")

        t = threading.Thread(target=_refresh_loop, daemon=True)
        t.start()


# Instancia global
kb = KnowledgeBase()
