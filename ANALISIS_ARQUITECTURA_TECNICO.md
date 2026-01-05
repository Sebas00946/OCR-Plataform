# 🏗️ ANÁLISIS TÉCNICO DE LA ARQUITECTURA
## Sistema OCR de Clasificación de Facturas

---

## 📐 ARQUITECTURA ACTUAL

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────┐
│                      ENTRADA (Node.js)                       │
│                    XML + PDF + factura_id                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   API REST (FastAPI)                         │
│                  POST /api/classify                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  InvoiceExtractor                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. extract_from_xml()                                │   │
│  │    - Parsea XML con namespaces UBL                   │   │
│  │    - Extrae proveedor, cliente, factura              │   │
│  │    - Extrae valores monetarios                       │   │
│  │    - Calcula calidad (0.0-1.0)                       │   │
│  │                                                       │   │
│  │ 2. extract_from_pdf()                                │   │
│  │    - Extrae texto con pdfplumber                     │   │
│  │    - Busca NIT, número factura con regex             │   │
│  │                                                       │   │
│  │ 3. extract_combined()                                │   │
│  │    - Combina XML + PDF con pesos dinámicos           │   │
│  │    - XML quality >= 0.8 → 70% XML, 30% PDF          │   │
│  │    - XML quality >= 0.5 → 60% XML, 40% PDF          │   │
│  │    - XML quality < 0.5  → 50% XML, 50% PDF          │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   PDFClassifier                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. _classify_sucursal()                              │   │
│  │    - Busca keywords en texto                         │   │
│  │    - Filtra keywords genéricas                       │   │
│  │    - Acumula scores por sucursal                     │   │
│  │                                                       │   │
│  │ 2. _classify_unidad()                                │   │
│  │    - Busca keywords de unidades                      │   │
│  │    - Filtra por sucursal si existe                   │   │
│  │    - Detecta tipo de unidad por contenido            │   │
│  │                                                       │   │
│  │ 3. _validar_coherencia()                             │   │
│  │    - Verifica sucursal-unidad match                  │   │
│  │    - Corrige inconsistencias                         │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 ProveedorMatcher                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. _match_by_nit()                                   │   │
│  │    - Busca por NIT exacto                            │   │
│  │    - Confidence: 1.0                                 │   │
│  │                                                       │   │
│  │ 2. _match_by_nombre()                                │   │
│  │    - Similitud de texto (SequenceMatcher)            │   │
│  │    - Limpia sufijos (S.A.S, LTDA)                    │   │
│  │    - Confidence: 0.0-1.0                             │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  LearningSystem                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. save_classification()                             │   │
│  │    - Guarda en ocr_clasificacion_historial           │   │
│  │                                                       │   │
│  │ 2. validate_and_learn()                              │   │
│  │    - Si correcta: refuerza keywords (+1 peso)        │   │
│  │    - Si incorrecta: penaliza keywords (-1 peso)      │   │
│  │    - Extrae nuevas keywords inteligentes             │   │
│  │    - Agrega automáticamente a BD                     │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      RESPUESTA                               │
│  {                                                           │
│    sucursal: {...},                                          │
│    unidad_funcional: {...},                                  │
│    proveedor: {...},                                         │
│    proveedor_match: {...},                                   │
│    factura: {...},                                           │
│    cliente: {...},                                           │
│    historial_id: 123                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 ANÁLISIS DE COMPONENTES

### 1. InvoiceExtractor (`src/extractor.py`)

#### Fortalezas ✅
- Manejo robusto de XML con namespaces UBL
- Extracción de Invoice embebido en CDATA
- Cálculo inteligente de calidad XML
- Pesos dinámicos XML/PDF
- Extracción completa de valores monetarios
- Manejo de retenciones agrupadas

#### Oportunidades de Mejora 🔧

**1. Caché de Parsing XML**
```python
# Problema: Parsea XML múltiples veces
# Solución: Cache del árbol parseado

from functools import lru_cache

class InvoiceExtractor:
    @lru_cache(maxsize=100)
    def _parse_xml_cached(self, xml_path: str) -> ET.Element:
        """Cache del parsing XML"""
        tree = ET.parse(xml_path)
        return tree.getroot()
```

**2. Extracción Paralela XML + PDF**
```python
# Problema: Extrae secuencialmente
# Solución: Usar ThreadPoolExecutor

from concurrent.futures import ThreadPoolExecutor

def extract_combined(self, xml_path=None, pdf_path=None):
    with ThreadPoolExecutor(max_workers=2) as executor:
        xml_future = executor.submit(self.extract_from_xml, xml_path) if xml_path else None
        pdf_future = executor.submit(self.extract_from_pdf, pdf_path) if pdf_path else None
        
        xml_result = xml_future.result() if xml_future else ("", 0.0, {})
        pdf_result = pdf_future.result() if pdf_future else ("", {})
```

**3. Validación de Datos Extraídos**
```python
# Problema: No valida datos extraídos
# Solución: Validación con Pydantic

from pydantic import BaseModel, validator

class ProveedorData(BaseModel):
    nombre: str
    nit: str
    
    @validator('nit')
    def validate_nit(cls, v):
        if not v or len(v) < 9:
            raise ValueError('NIT inválido')
        return v
```

---

### 2. PDFClassifier (`src/classifier.py`)

#### Fortalezas ✅
- Filtrado de keywords genéricas
- Validación de coherencia sucursal-unidad
- Detección inteligente de tipo de unidad
- Asignación por defecto cuando no hay match

#### Oportunidades de Mejora 🔧

**1. Índice de Keywords en Memoria**
```python
# Problema: Query a BD por cada clasificación
# Solución: Cache de keywords en memoria

class PDFClassifier:
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self._keywords_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 3600  # 1 hora
    
    def _get_keywords_cached(self):
        """Obtiene keywords con cache"""
        now = time.time()
        if (self._keywords_cache is None or 
            self._cache_timestamp is None or 
            now - self._cache_timestamp > self._cache_ttl):
            
            # Recargar cache
            self._keywords_cache = self._load_all_keywords()
            self._cache_timestamp = now
        
        return self._keywords_cache
```

**2. Búsqueda Optimizada de Keywords**
```python
# Problema: Busca cada keyword con 'in text' (O(n*m))
# Solución: Usar Aho-Corasick para búsqueda múltiple (O(n+m))

import ahocorasick

class PDFClassifier:
    def _build_automaton(self, keywords: List[str]):
        """Construye autómata para búsqueda rápida"""
        A = ahocorasick.Automaton()
        for idx, keyword in enumerate(keywords):
            A.add_word(keyword, (idx, keyword))
        A.make_automaton()
        return A
    
    def _find_all_keywords(self, text: str, automaton):
        """Encuentra todas las keywords en O(n)"""
        matches = []
        for end_index, (idx, keyword) in automaton.iter(text):
            matches.append(keyword)
        return matches
```

**3. Score Normalizado**
```python
# Problema: Scores absolutos difíciles de interpretar
# Solución: Normalizar scores a 0-1

def _normalize_score(self, score: float, max_possible: float) -> float:
    """Normaliza score a rango 0-1"""
    if max_possible == 0:
        return 0.0
    return min(score / max_possible, 1.0)
```

---

### 3. MultiPassClassifier (`src/multi_pass_classifier.py`)

#### Fortalezas ✅
- Sistema de 4 pasadas bien estructurado
- Extracción de contexto de alta confiabilidad
- Keywords únicas con peso x10
- Análisis semántico con patrones
- Detección de ambigüedades

#### Oportunidades de Mejora 🔧

**1. Configuración Dinámica de Patrones**
```python
# Problema: Patrones hardcodeados
# Solución: Cargar desde BD o archivo YAML

# patterns.yaml
semantic_patterns:
  ADMINISTRACION:
    - servicios administrativos
    - telecomunicaciones
  ALMACEN:
    - medicamentos
    - insumos medicos

class SemanticAnalyzer:
    def __init__(self, patterns_file: str = 'patterns.yaml'):
        with open(patterns_file) as f:
            self.PATTERNS = yaml.safe_load(f)['semantic_patterns']
```

**2. Pesos Adaptativos**
```python
# Problema: Pesos fijos para cada pasada
# Solución: Ajustar pesos según confiabilidad

class MultiPassClassifier:
    def _calculate_adaptive_weights(self, context: Dict) -> Dict:
        """Calcula pesos adaptativos según contexto"""
        weights = {
            'context': 0.4,
            'keywords': 0.3,
            'semantic': 0.2,
            'memory': 0.1
        }
        
        # Si contexto tiene alta confiabilidad, aumentar peso
        if context.get('confidence', {}).get('ciudad', 0) > 0.95:
            weights['context'] = 0.5
            weights['keywords'] = 0.25
        
        return weights
```

**3. Explicabilidad de Decisiones**
```python
# Problema: No explica por qué clasificó así
# Solución: Generar explicación detallada

def _generate_explanation(self, result: Dict) -> str:
    """Genera explicación legible de la clasificación"""
    explanation = []
    
    if 'context' in result:
        ciudad = result['context'].get('ciudad')
        if ciudad:
            explanation.append(f"Ciudad detectada: {ciudad}")
    
    if 'keywords' in result:
        explanation.append(f"Keywords encontradas: {', '.join(result['keywords'][:5])}")
    
    if 'semantic_matches' in result:
        explanation.append(f"Patrones semánticos: {len(result['semantic_matches'])}")
    
    return " | ".join(explanation)
```

---

### 4. LearningSystem (`src/learning.py`)

#### Fortalezas ✅
- Auto-aprendizaje con validaciones
- Extracción inteligente de keywords
- Refuerzo/penalización de pesos
- Agregado automático de keywords

#### Oportunidades de Mejora 🔧

**1. Análisis de Tendencias**
```python
# Problema: No analiza tendencias de aprendizaje
# Solución: Dashboard de métricas

class LearningSystem:
    def get_learning_trends(self, days: int = 30) -> Dict:
        """Analiza tendencias de aprendizaje"""
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    DATE(fecha_validacion) as fecha,
                    COUNT(*) as total,
                    SUM(CASE WHEN clasificacion_correcta THEN 1 ELSE 0 END) as correctas,
                    AVG(confianza_unidad) as confianza_promedio
                FROM ocr_clasificacion_historial
                WHERE fecha_validacion >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(fecha_validacion)
                ORDER BY fecha
            """, (days,))
            
            trends = []
            for row in cursor.fetchall():
                trends.append({
                    'fecha': row[0].isoformat(),
                    'total': row[1],
                    'correctas': row[2],
                    'precision': (row[2] / row[1] * 100) if row[1] > 0 else 0,
                    'confianza_promedio': float(row[3])
                })
            
            return {'trends': trends}
            
        finally:
            cursor.close()
            conn.close()
```

**2. Detección de Keywords Problemáticas**
```python
# Problema: No identifica keywords que causan errores
# Solución: Análisis de keywords en clasificaciones incorrectas

def identify_problematic_keywords(self) -> List[Dict]:
    """Identifica keywords que causan clasificaciones incorrectas"""
    conn = psycopg2.connect(**self.db_config)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                jsonb_array_elements_text(keywords_encontradas->'unidad') as keyword,
                COUNT(*) as total_usos,
                SUM(CASE WHEN clasificacion_correcta = FALSE THEN 1 ELSE 0 END) as errores,
                (SUM(CASE WHEN clasificacion_correcta = FALSE THEN 1 ELSE 0 END)::float / COUNT(*)) as tasa_error
            FROM ocr_clasificacion_historial
            WHERE clasificacion_correcta IS NOT NULL
            GROUP BY keyword
            HAVING COUNT(*) >= 5
            AND (SUM(CASE WHEN clasificacion_correcta = FALSE THEN 1 ELSE 0 END)::float / COUNT(*)) > 0.5
            ORDER BY tasa_error DESC
            LIMIT 20
        """)
        
        problematic = []
        for row in cursor.fetchall():
            problematic.append({
                'keyword': row[0],
                'total_usos': row[1],
                'errores': row[2],
                'tasa_error': float(row[3])
            })
        
        return problematic
        
    finally:
        cursor.close()
        conn.close()
```

**3. Aprendizaje Incremental Automático**
```python
# Problema: Requiere validación manual
# Solución: Auto-validación con alta confiabilidad

def auto_validate_high_confidence(self, threshold: float = 0.95):
    """Auto-valida clasificaciones con alta confiabilidad"""
    conn = psycopg2.connect(**self.db_config)
    cursor = conn.cursor()
    
    try:
        # Buscar clasificaciones sin validar con alta confiabilidad
        cursor.execute("""
            SELECT id, sucursal_detectada_id, unidad_funcional_detectada_id
            FROM ocr_clasificacion_historial
            WHERE clasificacion_correcta IS NULL
            AND confianza_unidad >= %s
            AND confianza_sucursal >= %s
            AND fecha_clasificacion >= NOW() - INTERVAL '7 days'
        """, (threshold, threshold))
        
        auto_validated = 0
        for row in cursor.fetchall():
            historial_id, sucursal_id, unidad_id = row
            
            # Auto-validar como correcta
            self.validate_and_learn(
                historial_id=historial_id,
                es_correcta=True,
                sucursal_correcta_id=sucursal_id,
                unidad_correcta_id=unidad_id,
                observaciones='Auto-validado por alta confiabilidad',
                auto_add_keywords=True
            )
            auto_validated += 1
        
        return {'auto_validated': auto_validated}
        
    finally:
        cursor.close()
        conn.close()
```

---

## 🚀 OPTIMIZACIONES DE RENDIMIENTO

### 1. Connection Pooling

```python
# Problema: Abre/cierra conexión en cada operación
# Solución: Pool de conexiones

from psycopg2 import pool

class DatabasePool:
    _pool = None
    
    @classmethod
    def initialize(cls, db_config: Dict, minconn=1, maxconn=10):
        """Inicializa pool de conexiones"""
        cls._pool = pool.ThreadedConnectionPool(
            minconn, maxconn, **db_config
        )
    
    @classmethod
    def get_connection(cls):
        """Obtiene conexión del pool"""
        return cls._pool.getconn()
    
    @classmethod
    def return_connection(cls, conn):
        """Devuelve conexión al pool"""
        cls._pool.putconn(conn)

# Uso en clasificadores
class PDFClassifier:
    def classify(self, text: str):
        conn = DatabasePool.get_connection()
        try:
            cursor = conn.cursor()
            # ... operaciones ...
        finally:
            cursor.close()
            DatabasePool.return_connection(conn)
```

### 2. Batch Processing

```python
# Problema: Procesa facturas una por una
# Solución: Procesamiento en lotes

class BatchProcessor:
    def __init__(self, classifier, batch_size: int = 10):
        self.classifier = classifier
        self.batch_size = batch_size
    
    def process_batch(self, invoices: List[Dict]) -> List[Dict]:
        """Procesa múltiples facturas en paralelo"""
        from concurrent.futures import ThreadPoolExecutor
        
        results = []
        with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            futures = [
                executor.submit(self._process_single, inv)
                for inv in invoices
            ]
            
            for future in futures:
                results.append(future.result())
        
        return results
    
    def _process_single(self, invoice: Dict) -> Dict:
        """Procesa una factura"""
        return self.classifier.classify(
            invoice['xml_data'],
            invoice['pdf_text']
        )
```

### 3. Caché de Resultados

```python
# Problema: Re-clasifica facturas idénticas
# Solución: Cache con hash del contenido

import hashlib
import redis

class ClassificationCache:
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        self.redis = redis.from_url(redis_url)
        self.ttl = 86400  # 24 horas
    
    def get_cached_result(self, text: str) -> Optional[Dict]:
        """Obtiene resultado cacheado"""
        key = self._generate_key(text)
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    def cache_result(self, text: str, result: Dict):
        """Cachea resultado"""
        key = self._generate_key(text)
        self.redis.setex(
            key,
            self.ttl,
            json.dumps(result)
        )
    
    def _generate_key(self, text: str) -> str:
        """Genera key único para el texto"""
        return f"classification:{hashlib.md5(text.encode()).hexdigest()}"
```

---

## 📊 MÉTRICAS Y MONITOREO

### 1. Métricas de Rendimiento

```python
# src/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Contadores
classifications_total = Counter(
    'ocr_classifications_total',
    'Total de clasificaciones',
    ['status']
)

# Histogramas (latencia)
classification_duration = Histogram(
    'ocr_classification_duration_seconds',
    'Duración de clasificación',
    ['method']
)

# Gauges (valores actuales)
classification_confidence = Gauge(
    'ocr_classification_confidence',
    'Confiabilidad promedio'
)

class MetricsCollector:
    @staticmethod
    def track_classification(method: str):
        """Decorator para trackear clasificaciones"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    classifications_total.labels(status='success').inc()
                    
                    # Registrar confiabilidad
                    if 'confidence' in result:
                        classification_confidence.set(result['confidence'])
                    
                    return result
                except Exception as e:
                    classifications_total.labels(status='error').inc()
                    raise
                finally:
                    duration = time.time() - start
                    classification_duration.labels(method=method).observe(duration)
            
            return wrapper
        return decorator
```

### 2. Dashboard de Monitoreo

```python
# Endpoint para métricas
@app.get("/api/metrics")
async def get_metrics():
    """Obtiene métricas del sistema"""
    return {
        'classifications': {
            'total': classifications_total._value.get(),
            'success_rate': calculate_success_rate(),
        },
        'performance': {
            'avg_duration': classification_duration._sum.get() / classification_duration._count.get(),
            'p95_duration': calculate_p95(),
        },
        'quality': {
            'avg_confidence': classification_confidence._value.get(),
            'precision': get_precision_from_db(),
        }
    }
```

---

## 🔒 SEGURIDAD Y VALIDACIÓN

### 1. Validación de Entrada

```python
# Problema: No valida archivos subidos
# Solución: Validación estricta

from fastapi import UploadFile, HTTPException
import magic

class FileValidator:
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_XML_MIMES = ['application/xml', 'text/xml']
    ALLOWED_PDF_MIMES = ['application/pdf']
    
    @staticmethod
    def validate_xml(file: UploadFile):
        """Valida archivo XML"""
        # Verificar tamaño
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > FileValidator.MAX_FILE_SIZE:
            raise HTTPException(400, "Archivo XML muy grande")
        
        # Verificar MIME type
        mime = magic.from_buffer(file.file.read(1024), mime=True)
        file.file.seek(0)
        
        if mime not in FileValidator.ALLOWED_XML_MIMES:
            raise HTTPException(400, f"Tipo de archivo inválido: {mime}")
        
        # Verificar que sea XML válido
        try:
            content = file.file.read()
            file.file.seek(0)
            ET.fromstring(content)
        except ET.ParseError:
            raise HTTPException(400, "XML malformado")
```

### 2. Rate Limiting

```python
# Problema: Sin protección contra abuso
# Solución: Rate limiting por IP

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/classify")
@limiter.limit("100/hour")  # 100 requests por hora
async def classify_invoice(request: Request, ...):
    ...
```

---

## 📝 CONCLUSIONES Y RECOMENDACIONES

### Prioridades de Implementación

#### 🔴 Alta Prioridad (Implementar Ya)
1. **Connection Pooling** → Mejora rendimiento 30-40%
2. **Cache de Keywords** → Reduce queries a BD 80%
3. **Validación de Entrada** → Seguridad crítica
4. **Métricas y Monitoreo** → Visibilidad del sistema

#### 🟡 Media Prioridad (Próximas 2 semanas)
1. **Batch Processing** → Escalabilidad
2. **Cache de Resultados** → Reduce carga
3. **Análisis de Tendencias** → Mejora continua
4. **Pesos Adaptativos** → Mayor precisión

#### 🟢 Baja Prioridad (Futuro)
1. **Búsqueda Aho-Corasick** → Optimización marginal
2. **Auto-validación** → Requiere más datos
3. **Explicabilidad** → Nice to have

### Impacto Estimado

| Optimización | Impacto Rendimiento | Impacto Precisión | Esfuerzo |
|--------------|---------------------|-------------------|----------|
| Connection Pool | +35% | 0% | 2 horas |
| Cache Keywords | +50% | 0% | 3 horas |
| Batch Processing | +200% | 0% | 4 horas |
| Pesos Adaptativos | +5% | +3% | 6 horas |
| IA (Embeddings) | -20% | +10% | 3 días |

### Arquitectura Objetivo

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (FastAPI)                     │
│              Rate Limiting + Validación + Métricas           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Cache Layer (Redis)                        │
│              Resultados + Keywords + Embeddings              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Hybrid Classifier                            │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │ Multi-Pass   │  Embeddings  │   Memory     │   LLM    │  │
│  │  (35%)       │    (30%)     │   (25%)      │  (10%)   │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Database Pool (PostgreSQL)                      │
│         Keywords + Historial + Embeddings + Proveedores      │
└─────────────────────────────────────────────────────────────┘
```

---

**Próximo Paso**: Implementar optimizaciones de alta prioridad antes de agregar IA.
