"""
Clasificador Probabilístico Bayesiano para OCR.

Este clasificador aprende P(unidad | keywords, proveedor, ciudad) desde el historial
de clasificaciones validadas. Usa matemática probabilística en lugar de scoring simple.

Ventajas sobre keyword scoring:
- Aprende de correcciones históricas reales
- Considera contexto completo (proveedor + ciudad + keywords)
- Maneja proveedores que van a diferentes unidades según ciudad
- Actualización incremental sin reentrenamiento completo

Fórmula Bayesiana:
P(unidad | features) ∝ P(features | unidad) × P(unidad)

Donde features = {proveedor_nit, ciudad, keywords_presentes}
"""
import logging
import math
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict, Counter
import psycopg2.extras

from .database import db
from .engine.knowledge_base import kb

logger = logging.getLogger(__name__)


class ProbabilisticClassifier:
    """
    Clasificador bayesiano que aprende probabilidades desde el historial.
    
    Mantiene en memoria:
    - P(unidad) — probabilidad a priori de cada unidad
    - P(keyword | unidad) — probabilidad de cada keyword dada una unidad
    - P(proveedor | unidad) — probabilidad de proveedor dada una unidad
    - P(ciudad | unidad) — probabilidad de ciudad dada una unidad
    - P(proveedor, ciudad | unidad) — probabilidad conjunta (para proveedores multi-ciudad)
    """
    
    def __init__(self):
        self.loaded = False
        self.priors = {}  # P(unidad)
        self.keyword_likelihoods = defaultdict(lambda: defaultdict(float))  # P(kw | unidad)
        self.proveedor_likelihoods = defaultdict(lambda: defaultdict(float))  # P(prov | unidad)
        self.ciudad_likelihoods = defaultdict(lambda: defaultdict(float))  # P(ciudad | unidad)
        self.proveedor_ciudad_likelihoods = defaultdict(lambda: defaultdict(float))  # P(prov,ciudad | unidad)
        
        # Contadores para actualización incremental
        self.unidad_counts = Counter()
        self.total_samples = 0
        
        # Suavizado de Laplace (evita probabilidades cero)
        self.alpha = 0.1
        
    def load_from_history(self, limit: int = 10000):
        """
        Carga probabilidades desde ocr_clasificacion_historial.
        Solo usa registros validados (clasificacion_correcta = TRUE o con corrección manual).
        """
        logger.info("Cargando historial de clasificaciones para entrenamiento bayesiano...")
        
        with db.get_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Obtener clasificaciones validadas
            cur.execute("""
                SELECT 
                    COALESCE(h.unidad_correcta_id, h.unidad_funcional_detectada_id) as unidad_id,
                    COALESCE(h.sucursal_correcta_id, h.sucursal_detectada_id) as sucursal_id,
                    h.proveedor_detectado_id,
                    h.keywords_encontradas,
                    h.datos_extraidos
                FROM ocr_clasificacion_historial h
                WHERE 
                    (h.clasificacion_correcta = TRUE OR h.unidad_correcta_id IS NOT NULL)
                    AND h.unidad_funcional_detectada_id IS NOT NULL
                ORDER BY h.created_at DESC
                LIMIT %s
            """, (limit,))
            
            registros = cur.fetchall()
            cur.close()
            
        if not registros:
            logger.warning("No hay historial de clasificaciones validadas para entrenar")
            return
        
        # Procesar cada registro
        for reg in registros:
            unidad_id = reg['unidad_id']
            if not unidad_id:
                continue
                
            self.unidad_counts[unidad_id] += 1
            self.total_samples += 1
            
            # Extraer features
            proveedor_id = reg['proveedor_detectado_id']
            keywords_json = reg['keywords_encontradas'] or {}
            datos = reg['datos_extraidos'] or {}
            
            # Extraer ciudad del XML
            ciudad = None
            if isinstance(datos, dict):
                xml_data = datos.get('xml_data', {})
                if isinstance(xml_data, dict):
                    cliente = xml_data.get('cliente', {})
                    if isinstance(cliente, dict):
                        ciudad = (cliente.get('ciudad') or '').upper().strip()
            
            # Actualizar contadores de keywords
            keywords_unidad = keywords_json.get('unidad', [])
            if isinstance(keywords_unidad, list):
                for kw in keywords_unidad:
                    if isinstance(kw, str):
                        self.keyword_likelihoods[unidad_id][kw.upper()] += 1
            
            # Actualizar contadores de proveedor
            if proveedor_id:
                self.proveedor_likelihoods[unidad_id][proveedor_id] += 1
                
                # Actualizar proveedor + ciudad (clave para multi-ciudad)
                if ciudad:
                    key = f"{proveedor_id}:{ciudad}"
                    self.proveedor_ciudad_likelihoods[unidad_id][key] += 1
            
            # Actualizar contadores de ciudad
            if ciudad:
                self.ciudad_likelihoods[unidad_id][ciudad] += 1
        
        # Calcular probabilidades a priori
        for unidad_id, count in self.unidad_counts.items():
            self.priors[unidad_id] = count / self.total_samples
        
        # Normalizar likelihoods (convertir conteos a probabilidades)
        self._normalize_likelihoods()
        
        self.loaded = True
        logger.info(
            f"Clasificador probabilístico entrenado: {len(registros)} muestras, "
            f"{len(self.priors)} unidades, "
            f"{sum(len(v) for v in self.keyword_likelihoods.values())} keywords únicas"
        )
    
    def _normalize_likelihoods(self):
        """Convierte conteos a probabilidades con suavizado de Laplace."""
        # Keywords
        for unidad_id in self.keyword_likelihoods:
            total = sum(self.keyword_likelihoods[unidad_id].values())
            vocab_size = len(self.keyword_likelihoods[unidad_id])
            for kw in self.keyword_likelihoods[unidad_id]:
                count = self.keyword_likelihoods[unidad_id][kw]
                # Suavizado de Laplace
                self.keyword_likelihoods[unidad_id][kw] = (
                    (count + self.alpha) / (total + self.alpha * vocab_size)
                )
        
        # Proveedores
        for unidad_id in self.proveedor_likelihoods:
            total = sum(self.proveedor_likelihoods[unidad_id].values())
            vocab_size = len(self.proveedor_likelihoods[unidad_id])
            for prov_id in self.proveedor_likelihoods[unidad_id]:
                count = self.proveedor_likelihoods[unidad_id][prov_id]
                self.proveedor_likelihoods[unidad_id][prov_id] = (
                    (count + self.alpha) / (total + self.alpha * vocab_size)
                )
        
        # Ciudades
        for unidad_id in self.ciudad_likelihoods:
            total = sum(self.ciudad_likelihoods[unidad_id].values())
            vocab_size = len(self.ciudad_likelihoods[unidad_id])
            for ciudad in self.ciudad_likelihoods[unidad_id]:
                count = self.ciudad_likelihoods[unidad_id][ciudad]
                self.ciudad_likelihoods[unidad_id][ciudad] = (
                    (count + self.alpha) / (total + self.alpha * vocab_size)
                )
        
        # Proveedor + Ciudad
        for unidad_id in self.proveedor_ciudad_likelihoods:
            total = sum(self.proveedor_ciudad_likelihoods[unidad_id].values())
            vocab_size = len(self.proveedor_ciudad_likelihoods[unidad_id])
            for key in self.proveedor_ciudad_likelihoods[unidad_id]:
                count = self.proveedor_ciudad_likelihoods[unidad_id][key]
                self.proveedor_ciudad_likelihoods[unidad_id][key] = (
                    (count + self.alpha) / (total + self.alpha * vocab_size)
                )
    
    def classify(
        self,
        xml_data: Dict,
        pdf_text: str,
        proveedor_id: Optional[int] = None,
        sucursal_id: Optional[int] = None
    ) -> Tuple[Optional[int], float, Dict]:
        """
        Clasifica usando inferencia bayesiana.
        
        Returns:
            (unidad_id, confidence, debug_info)
        """
        if not self.loaded:
            logger.warning("Clasificador probabilístico no entrenado, cargando...")
            self.load_from_history()
        
        if not self.priors:
            logger.warning("No hay datos de entrenamiento, no se puede clasificar")
            return None, 0.0, {'error': 'sin_entrenamiento'}
        
        # Extraer features
        proveedor = xml_data.get('proveedor', {}) or {}
        factura = xml_data.get('factura', {}) or {}
        cliente = xml_data.get('cliente', {}) or {}
        
        nit = ''.join(c for c in str(proveedor.get('nit', '')) if c.isdigit())
        ciudad = (cliente.get('ciudad', '') or '').upper().strip()
        texto_upper = (pdf_text or '').upper()
        
        # Obtener proveedor_id si no se pasó
        if not proveedor_id and nit:
            prov = kb.get_proveedor_by_nit(nit)
            if prov:
                proveedor_id = prov['id']
        
        # Extraer keywords presentes en el texto
        keywords_presentes = self._extract_keywords_from_text(texto_upper)
        
        # Calcular log-probabilidad para cada unidad
        log_probs = {}
        debug_info = defaultdict(dict)
        
        # Filtrar unidades por sucursal si se especificó
        unidades_candidatas = (
            [u['id'] for u in kb.get_unidades_by_sucursal(sucursal_id)]
            if sucursal_id
            else list(self.priors.keys())
        )
        
        for unidad_id in unidades_candidatas:
            if unidad_id not in self.priors:
                continue
            
            # Log-probabilidad a priori
            log_prob = math.log(self.priors[unidad_id])
            debug_info[unidad_id]['prior'] = self.priors[unidad_id]
            
            # Log-likelihood de proveedor + ciudad (más específico)
            if proveedor_id and ciudad:
                key = f"{proveedor_id}:{ciudad}"
                if key in self.proveedor_ciudad_likelihoods[unidad_id]:
                    prob = self.proveedor_ciudad_likelihoods[unidad_id][key]
                    log_prob += math.log(prob) * 3.0  # Peso alto (muy específico)
                    debug_info[unidad_id]['proveedor_ciudad'] = prob
            
            # Log-likelihood de proveedor solo
            elif proveedor_id:
                if proveedor_id in self.proveedor_likelihoods[unidad_id]:
                    prob = self.proveedor_likelihoods[unidad_id][proveedor_id]
                    log_prob += math.log(prob) * 2.0  # Peso medio
                    debug_info[unidad_id]['proveedor'] = prob
            
            # Log-likelihood de ciudad
            if ciudad and ciudad in self.ciudad_likelihoods[unidad_id]:
                prob = self.ciudad_likelihoods[unidad_id][ciudad]
                log_prob += math.log(prob) * 1.0  # Peso bajo
                debug_info[unidad_id]['ciudad'] = prob
            
            # Log-likelihood de keywords (Naive Bayes)
            kw_score = 0.0
            kw_matched = []
            for kw in keywords_presentes:
                if kw in self.keyword_likelihoods[unidad_id]:
                    prob = self.keyword_likelihoods[unidad_id][kw]
                    kw_score += math.log(prob)
                    kw_matched.append((kw, prob))
            
            if kw_matched:
                log_prob += kw_score * 1.5  # Peso medio-alto
                debug_info[unidad_id]['keywords'] = kw_matched[:5]
            
            log_probs[unidad_id] = log_prob
            debug_info[unidad_id]['log_prob'] = log_prob
        
        if not log_probs:
            return None, 0.0, {'error': 'sin_candidatos'}
        
        # Encontrar la unidad con mayor log-probabilidad
        mejor_unidad_id = max(log_probs, key=log_probs.get)
        mejor_log_prob = log_probs[mejor_unidad_id]
        
        # Convertir log-prob a confidence (0-1)
        # Usar softmax para normalizar
        max_log = max(log_probs.values())
        exp_probs = {uid: math.exp(lp - max_log) for uid, lp in log_probs.items()}
        total_exp = sum(exp_probs.values())
        confidence = exp_probs[mejor_unidad_id] / total_exp
        
        return mejor_unidad_id, confidence, dict(debug_info)
    
    def _extract_keywords_from_text(self, texto: str) -> Set[str]:
        """Extrae keywords relevantes del texto que existen en el modelo."""
        keywords = set()
        
        # Buscar todas las keywords conocidas en el texto
        for unidad_id in self.keyword_likelihoods:
            for kw in self.keyword_likelihoods[unidad_id]:
                if kw in texto:
                    keywords.add(kw)
        
        return keywords
    
    def update_incremental(
        self,
        unidad_id: int,
        proveedor_id: Optional[int],
        ciudad: Optional[str],
        keywords: List[str]
    ):
        """
        Actualización incremental después de una clasificación validada.
        Permite aprender sin recargar todo el historial.
        """
        # Actualizar contadores
        self.unidad_counts[unidad_id] += 1
        self.total_samples += 1
        
        # Actualizar keywords
        for kw in keywords:
            kw_upper = kw.upper()
            self.keyword_likelihoods[unidad_id][kw_upper] += 1
        
        # Actualizar proveedor
        if proveedor_id:
            self.proveedor_likelihoods[unidad_id][proveedor_id] += 1
            
            if ciudad:
                key = f"{proveedor_id}:{ciudad}"
                self.proveedor_ciudad_likelihoods[unidad_id][key] += 1
        
        # Actualizar ciudad
        if ciudad:
            ciudad_upper = ciudad.upper()
            self.ciudad_likelihoods[unidad_id][ciudad_upper] += 1
        
        # Recalcular probabilidades
        for uid, count in self.unidad_counts.items():
            self.priors[uid] = count / self.total_samples
        
        self._normalize_likelihoods()
        
        logger.debug(f"Actualización incremental: unidad {unidad_id}, total muestras {self.total_samples}")


# Instancia global
probabilistic_classifier = ProbabilisticClassifier()
