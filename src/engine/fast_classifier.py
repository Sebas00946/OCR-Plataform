"""
Clasificador rápido que opera 100% desde RAM (KnowledgeBase).
Sin queries a BD durante la clasificación — todo precargado.

Diseñado para 500+ facturas/día con 1250 proveedores.
Tiempo estimado por clasificación: < 5ms (vs ~200ms con queries a BD).

Cascada de decisión:
  1. Regla exacta por NIT (ocr_reglas_clasificacion)
  2. Config de proveedor (ocr_proveedor_config)
  3. Scoring de keywords (ocr_unidad_keywords)
  4. Fallback por tipo de proveedor (nombre del proveedor)
"""
import logging
import re
import time
from typing import Dict, List, Optional, Tuple

from .knowledge_base import kb

logger = logging.getLogger(__name__)

# Keywords de medicamentos/insumos para detección rápida
_KW_ALMACEN: List[str] = [
    'MEDICAMENTO', 'INSUMO', 'FARMACO', 'FARMACEUTICO', 'SUSPENSION',
    'TABLETA', 'CAPSULA', 'AMPOLLA', 'JERINGA', 'CATETER', 'SUERO',
    'SOLUCION', 'INYECTABLE', 'CREMA', 'GEL', 'MATERIAL QUIRURGICO',
    'MATERIAL DE CURACION', 'DISPOSITIVO MEDICO', 'GUANTE', 'GASA',
    'VENDA', 'ESPARADRAPO', 'OXCARBAZEPINA', 'IBUPROFENO', 'ACETAMINOFEN',
    'AMOXICILINA', 'METFORMINA', 'LOSARTAN', 'ATORVASTATINA', 'OMEPRAZOL',
    'DROGUERIA', 'FARMACIA', 'FARMAQUIRURGICO',
]

_KW_ADMIN: List[str] = [
    'SERVICIO', 'MANTENIMIENTO', 'CONTRATO', 'HONORARIO', 'CONSULTORIA',
    'TELECOMUNICACION', 'INTERNET', 'TELEFONIA', 'ENERGIA', 'AGUA',
    'GAS', 'ACUEDUCTO', 'VIGILANCIA', 'ASEO', 'LIMPIEZA', 'ARRENDAMIENTO',
    'PAPELERIA', 'PUBLICIDAD', 'TRANSPORTE', 'MENSAJERIA',
]

# Mapeo de código interno (Note XML) a código de sucursal en BD
_NOTE_CODIGO_MAP: Dict[str, str] = {
    'NVA': 'NVA', 'TJA': 'TJA', 'FLA': 'FLA', 'PTO': 'PTO',
    'BOG': 'BOG', 'FAC': 'FAC', 'DUI': 'DUI', 'KTA': 'KTA',
    'EAL': 'EAL', 'DTA': 'DTA', 'MOC': 'MOC', 'CMI': 'CMI',
    # Variantes comunes en notas de proveedores
    'NEIVA': 'NVA', 'TUNJA': 'TJA', 'FLORENCIA': 'FLA',
    'PITALITO': 'PTO', 'BOGOTA': 'BOG', 'FACATATIVA': 'KTA',
    'DUITAMA': 'DTA', 'MOCOA': 'MOC', 'CAJICA': 'EAL',
    # Códigos de almacén de Farmaquirurgicos
    'NVA MED': 'NVA', 'TJA MED': 'TJA', 'FLO MED': 'FLA',
    'PTO MED': 'PTO', 'KTA MED': 'KTA', 'EAL MED': 'EAL',
    'DTA MED': 'DTA', 'CMI MED': 'CMI',
}


