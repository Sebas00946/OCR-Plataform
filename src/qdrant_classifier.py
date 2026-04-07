"""
Clasificador basado en similitud vectorial usando Qdrant.
Fase 2 del plan de mejoras con IA.

Requiere:
  pip install qdrant-client sentence-transformers

Qdrant corriendo en Docker:
  docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
"""
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
COLLECTION_NAME = 'facturas_clasificadas'
SIMILARITY_THRESHOLD = float(os.getenv('QDRANT_SIMILARITY_THRESHOLD', '0.82'))
TOP_K = 5  # Cuántas facturas similares consultar


class QdrantClassifier:
    """
    Clasifica facturas buscando las más similares en Qdrant.
    Actúa como Paso 3 en la cascada: se activa cuando keywords dan score < 50.
    """

    def __init__(self):
        self._client = None
        self._encoder = None
        self._available = False
        self._init()

    def _init(self):
        """Inicializa cliente y encoder. Falla silenciosamente si no están instalados."""
        try:
            from qdrant_client import QdrantClient
            from sentence_transformers import SentenceTransformer

            self._client = QdrantClient(url=QDRANT_URL, timeout=5)
            # Modelo multilingüe liviano (384 dims, corre en CPU)
            self._encoder = SentenceTransformer(
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
            )
            # Verificar que la colección existe
            self._ensure_collection()
            self._available = True
            logger.info("QdrantClassifier inicializado correctamente")
        except ImportError:
            logger.warning(
                "qdrant-client o sentence-transformers no instalados. "
                "Ejecuta: pip install qdrant-client sentence-transformers"
            )
        except Exception as e:
            logger.warning(f"Qdrant no disponible ({QDRANT_URL}): {e}")

    @property
    def available(self) -> bool:
        return self._available

    def classify(self, texto: str, proveedor_nit: Optional[str] = None) -> Optional[Dict]:
        """
        Busca facturas similares y retorna la clasificación más frecuente.

        Args:
            texto: Texto combinado XML+PDF de la factura
            proveedor_nit: NIT del proveedor (mejora la búsqueda)

        Returns:
            Dict con sucursal y unidad si similitud >= threshold, None si no hay match
        """
        if not self._available or not texto:
            return None

        try:
            vector = self._encode(texto)

            # Filtrar por proveedor si se proporciona (resultados más precisos)
            search_filter = None
            if proveedor_nit:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                search_filter = Filter(
                    must=[FieldCondition(
                        key='proveedor_nit',
                        match=MatchValue(value=proveedor_nit)
                    )]
                )

            results = self._client.search(
                collection_name=COLLECTION_NAME,
                query_vector=vector,
                query_filter=search_filter,
                limit=TOP_K,
                score_threshold=SIMILARITY_THRESHOLD
            )

            if not results:
                # Si no hay resultados con filtro de proveedor, buscar sin filtro
                if proveedor_nit:
                    results = self._client.search(
                        collection_name=COLLECTION_NAME,
                        query_vector=vector,
                        limit=TOP_K,
                        score_threshold=SIMILARITY_THRESHOLD
                    )

            if not results:
                return None

            # Votar por la clasificación más frecuente entre los top-K resultados
            return self._vote_classification(results)

        except Exception as e:
            logger.error(f"Error en búsqueda Qdrant: {e}")
            return None

    def index_classification(
        self,
        historial_id: int,
        texto: str,
        proveedor_nit: str,
        proveedor_nombre: str,
        unidad_id: int,
        unidad_nombre: str,
        sucursal_id: int,
        sucursal_nombre: str,
        clasificacion_correcta: bool = True,
        score_original: float = 0.0
    ) -> bool:
        """
        Indexa una factura clasificada correctamente en Qdrant.
        Llamar después de cada validación correcta o corrección manual.
        """
        if not self._available or not texto:
            return False

        try:
            from qdrant_client.models import PointStruct

            vector = self._encode(texto)
            point = PointStruct(
                id=historial_id,
                vector=vector,
                payload={
                    'proveedor_nit': proveedor_nit,
                    'proveedor_nombre': proveedor_nombre,
                    'unidad_funcional_id': unidad_id,
                    'unidad_funcional_nombre': unidad_nombre,
                    'sucursal_id': sucursal_id,
                    'sucursal_nombre': sucursal_nombre,
                    'clasificacion_correcta': clasificacion_correcta,
                    'score_original': score_original,
                }
            )
            self._client.upsert(collection_name=COLLECTION_NAME, points=[point])
            logger.debug(f"Factura {historial_id} indexada en Qdrant")
            return True
        except Exception as e:
            logger.error(f"Error indexando en Qdrant: {e}")
            return False

    def index_batch_from_db(self, limit: int = 1000) -> int:
        """
        Indexa el historial existente de la BD en Qdrant.
        Útil para la carga inicial.
        """
        if not self._available:
            return 0

        from .database import db
        import psycopg2.extras

        indexed = 0
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute("""
                    SELECT
                        h.id,
                        h.keywords_encontradas,
                        h.datos_extraidos,
                        p.nit AS proveedor_nit,
                        p.razon_social AS proveedor_nombre,
                        uf.id AS unidad_id,
                        uf.nombre AS unidad_nombre,
                        s.id AS sucursal_id,
                        s.nombre AS sucursal_nombre,
                        h.clasificacion_correcta,
                        COALESCE(h.confianza_unidad, 0) AS score_original
                    FROM ocr_clasificacion_historial h
                    LEFT JOIN proveedores p ON p.id = h.proveedor_detectado_id
                    LEFT JOIN unidades_funcionales uf ON uf.id = COALESCE(
                        h.unidad_correcta_id, h.unidad_funcional_detectada_id
                    )
                    LEFT JOIN sucursales s ON s.id = uf.sucursal_id
                    WHERE h.clasificacion_correcta = TRUE
                       OR h.unidad_correcta_id IS NOT NULL
                    ORDER BY h.created_at DESC
                    LIMIT %s
                """, (limit,))

                rows = cursor.fetchall()
                cursor.close()

            for row in rows:
                # Reconstruir texto desde datos guardados
                kw = row['keywords_encontradas'] or {}
                datos = row['datos_extraidos'] or {}
                texto = ' '.join(
                    kw.get('sucursal', []) +
                    kw.get('unidad', []) +
                    [kw.get('texto_completo', '')] +
                    [datos.get('text', '')]
                )

                if not texto.strip() or not row['unidad_id']:
                    continue

                ok = self.index_classification(
                    historial_id=row['id'],
                    texto=texto,
                    proveedor_nit=row['proveedor_nit'] or '',
                    proveedor_nombre=row['proveedor_nombre'] or '',
                    unidad_id=row['unidad_id'],
                    unidad_nombre=row['unidad_nombre'] or '',
                    sucursal_id=row['sucursal_id'] or 0,
                    sucursal_nombre=row['sucursal_nombre'] or '',
                    clasificacion_correcta=bool(row['clasificacion_correcta']),
                    score_original=float(row['score_original'] or 0)
                )
                if ok:
                    indexed += 1

            logger.info(f"Indexadas {indexed}/{len(rows)} facturas en Qdrant")
        except Exception as e:
            logger.error(f"Error en indexación masiva: {e}")

        return indexed

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODOS PRIVADOS
    # ─────────────────────────────────────────────────────────────────────────

    def _encode(self, texto: str) -> List[float]:
        """Genera embedding del texto. Limita a 512 tokens."""
        texto_limpio = texto[:2000]  # ~512 tokens aprox
        return self._encoder.encode(texto_limpio).tolist()

    def _ensure_collection(self):
        """Crea la colección en Qdrant si no existe."""
        from qdrant_client.models import VectorParams, Distance

        collections = [c.name for c in self._client.get_collections().collections]
        if COLLECTION_NAME not in collections:
            self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info(f"Colección '{COLLECTION_NAME}' creada en Qdrant")

    def _vote_classification(self, results) -> Optional[Dict]:
        """
        Vota por la clasificación más frecuente entre los resultados.
        Pondera por score de similitud.
        """
        votes: Dict[int, Dict] = {}

        for hit in results:
            payload = hit.payload
            unidad_id = payload.get('unidad_funcional_id')
            if not unidad_id:
                continue

            if unidad_id not in votes:
                votes[unidad_id] = {
                    'score_total': 0.0,
                    'count': 0,
                    'payload': payload
                }
            votes[unidad_id]['score_total'] += hit.score
            votes[unidad_id]['count'] += 1

        if not votes:
            return None

        # Elegir la unidad con mayor score ponderado
        mejor = max(votes.values(), key=lambda x: x['score_total'])
        payload = mejor['payload']
        avg_score = mejor['score_total'] / mejor['count']

        return {
            'success': True,
            'id': payload.get('unidad_funcional_id'),
            'nombre': payload.get('unidad_funcional_nombre'),
            'sucursal_id': payload.get('sucursal_id'),
            'sucursal_nombre': payload.get('sucursal_nombre'),
            'score': avg_score * 100,  # Normalizar a escala 0-100
            'confidence': avg_score,
            'method': 'qdrant_similarity',
            'matches_count': mejor['count'],
            'keywords': [f'similitud={avg_score:.2f}']
        }


# Instancia global (se inicializa lazy)
_qdrant_classifier: Optional[QdrantClassifier] = None


def get_qdrant_classifier() -> QdrantClassifier:
    global _qdrant_classifier
    if _qdrant_classifier is None:
        _qdrant_classifier = QdrantClassifier()
    return _qdrant_classifier