class FastClassifier:
    """
    Clasificador sin queries a BD. Opera desde KnowledgeBase en RAM.
    Thread-safe (solo lectura de estructuras inmutables durante clasificación).
    """

    def classify(self, xml_data: Dict, pdf_text: str, empresa_id: int = 1) -> Tuple[Dict, Dict]:
        """
        Clasifica una factura.

        Args:
            xml_data: {'proveedor': {...}, 'factura': {...}, 'cliente': {...}}
            pdf_text: Texto extraído del PDF (mayúsculas)
            empresa_id: ID de la empresa para filtrar reglas (default=1 Medilaser)

        Returns:
            (sucursal_result, unidad_result)
        """
        t0 = time.monotonic()

        proveedor = xml_data.get('proveedor', {}) or {}
        factura = xml_data.get('factura', {}) or {}
        cliente = xml_data.get('cliente', {}) or {}

        nit = ''.join(c for c in str(proveedor.get('nit', '')) if c.isdigit())
        note = factura.get('note', '') or factura.get('notas', '') or ''
        ciudad = (cliente.get('ciudad', '') or '').upper().strip()
        
        # Notas específicas del XML (Sucursal/Almacén de proveedores como Farmaquirurgicos)
        sucursal_nota = factura.get('sucursal_nota', '') or ''
        almacen_nota = factura.get('almacen_nota', '') or ''

        # Texto combinado para scoring — incluir notas del XML
        texto = pdf_text or ''
        if sucursal_nota:
            texto = f"{sucursal_nota} {texto}"
        if almacen_nota:
            texto = f"{almacen_nota} {texto}"

        # ── Paso 1: Identificar sucursal ──────────────────────────────────
        # Pasar también las notas específicas para mejor detección
        note_completo = note
        if sucursal_nota:
            note_completo = f"{note_completo} | {sucursal_nota}"
        if almacen_nota:
            note_completo = f"{note_completo} | {almacen_nota}"
        sucursal = self._detectar_sucursal(note_completo, ciudad, texto)

        # ── Paso 2: Regla exacta por NIT ─────────────────────────────────
        if nit:
            regla = self._aplicar_regla_nit(nit, sucursal, texto, empresa_id)
            if regla:
                # Si la regla define sucursal_id, usar esa sucursal
                regla_sucursal_id = regla.get('sucursal_id')
                if regla_sucursal_id and regla_sucursal_id != sucursal.get('id'):
                    suc_data = kb.get_sucursal(regla_sucursal_id)
                    if suc_data:
                        sucursal = self._sucursal_ok(suc_data, 'regla_nit', 1.0)
                
                ms = (time.monotonic() - t0) * 1000
                logger.debug(f"FastClassifier: regla NIT en {ms:.1f}ms -> {regla.get('nombre')}")
                return sucursal, regla

        # ── Paso 3: Config de proveedor ───────────────────────────────────
        if nit:
            config_result = self._clasificar_por_config(nit, sucursal)
            if config_result:
                ms = (time.monotonic() - t0) * 1000
                logger.debug(f"FastClassifier: config proveedor en {ms:.1f}ms → {config_result.get('nombre')}")
                return sucursal, config_result

        # ── Paso 4: Scoring de keywords ───────────────────────────────────
        kw_result = self._clasificar_por_keywords(texto, sucursal)
        if kw_result and kw_result.get('score', 0) >= 15:
            ms = (time.monotonic() - t0) * 1000
            logger.debug(f"FastClassifier: keywords en {ms:.1f}ms → {kw_result.get('nombre')} score={kw_result.get('score')}")
            return sucursal, kw_result

        # ── Paso 5: Fallback por nombre del proveedor ─────────────────────
        fallback = self._fallback_por_proveedor(proveedor, sucursal, texto)
        ms = (time.monotonic() - t0) * 1000
        logger.debug(f"FastClassifier: fallback en {ms:.1f}ms → {fallback.get('nombre')}")
        return sucursal, fallback

    # ─────────────────────────────────────────────────────────────────────────
    # DETECCIÓN DE SUCURSAL
    # ─────────────────────────────────────────────────────────────────────────

    def _detectar_sucursal(self, note: str, ciudad: str, texto: str) -> Dict:
        """Detecta sucursal con prioridad: Note XML > Ciudad > Texto."""

        # Estrategia 1: Note XML (más confiable — ej: "OC118055-NVA")
        if note:
            codigo = self._extraer_codigo_de_note(note)
            if codigo:
                sucursal = kb.get_sucursal_by_codigo(codigo)
                if sucursal:
                    return self._sucursal_ok(sucursal, 'note_xml', 0.98)

        # Estrategia 2: Ciudad del cliente en XML
        if ciudad:
            codigo = self._ciudad_a_codigo(ciudad)
            if codigo:
                sucursal = kb.get_sucursal_by_codigo(codigo)
                if sucursal:
                    return self._sucursal_ok(sucursal, 'ciudad_xml', 0.95)

        # Estrategia 3: Keywords de sucursal en texto (desde BD)
        mejor_sucursal_id, mejor_score = None, 0.0
        for sid, keywords in kb.get_all_sucursal_keywords().items():
            score = sum(peso for kw, peso in keywords if kw in texto)
            if score > mejor_score:
                mejor_score = score
                mejor_sucursal_id = sid

        if mejor_sucursal_id and mejor_score >= 5:
            sucursal = kb.get_sucursal(mejor_sucursal_id)
            if sucursal:
                return self._sucursal_ok(sucursal, 'keywords_texto', 0.80)

        return {'success': False, 'id': None, 'nombre': None, 'score': 0, 'keywords': []}

    def _extraer_codigo_de_note(self, note: str) -> Optional[str]:
        """Extrae código de sucursal del campo Note. Ej: 'OC118055-CENV36828-NVA' → 'NVA'"""
        note_upper = note.upper()
        # El código suele estar al final
        partes = note_upper.split('-')
        for parte in reversed(partes):
            parte = parte.strip()
            if parte in _NOTE_CODIGO_MAP:
                return _NOTE_CODIGO_MAP[parte]
        # Buscar en cualquier posición
        for codigo in _NOTE_CODIGO_MAP:
            if re.search(rf'\b{codigo}\b', note_upper):
                return _NOTE_CODIGO_MAP[codigo]
        return None

    def _ciudad_a_codigo(self, ciudad: str) -> Optional[str]:
        """Mapea nombre de ciudad a código de sucursal."""
        mapa = {
            'NEIVA': 'NVA', 'TUNJA': 'TJA', 'FLORENCIA': 'FLA',
            'PITALITO': 'PTO', 'BOGOTA': 'BOG', 'BOGOTÁ': 'BOG',
            'FACATATIVA': 'FAC', 'FACATATIVÁ': 'FAC',
            'DUITAMA': 'DUI', 'CARTAGENA': 'KTA',
        }
        return mapa.get(ciudad.upper())

    # ─────────────────────────────────────────────────────────────────────────
    # REGLAS EXACTAS
    # ─────────────────────────────────────────────────────────────────────────

    def _aplicar_regla_nit(self, nit: str, sucursal: Dict, texto: str = '', empresa_id: int = 1) -> Optional[Dict]:
        """
        Aplica reglas de ocr_reglas_clasificacion.
        Las reglas tienen máxima prioridad — son configuradas manualmente.
        
        Soporta dos tipos de condición:
        - Simple: {"nit": "900433437"} → aplica siempre para ese NIT
        - Con keyword: {"nit": "900433437", "sucursal_keyword": "FLORENCIA"} → aplica si keyword está en texto
        - Fallback: {"nit": "900433437"} + accion.es_fallback → aplica si ninguna keyword matcheó
        
        Filtra por empresa_id: incluye reglas globales (NULL) + reglas de la empresa específica.
        """
        # Obtener reglas filtradas por empresa (globales + específicas de esta empresa)
        todas_reglas = kb.get_reglas(empresa_id=empresa_id)
        
        # Filtrar reglas de este NIT
        reglas_nit = []
        for regla in todas_reglas:
            condicion = regla.get('condicion') or {}
            if isinstance(condicion, str):
                import json
                try:
                    condicion = json.loads(condicion)
                except Exception:
                    condicion = {}
            
            nit_regla = ''.join(c for c in str(condicion.get('nit', '')) if c.isdigit())
            if nit_regla and nit_regla == nit:
                reglas_nit.append({**regla, '_condicion': condicion})
        
        if not reglas_nit:
            return None
        
        texto_upper = texto.upper() if texto else ''
        
        # PASO 1: Buscar reglas con sucursal_keyword (prioridad alta)
        for regla in reglas_nit:
            condicion = regla['_condicion']
            keyword = condicion.get('sucursal_keyword', '').strip()
            
            if not keyword:
                continue  # Es regla sin keyword (fallback), se evalúa después
            
            if keyword.upper() in texto_upper:
                unidad_id = regla.get('unidad_funcional_id')
                if not unidad_id:
                    continue
                
                unidad = kb.get_unidad(unidad_id)
                if unidad:
                    logger.info(
                        f"Regla NIT+keyword: NIT={nit} keyword='{keyword}' → {unidad['nombre']} "
                        f"(regla_id={regla.get('id')}, prioridad={regla.get('prioridad')})"
                    )
                    return {
                        'success': True,
                        'id': unidad['id'],
                        'nombre': unidad['nombre'],
                        'codigo': unidad['codigo'],
                        'sucursal_id': unidad['sucursal_id'],
                        'score': regla.get('prioridad', 150) * 10,
                        'confidence': 1.0,
                        'method': 'regla_nit_keyword',
                        'keywords': [f"regla_id={regla.get('id')}", f"keyword={keyword}"]
                    }
        
        # PASO 2: Buscar reglas simples (sin keyword, sin fallback)
        for regla in reglas_nit:
            condicion = regla['_condicion']
            accion = regla.get('accion') or {}
            if isinstance(accion, str):
                import json
                try:
                    accion = json.loads(accion)
                except Exception:
                    accion = {}
            
            # Saltar si tiene keyword (ya se evaluó arriba)
            if condicion.get('sucursal_keyword'):
                continue
            # Saltar si es fallback explícito
            if accion.get('es_fallback'):
                continue
            
            unidad_id = regla.get('unidad_funcional_id')
            if not unidad_id:
                continue
            
            unidad = kb.get_unidad(unidad_id)
            if unidad:
                logger.info(f"Regla NIT simple: NIT={nit} → {unidad['nombre']} (regla_id={regla.get('id')})")
                return {
                    'success': True,
                    'id': unidad['id'],
                    'nombre': unidad['nombre'],
                    'codigo': unidad['codigo'],
                    'sucursal_id': unidad['sucursal_id'],
                    'score': 1000,
                    'confidence': 1.0,
                    'method': 'regla_exacta',
                    'keywords': [f"regla_id={regla.get('id')}"]
                }
        
        # PASO 3: Fallback (prioridad baja, solo si nada más matcheó)
        for regla in reglas_nit:
            condicion = regla['_condicion']
            accion = regla.get('accion') or {}
            if isinstance(accion, str):
                import json
                try:
                    accion = json.loads(accion)
                except Exception:
                    accion = {}
            
            if not accion.get('es_fallback') and condicion.get('sucursal_keyword'):
                continue
            
            if accion.get('es_fallback'):
                unidad_id = regla.get('unidad_funcional_id')
                if not unidad_id:
                    continue
                
                unidad = kb.get_unidad(unidad_id)
                if unidad:
                    logger.info(f"Regla NIT fallback: NIT={nit} → {unidad['nombre']} (regla_id={regla.get('id')})")
                    return {
                        'success': True,
                        'id': unidad['id'],
                        'nombre': unidad['nombre'],
                        'codigo': unidad['codigo'],
                        'sucursal_id': unidad['sucursal_id'],
                        'score': regla.get('prioridad', 50) * 10,
                        'confidence': 0.7,
                        'method': 'regla_nit_fallback',
                        'keywords': [f"regla_id={regla.get('id')}", "fallback"]
                    }
        
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # CONFIG DE PROVEEDOR
    # ─────────────────────────────────────────────────────────────────────────

    def _clasificar_por_config(self, nit: str, sucursal: Dict) -> Optional[Dict]:
        """
        Usa ocr_proveedor_config para clasificar.
        Si el proveedor tiene unidades configuradas, elige la que coincide con la sucursal.
        """
        proveedor = kb.get_proveedor_by_nit(nit)
        if not proveedor:
            return None

        config = kb.get_proveedor_config(proveedor['id'])
        if not config:
            return None

        unidades_ids = config.get('unidades_funcionales_ids') or []
        if not unidades_ids:
            return None

        sucursal_id = sucursal.get('id')

        # Priorizar unidades de la sucursal detectada
        candidatas = []
        for uid in unidades_ids:
            if isinstance(uid, dict):
                uid = uid.get('unidad_id') or uid.get('id')
            if not uid:
                continue
            unidad = kb.get_unidad(int(uid))
            if unidad:
                candidatas.append(unidad)

        if not candidatas:
            return None

        # Elegir la que coincide con la sucursal
        if sucursal_id:
            for unidad in candidatas:
                if unidad['sucursal_id'] == sucursal_id:
                    return self._unidad_ok(unidad, 'proveedor_config_sucursal', 0.95)

        # Si no hay match de sucursal, usar la primera configurada
        return self._unidad_ok(candidatas[0], 'proveedor_config_general', 0.85)

    # ─────────────────────────────────────────────────────────────────────────
    # SCORING DE KEYWORDS (desde RAM)
    # ─────────────────────────────────────────────────────────────────────────

    def _clasificar_por_keywords(self, texto: str, sucursal: Dict) -> Optional[Dict]:
        """
        Calcula score de keywords para cada unidad funcional.
        Opera 100% desde RAM — sin queries a BD.
        """
        if not texto:
            return None

        sucursal_id = sucursal.get('id')
        all_keywords = kb.get_all_unidad_keywords()

        mejor_score = 0.0
        mejor_unidad_id = None
        mejor_keywords = []

        # Si tenemos sucursal, solo evaluar unidades de esa sucursal
        if sucursal_id:
            unidades_ids = {u['id'] for u in kb.get_unidades_by_sucursal(sucursal_id)}
        else:
            unidades_ids = set(all_keywords.keys())

        for uid in unidades_ids:
            keywords = all_keywords.get(uid, [])
            if not keywords:
                continue

            score = 0.0
            matched = []
            for kw, peso in keywords:
                if kw in texto:
                    score += peso
                    matched.append(kw)

            if score > mejor_score:
                mejor_score = score
                mejor_unidad_id = uid
                mejor_keywords = matched

        if not mejor_unidad_id:
            return None

        unidad = kb.get_unidad(mejor_unidad_id)
        if not unidad:
            return None

        return {
            'success': True,
            'id': unidad['id'],
            'nombre': unidad['nombre'],
            'codigo': unidad['codigo'],
            'sucursal_id': unidad['sucursal_id'],
            'score': mejor_score,
            'confidence': min(mejor_score / 100, 1.0),
            'method': 'keywords_ram',
            'keywords': mejor_keywords[:10]
        }

    # ─────────────────────────────────────────────────────────────────────────
    # FALLBACK POR TIPO DE PROVEEDOR
    # ─────────────────────────────────────────────────────────────────────────

    def _fallback_por_proveedor(self, proveedor: Dict, sucursal: Dict, texto: str) -> Dict:
        """
        Último recurso: detecta tipo por nombre del proveedor + contenido del texto.
        ALMACEN para medicamentos/insumos, ADMINISTRACION para servicios.
        """
        nombre_proveedor = (proveedor.get('nombre') or proveedor.get('razon_social') or '').upper()
        texto_upper = texto.upper()

        score_almacen = sum(1 for kw in _KW_ALMACEN if kw in texto_upper or kw in nombre_proveedor)
        score_admin = sum(1 for kw in _KW_ADMIN if kw in texto_upper or kw in nombre_proveedor)

        tipo_preferido = 'ALMAC' if score_almacen >= score_admin else 'ADMINISTRACI'
        keywords_detectadas = (
            [kw for kw in _KW_ALMACEN if kw in texto_upper][:3]
            if tipo_preferido == 'ALMAC'
            else [kw for kw in _KW_ADMIN if kw in texto_upper][:3]
        )

        sucursal_id = sucursal.get('id')
        unidades = kb.get_unidades_by_sucursal(sucursal_id) if sucursal_id else kb.get_all_unidades()

        # Buscar unidad del tipo preferido
        for unidad in unidades:
            if tipo_preferido in unidad['nombre'].upper():
                return {
                    'success': True,
                    'id': unidad['id'],
                    'nombre': unidad['nombre'],
                    'codigo': unidad['codigo'],
                    'sucursal_id': unidad['sucursal_id'],
                    'score': max(score_almacen, score_admin) * 5,
                    'confidence': 0.4,
                    'method': 'fallback_tipo_proveedor',
                    'keywords': keywords_detectadas or ['[FALLBACK]']
                }

        # Si no hay ninguna, usar la primera disponible
        if unidades:
            u = unidades[0]
            return {
                'success': True,
                'id': u['id'], 'nombre': u['nombre'], 'codigo': u['codigo'],
                'sucursal_id': u['sucursal_id'], 'score': 1,
                'confidence': 0.2, 'method': 'fallback_primera_unidad',
                'keywords': ['[SIN MATCH]']
            }

        return {'success': False, 'id': None, 'nombre': None, 'score': 0, 'keywords': []}

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _sucursal_ok(self, sucursal: Dict, method: str, confidence: float) -> Dict:
        return {
            'success': True,
            'id': sucursal['id'],
            'nombre': sucursal['nombre'],
            'codigo': sucursal['codigo'],
            'score': confidence * 100,
            'confidence': confidence,
            'method': method,
            'keywords': []
        }

    def _unidad_ok(self, unidad: Dict, method: str, confidence: float) -> Dict:
        return {
            'success': True,
            'id': unidad['id'],
            'nombre': unidad['nombre'],
            'codigo': unidad['codigo'],
            'sucursal_id': unidad['sucursal_id'],
            'score': confidence * 100,
            'confidence': confidence,
            'method': method,
            'keywords': []
        }


# Instancia global
fast_classifier = FastClassifier()
