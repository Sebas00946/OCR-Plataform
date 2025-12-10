# 📚 DOCUMENTACIÓN COMPLETA DEL SISTEMA OCR

## 🎯 DESCRIPCIÓN GENERAL

Sistema de clasificación automática de facturas que utiliza inteligencia artificial para leer archivos XML y PDF, identificar automáticamente la sucursal y unidad funcional correspondiente, y aprender de las validaciones del usuario para mejorar continuamente su precisión.

### Características Principales

- **Extracción Inteligente**: Lee y combina información de archivos XML (60%) y PDF (40%) con pesos dinámicos
- **Clasificación Automática**: Identifica sucursal y unidad funcional usando keywords parametrizables
- **Auto-aprendizaje**: Mejora automáticamente con cada validación del usuario
- **API REST**: Completamente integrable con sistemas Node.js y otros backends
- **Base de Datos PostgreSQL**: Almacena keywords, historial y configuraciones
- **Sistema de Pesos**: Keywords con pesos ajustables (1-10) que se refuerzan automáticamente

---

## 🏗️ ARQUITECTURA DEL SISTEMA

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENTE (Node.js)                       │
│                    Frontend / Backend                        │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    API REST (FastAPI)                        │
│                      src/api.py                              │
│  Endpoints: /classify, /validate, /stats, /health           │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Extractor   │  │  Classifier  │  │   Learning   │
│ extractor.py │  │classifier.py │  │ learning.py  │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
              ┌─────────────────────┐
              │  PostgreSQL Database │
              │   veritask_manager   │
              └─────────────────────┘
```


---

## 📂 ESTRUCTURA DE ARCHIVOS

```
OCR-Plataform/
│
├── 📁 src/                          # Código fuente principal
│   ├── api.py                       # API REST con FastAPI
│   ├── classifier.py                # Motor de clasificación con keywords
│   ├── extractor.py                 # Extractor de texto XML/PDF
│   ├── learning.py                  # Sistema de auto-aprendizaje
│   ├── config.py                    # Configuración de base de datos
│   └── __init__.py
│
├── 📁 database/                     # Scripts de base de datos
│   ├── schema.sql                   # Estructura completa de tablas
│   ├── keywords.sql                 # Keywords iniciales por unidad
│   ├── add_admin_keywords.sql       # Keywords administrativas
│   └── seed_data.sql                # Datos de prueba (opcional)
│
├── 📁 scripts/                      # Scripts de utilidad
│   ├── classify.py                  # Clasificar facturas desde CLI
│   ├── test_api.py                  # Prueba rápida del sistema
│   └── __init__.py
│
├── 📁 tests/                        # Pruebas automatizadas
│   ├── test_api_integration.py      # Tests de integración API
│   ├── test_extraction.py           # Tests de extracción
│   ├── test_ocr_service.py          # Tests del servicio OCR
│   └── __init__.py
│
├── 📁 ejemplos/                     # Facturas de ejemplo
│   └── z09012928260082500000039/
│       ├── ad09012928260082500000039.xml
│       └── fv09012928260082500000039.pdf
│
├── 📁 data/                         # Datos de la aplicación
│   ├── uploads/                     # Archivos subidos temporalmente
│   ├── results/                     # Resultados de clasificación
│   └── temp/                        # Archivos temporales
│
├── 📁 logs/                         # Logs del sistema
│
├── .env                             # Variables de entorno
├── requirements.txt                 # Dependencias Python
├── README.md                        # Documentación básica
├── INTEGRACION_NODEJS.md           # Guía de integración Node.js
└── DOCUMENTACION_SISTEMA.md        # Este archivo
```

---

## 🔧 COMPONENTES DETALLADOS

### 1. API REST (src/api.py)

**Propósito**: Exponer endpoints HTTP para que sistemas externos (Node.js) puedan clasificar facturas.

**Endpoints Principales**:

#### POST /api/classify
Clasifica una factura usando XML y/o PDF.

**Parámetros**:
- `xml_file` (File, opcional): Archivo XML de la factura
- `pdf_file` (File, opcional): Archivo PDF de la factura
- `factura_id` (int, opcional): ID de la factura en tu sistema

**Respuesta**:
```json
{
  "success": true,
  "sucursal": {
    "id": 3,
    "nombre": "Clinica Medilaser S.A.S - Florencia",
    "codigo": "FLA",
    "score": 20,
    "keywords": ["FLORENCIA", "SEDE FLORENCIA"]
  },
  "unidad_funcional": {
    "id": 12,
    "nombre": "Administración - FLA",
    "codigo": "0008",
    "score": 35,
    "keywords": ["SEGUNDAS LECTURAS", "SEDE FLORENCIA"]
  },
  "historial_id": 123,
  "metadata": {
    "xml_quality": 0.5,
    "xml_weight": 0.6,
    "pdf_weight": 0.4,
    "has_xml": true,
    "has_pdf": true
  }
}
```

**Flujo Interno**:
1. Recibe archivos XML/PDF
2. Guarda temporalmente en disco
3. Llama a `InvoiceExtractor.extract_combined()`
4. Llama a `PDFClassifier.classify()`
5. Guarda en historial con `LearningSystem.save_classification()`
6. Retorna resultado con `historial_id`
7. Limpia archivos temporales

#### POST /api/validate
Valida una clasificación y permite al sistema aprender.

**Parámetros**:
```json
{
  "historial_id": 123,
  "es_correcta": true,
  "sucursal_correcta_id": null,
  "unidad_correcta_id": null,
  "observaciones": "Clasificación correcta"
}
```

**Respuesta**:
```json
{
  "success": true,
  "message": "Keywords reforzadas exitosamente",
  "keywords_reforzadas": 6,
  "sugerencias": []
}
```

**Flujo Interno**:
- Si `es_correcta = true`: Aumenta peso de keywords usadas (+1, máximo 10)
- Si `es_correcta = false`: Sugiere nuevas keywords basadas en el texto

#### GET /api/stats
Obtiene estadísticas del sistema.

**Respuesta**:
```json
{
  "total_clasificaciones": 150,
  "correctas": 142,
  "incorrectas": 8,
  "precision": 94.67,
  "confianza_promedio": {
    "sucursal": 28.5,
    "unidad": 35.2
  }
}
```

#### GET /api/health
Verifica estado del servicio y conexión a base de datos.


---

### 2. Extractor (src/extractor.py)

**Propósito**: Extraer texto de archivos XML y PDF con pesos inteligentes.

**Clase Principal**: `InvoiceExtractor`

#### Método: extract_from_xml(xml_path)

Extrae texto estructurado del XML y calcula su calidad.

**Campos Extraídos**:
1. **Proveedor** (peso: 1) - Nombre del emisor
2. **Cliente** (peso: 1) - Nombre del receptor
3. **Dirección** (peso: 1) - Dirección del cliente
4. **Ciudad** (peso: 1) - Ciudad del cliente
5. **Observaciones/Notas** (peso: 1) - Notas de la factura
6. **Items/Productos** (peso: 1) - Descripción de productos (máximo 10)

**Cálculo de Calidad**:
```python
calidad = campos_encontrados / 6
# Ejemplo: Si encuentra 4 de 6 campos = 0.67 (67%)
```

**Retorna**: `(texto_extraido, calidad_0_a_1)`

#### Método: extract_from_pdf(pdf_path)

Extrae todo el texto del PDF usando `pdfplumber`.

**Retorna**: `texto_extraido`

#### Método: extract_combined(xml_path, pdf_path)

Combina XML y PDF con pesos dinámicos según calidad del XML.

**Lógica de Pesos**:
```python
if xml_quality >= 0.8:  # XML muy completo
    xml_weight = 0.70
    pdf_weight = 0.30
elif xml_quality >= 0.5:  # XML moderado
    xml_weight = 0.60
    pdf_weight = 0.40
else:  # XML pobre
    xml_weight = 0.50
    pdf_weight = 0.50
```

**Retorna**:
```python
{
    'text': "TEXTO COMBINADO EN MAYÚSCULAS",
    'xml_text': "texto del xml",
    'pdf_text': "texto del pdf",
    'xml_quality': 0.67,
    'xml_weight': 0.60,
    'pdf_weight': 0.40,
    'has_xml': True,
    'has_pdf': True
}
```

---

### 3. Clasificador (src/classifier.py)

**Propósito**: Clasificar facturas usando keywords de la base de datos.

**Clase Principal**: `PDFClassifier`

#### Método: classify(text, xml_weight, pdf_weight)

Clasifica el texto en sucursal y unidad funcional.

**Algoritmo**:

1. **Buscar Keywords de Sucursal**:
   ```sql
   SELECT sucursal_id, keyword, peso
   FROM ocr_sucursal_keywords
   WHERE activo = TRUE
   ORDER BY peso DESC
   ```

2. **Calcular Score por Sucursal**:
   ```python
   for keyword in keywords:
       if keyword in text:
           score += peso_keyword
   ```

3. **Seleccionar Mejor Match**:
   ```python
   mejor_sucursal = max(matches, key=lambda x: x['score'])
   ```

4. **Repetir para Unidad Funcional**

**Ejemplo de Clasificación**:
```
Texto: "CLINICA MEDILASER FLORENCIA SEDE FLORENCIA"

Keywords encontradas:
- "FLORENCIA" (peso: 9) → +9 puntos
- "SEDE FLORENCIA" (peso: 8) → +8 puntos
- "MEDILASER" (peso: 7) → +7 puntos

Score total: 24 puntos
Resultado: Sucursal "Clinica Medilaser - Florencia" (ID: 3)
```

**Retorna**: `(info_sucursal, info_unidad)`

---

### 4. Sistema de Aprendizaje (src/learning.py)

**Propósito**: Aprender de las validaciones del usuario para mejorar la precisión.

**Clase Principal**: `LearningSystem`

#### Método: save_classification()

Guarda cada clasificación en el historial para análisis posterior.

**Tabla**: `ocr_clasificacion_historial`

**Campos Guardados**:
- `factura_id`: ID de la factura en tu sistema
- `archivo_nombre`: Nombre del archivo procesado
- `sucursal_detectada_id`: Sucursal identificada
- `unidad_funcional_detectada_id`: Unidad identificada
- `confianza_sucursal`: Score de confianza
- `confianza_unidad`: Score de confianza
- `keywords_encontradas`: JSON con keywords que coincidieron
- `datos_extraidos`: JSON con todo el texto extraído
- `created_at`: Timestamp de la clasificación

#### Método: validate_and_learn()

Aprende de la validación del usuario.

**Caso 1: Clasificación Correcta** (`es_correcta = true`)
```python
# Refuerza keywords que funcionaron
for keyword in keywords_usadas[:3]:  # Top 3
    UPDATE ocr_sucursal_keywords
    SET peso = LEAST(peso + 1, 10)  # Máximo 10
    WHERE keyword = keyword
```

**Caso 2: Clasificación Incorrecta** (`es_correcta = false`)
```python
# Sugiere nuevas keywords del texto
palabras_unicas = extraer_palabras(texto, min_length=4)
sugerencias = top_5_palabras_frecuentes
```

**Ejemplo de Aprendizaje**:
```
Clasificación inicial:
- Keyword "FLORENCIA" (peso: 5) → Usada correctamente

Usuario valida como correcta:
- Keyword "FLORENCIA" (peso: 6) → +1 punto

Después de 5 validaciones correctas:
- Keyword "FLORENCIA" (peso: 10) → Máximo alcanzado
```

#### Método: get_statistics()

Calcula estadísticas del sistema:
- Total de clasificaciones
- Clasificaciones correctas/incorrectas
- Precisión (%)
- Confianza promedio


---

## 🗄️ BASE DE DATOS (PostgreSQL)

### Tablas Principales

#### 1. ocr_sucursal_keywords
Almacena keywords para identificar sucursales.

```sql
CREATE TABLE ocr_sucursal_keywords (
    id SERIAL PRIMARY KEY,
    sucursal_id INTEGER NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    peso INTEGER DEFAULT 1,              -- Peso 1-10
    activo BOOLEAN DEFAULT TRUE,
    case_sensitive BOOLEAN DEFAULT FALSE,
    tipo_match VARCHAR(20) DEFAULT 'contiene',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (sucursal_id, keyword)
);
```

**Ejemplo de Datos**:
```sql
INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso) VALUES
(3, 'FLORENCIA', 9),
(3, 'SEDE FLORENCIA', 8),
(3, 'MEDILASER FLORENCIA', 10);
```

#### 2. ocr_unidad_keywords
Almacena keywords para identificar unidades funcionales.

```sql
CREATE TABLE ocr_unidad_keywords (
    id SERIAL PRIMARY KEY,
    unidad_funcional_id INTEGER NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    peso INTEGER DEFAULT 1,
    activo BOOLEAN DEFAULT TRUE,
    case_sensitive BOOLEAN DEFAULT FALSE,
    tipo_match VARCHAR(20) DEFAULT 'contiene',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (unidad_funcional_id, keyword)
);
```

**Ejemplo de Datos**:
```sql
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso) VALUES
(8, 'FLO MED', 10),
(8, 'FLORENCIA', 9),
(8, 'FACTURACION MAOS MEDILASER FLORENCIA', 9);
```

#### 3. ocr_clasificacion_historial
Almacena todas las clasificaciones realizadas.

```sql
CREATE TABLE ocr_clasificacion_historial (
    id SERIAL PRIMARY KEY,
    factura_id INTEGER,
    archivo_nombre VARCHAR(255) NOT NULL,
    archivo_tipo VARCHAR(10) NOT NULL,
    sucursal_detectada_id INTEGER,
    unidad_funcional_detectada_id INTEGER,
    confianza_sucursal DECIMAL(5,2),
    confianza_unidad DECIMAL(5,2),
    keywords_encontradas JSONB,
    datos_extraidos JSONB,
    tiempo_procesamiento_ms INTEGER,
    clasificacion_correcta BOOLEAN,
    observaciones TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Ejemplo de Registro**:
```json
{
  "id": 123,
  "factura_id": 456,
  "archivo_nombre": "factura_001.pdf",
  "sucursal_detectada_id": 3,
  "unidad_funcional_detectada_id": 8,
  "confianza_sucursal": 24.00,
  "confianza_unidad": 35.00,
  "keywords_encontradas": {
    "sucursal": ["FLORENCIA", "SEDE FLORENCIA"],
    "unidad": ["FLO MED", "FLORENCIA"]
  },
  "clasificacion_correcta": true,
  "created_at": "2024-12-09 10:30:00"
}
```

#### 4. ocr_configuracion
Configuración general del sistema.

```sql
CREATE TABLE ocr_configuracion (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT NOT NULL,
    tipo_dato VARCHAR(20) DEFAULT 'string',
    descripcion TEXT,
    categoria VARCHAR(50) DEFAULT 'general'
);
```

**Configuraciones Importantes**:
```sql
INSERT INTO ocr_configuracion (clave, valor, descripcion) VALUES
('min_confianza_sucursal', '70', 'Confianza mínima para aceptar clasificación (%)'),
('min_confianza_unidad', '60', 'Confianza mínima para unidad funcional (%)'),
('max_file_size_mb', '10', 'Tamaño máximo de archivo en MB');
```

#### 5. ocr_sinonimos
Sinónimos para mejorar la detección.

```sql
CREATE TABLE ocr_sinonimos (
    id SERIAL PRIMARY KEY,
    palabra_original VARCHAR(100) NOT NULL,
    sinonimo VARCHAR(100) NOT NULL,
    tipo VARCHAR(30) DEFAULT 'general',
    activo BOOLEAN DEFAULT TRUE
);
```

**Ejemplo**:
```sql
INSERT INTO ocr_sinonimos (palabra_original, sinonimo, tipo) VALUES
('bogota', 'bogotá', 'sucursal'),
('bogota', 'santafe de bogota', 'sucursal'),
('almacen', 'bodega', 'unidad_funcional');
```

---

## 🔄 FLUJO COMPLETO DEL SISTEMA

### Flujo de Clasificación

```
1. CLIENTE (Node.js)
   │
   ├─→ Envía POST /api/classify
   │   ├─ xml_file: factura.xml
   │   ├─ pdf_file: factura.pdf
   │   └─ factura_id: 12345
   │
   ▼
2. API (src/api.py)
   │
   ├─→ Guarda archivos temporalmente
   │   └─ /tmp/tmpXXXXXX.xml
   │   └─ /tmp/tmpXXXXXX.pdf
   │
   ▼
3. EXTRACTOR (src/extractor.py)
   │
   ├─→ extract_from_xml()
   │   ├─ Lee campos estructurados
   │   ├─ Calcula calidad (0.0-1.0)
   │   └─ Retorna: ("TEXTO XML", 0.67)
   │
   ├─→ extract_from_pdf()
   │   └─ Retorna: "TEXTO PDF"
   │
   ├─→ extract_combined()
   │   ├─ Calcula pesos dinámicos
   │   │   └─ XML: 60%, PDF: 40%
   │   └─ Retorna: {text, xml_weight, pdf_weight}
   │
   ▼
4. CLASIFICADOR (src/classifier.py)
   │
   ├─→ classify()
   │   │
   │   ├─→ Buscar keywords de sucursal
   │   │   ├─ Query: SELECT * FROM ocr_sucursal_keywords
   │   │   ├─ Match: "FLORENCIA" (peso: 9)
   │   │   ├─ Match: "SEDE FLORENCIA" (peso: 8)
   │   │   └─ Score total: 17
   │   │
   │   ├─→ Buscar keywords de unidad
   │   │   ├─ Query: SELECT * FROM ocr_unidad_keywords
   │   │   ├─ Match: "FLO MED" (peso: 10)
   │   │   ├─ Match: "FLORENCIA" (peso: 9)
   │   │   └─ Score total: 19
   │   │
   │   └─→ Retorna: (sucursal_info, unidad_info)
   │
   ▼
5. LEARNING SYSTEM (src/learning.py)
   │
   ├─→ save_classification()
   │   ├─ INSERT INTO ocr_clasificacion_historial
   │   └─ Retorna: historial_id = 123
   │
   ▼
6. API (src/api.py)
   │
   ├─→ Limpia archivos temporales
   │   └─ os.unlink(xml_path)
   │   └─ os.unlink(pdf_path)
   │
   ├─→ Retorna JSON response
   │   └─ {success, sucursal, unidad, historial_id}
   │
   ▼
7. CLIENTE (Node.js)
   │
   └─→ Recibe clasificación
       └─ Muestra al usuario para validación
```

### Flujo de Validación (Auto-aprendizaje)

```
1. USUARIO valida clasificación
   │
   ├─→ Opción A: "Correcto" ✅
   │   └─ es_correcta = true
   │
   └─→ Opción B: "Incorrecto" ❌
       ├─ es_correcta = false
       ├─ sucursal_correcta_id = 5
       └─ unidad_correcta_id = 10
   │
   ▼
2. CLIENTE envía POST /api/validate
   │
   ▼
3. LEARNING SYSTEM (src/learning.py)
   │
   ├─→ validate_and_learn()
   │   │
   │   ├─→ UPDATE ocr_clasificacion_historial
   │   │   └─ SET clasificacion_correcta = true/false
   │   │
   │   ├─→ SI es_correcta = true:
   │   │   └─→ _reinforce_keywords()
   │   │       ├─ UPDATE ocr_sucursal_keywords
   │   │       │   SET peso = peso + 1
   │   │       │   WHERE keyword IN (keywords_usadas)
   │   │       └─ Máximo peso: 10
   │   │
   │   └─→ SI es_correcta = false:
   │       └─→ _suggest_new_keywords()
   │           ├─ Analiza texto extraído
   │           ├─ Identifica palabras frecuentes
   │           └─ Retorna sugerencias
   │
   ▼
4. API retorna resultado
   │
   └─→ {keywords_reforzadas: 6, sugerencias: [...]}
```


---

## 🚀 INSTALACIÓN Y CONFIGURACIÓN

### Requisitos Previos

- Python 3.8+
- PostgreSQL 12+
- pip (gestor de paquetes Python)

### Paso 1: Instalar Dependencias

```bash
pip install -r requirements.txt
```

**Dependencias Instaladas**:
- `psycopg2-binary==2.9.9` - Conexión a PostgreSQL
- `pdfplumber==0.10.3` - Extracción de texto de PDF
- `fastapi==0.104.1` - Framework API REST
- `uvicorn[standard]==0.24.0` - Servidor ASGI
- `python-multipart==0.0.6` - Manejo de archivos multipart
- `python-dotenv==1.0.0` - Variables de entorno
- `requests==2.31.0` - Cliente HTTP (testing)

### Paso 2: Configurar Base de Datos

```bash
# Crear estructura de tablas
psql -U postgres -d veritask_manager -f database/schema.sql

# Insertar keywords iniciales
psql -U postgres -d veritask_manager -f database/keywords.sql

# Insertar keywords administrativas
psql -U postgres -d veritask_manager -f database/add_admin_keywords.sql
```

### Paso 3: Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Base de Datos PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=tu_password
DB_NAME=veritask_manager

# API (opcional)
API_HOST=0.0.0.0
API_PORT=8000

# CORS (opcional)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Paso 4: Iniciar API

```bash
# Modo desarrollo (con auto-reload)
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# Modo producción (con Gunicorn)
gunicorn src.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Paso 5: Verificar Instalación

```bash
# Probar clasificación con factura de ejemplo
python scripts/test_api.py

# O probar endpoint de salud
curl http://localhost:8000/api/health
```

---

## 📡 RUTAS Y ENDPOINTS DETALLADOS

### Base URL
```
http://localhost:8000
```

### Documentación Interactiva
```
http://localhost:8000/docs          # Swagger UI
http://localhost:8000/redoc         # ReDoc
```

---

### 1. GET /

**Descripción**: Endpoint raíz con información del servicio.

**Respuesta**:
```json
{
  "service": "OCR Classification API",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "classify": "/api/classify",
    "validate": "/api/validate",
    "stats": "/api/stats",
    "health": "/api/health"
  }
}
```

---

### 2. GET /api/health

**Descripción**: Verifica estado del servicio y conexión a base de datos.

**Respuesta Exitosa**:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

**Respuesta Error** (503):
```json
{
  "detail": "Service unhealthy: connection refused"
}
```

---

### 3. POST /api/classify

**Descripción**: Clasifica una factura usando XML y/o PDF.

**Content-Type**: `multipart/form-data`

**Parámetros**:
| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| xml_file | File | No* | Archivo XML de la factura |
| pdf_file | File | No* | Archivo PDF de la factura |
| factura_id | Integer | No | ID de la factura en tu sistema |

*Al menos uno de los archivos (XML o PDF) es requerido.

**Ejemplo de Request (cURL)**:
```bash
curl -X POST "http://localhost:8000/api/classify" \
  -F "xml_file=@factura.xml" \
  -F "pdf_file=@factura.pdf" \
  -F "factura_id=12345"
```

**Ejemplo de Request (JavaScript)**:
```javascript
const formData = new FormData();
formData.append('xml_file', xmlFile);
formData.append('pdf_file', pdfFile);
formData.append('factura_id', 12345);

const response = await fetch('http://localhost:8000/api/classify', {
  method: 'POST',
  body: formData
});

const result = await response.json();
```

**Respuesta Exitosa** (200):
```json
{
  "success": true,
  "sucursal": {
    "id": 3,
    "nombre": "Clinica Medilaser S.A.S - Florencia",
    "codigo": "FLA",
    "score": 24,
    "keywords": ["FLORENCIA", "SEDE FLORENCIA", "MEDILASER"]
  },
  "unidad_funcional": {
    "id": 8,
    "nombre": "Almacén - FLA",
    "codigo": "0055",
    "score": 35,
    "keywords": ["FLO MED", "FLORENCIA", "FACTURACION MAOS"]
  },
  "historial_id": 123,
  "metadata": {
    "xml_quality": 0.67,
    "xml_weight": 0.6,
    "pdf_weight": 0.4,
    "has_xml": true,
    "has_pdf": true
  }
}
```

**Respuesta Error** (400):
```json
{
  "detail": "Debe proporcionar al menos un archivo (XML o PDF)"
}
```

**Respuesta Error** (400):
```json
{
  "detail": "No se pudo extraer texto de los archivos"
}
```

---

### 4. POST /api/validate

**Descripción**: Valida una clasificación y permite al sistema aprender.

**Content-Type**: `application/json`

**Body**:
```json
{
  "historial_id": 123,
  "es_correcta": true,
  "sucursal_correcta_id": null,
  "unidad_correcta_id": null,
  "observaciones": "Clasificación correcta"
}
```

**Parámetros**:
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| historial_id | Integer | Sí | ID del historial (retornado por /classify) |
| es_correcta | Boolean | Sí | Si la clasificación fue correcta |
| sucursal_correcta_id | Integer | No | ID de sucursal correcta (si es_correcta=false) |
| unidad_correcta_id | Integer | No | ID de unidad correcta (si es_correcta=false) |
| observaciones | String | No | Comentarios adicionales |

**Ejemplo de Request (JavaScript)**:
```javascript
// Clasificación correcta
await fetch('http://localhost:8000/api/validate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    historial_id: 123,
    es_correcta: true,
    observaciones: "Perfecto"
  })
});

// Clasificación incorrecta
await fetch('http://localhost:8000/api/validate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    historial_id: 123,
    es_correcta: false,
    sucursal_correcta_id: 5,
    unidad_correcta_id: 10,
    observaciones: "Debería ser Neiva"
  })
});
```

**Respuesta Exitosa (Correcta)** (200):
```json
{
  "success": true,
  "message": "Clasificación correcta - Keywords reforzadas",
  "keywords_reforzadas": 6,
  "sugerencias": []
}
```

**Respuesta Exitosa (Incorrecta)** (200):
```json
{
  "success": true,
  "message": "Clasificación incorrecta - Sugerencias generadas",
  "keywords_reforzadas": 0,
  "sugerencias": [
    {
      "keyword": "NEIVA",
      "tipo": "sucursal",
      "id": 5,
      "peso_sugerido": 5
    }
  ]
}
```

---

### 5. GET /api/stats

**Descripción**: Obtiene estadísticas del sistema de clasificación.

**Respuesta** (200):
```json
{
  "total_clasificaciones": 150,
  "correctas": 142,
  "incorrectas": 8,
  "precision": 94.67,
  "confianza_promedio": {
    "sucursal": 28.5,
    "unidad": 35.2
  }
}
```

---

### 6. GET /api/keywords/sucursales/{sucursal_id}

**Descripción**: Obtiene todas las keywords de una sucursal específica.

**Parámetros**:
- `sucursal_id` (path): ID de la sucursal

**Ejemplo**:
```bash
GET http://localhost:8000/api/keywords/sucursales/3
```

**Respuesta** (200):
```json
{
  "success": true,
  "sucursal_id": 3,
  "keywords": [
    {
      "keyword": "FLORENCIA",
      "peso": 9,
      "activo": true
    },
    {
      "keyword": "SEDE FLORENCIA",
      "peso": 8,
      "activo": true
    }
  ]
}
```

---

### 7. GET /api/keywords/unidades/{unidad_id}

**Descripción**: Obtiene todas las keywords de una unidad funcional.

**Parámetros**:
- `unidad_id` (path): ID de la unidad funcional

**Ejemplo**:
```bash
GET http://localhost:8000/api/keywords/unidades/8
```

**Respuesta** (200):
```json
{
  "success": true,
  "unidad_id": 8,
  "keywords": [
    {
      "keyword": "FLO MED",
      "peso": 10,
      "activo": true
    },
    {
      "keyword": "FLORENCIA",
      "peso": 9,
      "activo": true
    }
  ]
}
```


---

## 💡 EJEMPLOS DE USO

### Ejemplo 1: Clasificación Básica (Node.js + Axios)

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

async function clasificarFactura() {
  const formData = new FormData();
  formData.append('xml_file', fs.createReadStream('./factura.xml'));
  formData.append('pdf_file', fs.createReadStream('./factura.pdf'));
  formData.append('factura_id', 12345);
  
  try {
    const response = await axios.post(
      'http://localhost:8000/api/classify',
      formData,
      { headers: formData.getHeaders() }
    );
    
    const { sucursal, unidad_funcional, historial_id } = response.data;
    
    console.log('Sucursal:', sucursal.nombre);
    console.log('Unidad:', unidad_funcional.nombre);
    console.log('Historial ID:', historial_id);
    
    return response.data;
  } catch (error) {
    console.error('Error:', error.response?.data);
    throw error;
  }
}

clasificarFactura();
```

### Ejemplo 2: Flujo Completo con Validación

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

class OCRClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
  }
  
  async clasificar(xmlPath, pdfPath, facturaId) {
    const formData = new FormData();
    
    if (xmlPath) {
      formData.append('xml_file', fs.createReadStream(xmlPath));
    }
    
    if (pdfPath) {
      formData.append('pdf_file', fs.createReadStream(pdfPath));
    }
    
    if (facturaId) {
      formData.append('factura_id', facturaId);
    }
    
    const response = await axios.post(
      `${this.baseURL}/api/classify`,
      formData,
      { headers: formData.getHeaders() }
    );
    
    return response.data;
  }
  
  async validar(historialId, esCorrecta, sucursalId = null, unidadId = null, observaciones = null) {
    const response = await axios.post(
      `${this.baseURL}/api/validate`,
      {
        historial_id: historialId,
        es_correcta: esCorrecta,
        sucursal_correcta_id: sucursalId,
        unidad_correcta_id: unidadId,
        observaciones: observaciones
      }
    );
    
    return response.data;
  }
  
  async obtenerEstadisticas() {
    const response = await axios.get(`${this.baseURL}/api/stats`);
    return response.data;
  }
}

// Uso
(async () => {
  const client = new OCRClient();
  
  // 1. Clasificar factura
  const resultado = await client.clasificar(
    './factura.xml',
    './factura.pdf',
    12345
  );
  
  console.log('Clasificación:', resultado);
  
  // 2. Mostrar al usuario y esperar validación
  // ... (lógica de UI)
  
  // 3. Usuario confirma que es correcta
  await client.validar(resultado.historial_id, true, null, null, 'Correcto');
  
  // 4. Ver estadísticas
  const stats = await client.obtenerEstadisticas();
  console.log('Precisión del sistema:', stats.precision + '%');
})();
```

### Ejemplo 3: Integración con Express.js

```javascript
const express = require('express');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const app = express();
const upload = multer({ dest: 'uploads/' });

// Endpoint para clasificar factura
app.post('/facturas/clasificar', 
  upload.fields([
    { name: 'xml_file', maxCount: 1 },
    { name: 'pdf_file', maxCount: 1 }
  ]),
  async (req, res) => {
    try {
      const formData = new FormData();
      
      if (req.files.xml_file) {
        formData.append('xml_file', 
          fs.createReadStream(req.files.xml_file[0].path)
        );
      }
      
      if (req.files.pdf_file) {
        formData.append('pdf_file', 
          fs.createReadStream(req.files.pdf_file[0].path)
        );
      }
      
      if (req.body.factura_id) {
        formData.append('factura_id', req.body.factura_id);
      }
      
      // Llamar al servicio OCR
      const response = await axios.post(
        'http://localhost:8000/api/classify',
        formData,
        { headers: formData.getHeaders() }
      );
      
      // Limpiar archivos temporales
      if (req.files.xml_file) {
        fs.unlinkSync(req.files.xml_file[0].path);
      }
      if (req.files.pdf_file) {
        fs.unlinkSync(req.files.pdf_file[0].path);
      }
      
      res.json(response.data);
      
    } catch (error) {
      console.error('Error:', error);
      res.status(500).json({ 
        error: 'Error al clasificar factura',
        details: error.response?.data 
      });
    }
  }
);

// Endpoint para validar clasificación
app.post('/facturas/validar', express.json(), async (req, res) => {
  try {
    const response = await axios.post(
      'http://localhost:8000/api/validate',
      req.body
    );
    
    res.json(response.data);
    
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ 
      error: 'Error al validar clasificación',
      details: error.response?.data 
    });
  }
});

app.listen(3000, () => {
  console.log('Servidor Node.js corriendo en puerto 3000');
});
```

### Ejemplo 4: Script Python para Clasificación Masiva

```python
import os
import sys
from pathlib import Path
from src.config import get_db_config
from src.classifier import PDFClassifier
from src.extractor import InvoiceExtractor

def clasificar_carpeta(carpeta_path):
    """Clasifica todas las facturas en una carpeta"""
    extractor = InvoiceExtractor()
    classifier = PDFClassifier(get_db_config())
    
    carpeta = Path(carpeta_path)
    resultados = []
    
    for subfolder in carpeta.iterdir():
        if not subfolder.is_dir():
            continue
        
        # Buscar XML y PDF
        xml_files = list(subfolder.glob("*.xml"))
        pdf_files = list(subfolder.glob("*.pdf"))
        
        xml_path = str(xml_files[0]) if xml_files else None
        pdf_path = str(pdf_files[0]) if pdf_files else None
        
        if not xml_path and not pdf_path:
            continue
        
        print(f"\nProcesando: {subfolder.name}")
        
        # Extraer y clasificar
        data = extractor.extract_combined(xml_path, pdf_path)
        sucursal, unidad = classifier.classify(
            data['text'],
            xml_weight=data['xml_weight'],
            pdf_weight=data['pdf_weight']
        )
        
        resultado = {
            'carpeta': subfolder.name,
            'sucursal': sucursal['nombre'] if sucursal['success'] else 'No detectada',
            'unidad': unidad['nombre'] if unidad['success'] else 'No detectada',
            'score_sucursal': sucursal['score'],
            'score_unidad': unidad['score']
        }
        
        resultados.append(resultado)
        
        print(f"  Sucursal: {resultado['sucursal']} (score: {resultado['score_sucursal']})")
        print(f"  Unidad: {resultado['unidad']} (score: {resultado['score_unidad']})")
    
    # Resumen
    print(f"\n{'='*80}")
    print(f"RESUMEN: {len(resultados)} facturas procesadas")
    exitosas = sum(1 for r in resultados if r['score_sucursal'] > 0 and r['score_unidad'] > 0)
    print(f"Exitosas: {exitosas}/{len(resultados)} ({exitosas/len(resultados)*100:.1f}%)")
    
    return resultados

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python clasificar_masivo.py <carpeta>")
        sys.exit(1)
    
    clasificar_carpeta(sys.argv[1])
```

---

## 🔍 CASOS DE USO

### Caso 1: Sistema de Facturación Automática

**Escenario**: Una empresa recibe cientos de facturas diarias y necesita clasificarlas automáticamente.

**Flujo**:
1. Usuario sube factura (XML + PDF) desde frontend
2. Backend Node.js envía archivos a `/api/classify`
3. Sistema OCR clasifica automáticamente
4. Si confianza > 70%, se acepta automáticamente
5. Si confianza < 70%, se envía a revisión manual
6. Usuario valida clasificación
7. Sistema aprende y mejora

**Código**:
```javascript
async function procesarFactura(xmlFile, pdfFile) {
  // Clasificar
  const resultado = await clasificar(xmlFile, pdfFile);
  
  // Decisión automática
  if (resultado.sucursal.score >= 70 && resultado.unidad_funcional.score >= 60) {
    // Aceptar automáticamente
    await guardarEnBaseDatos(resultado);
    await validar(resultado.historial_id, true);
    return { status: 'auto', resultado };
  } else {
    // Enviar a revisión manual
    await enviarARevision(resultado);
    return { status: 'manual', resultado };
  }
}
```

### Caso 2: Migración de Facturas Históricas

**Escenario**: Migrar 10,000 facturas antiguas clasificándolas automáticamente.

**Flujo**:
1. Script Python lee carpeta con facturas
2. Procesa cada factura en lote
3. Guarda resultados en CSV
4. Importa a base de datos principal

**Código**: Ver Ejemplo 4 arriba

### Caso 3: Dashboard de Monitoreo

**Escenario**: Dashboard en tiempo real mostrando precisión del sistema.

**Flujo**:
1. Frontend consulta `/api/stats` cada 30 segundos
2. Muestra gráficos de precisión
3. Alerta si precisión < 90%

**Código**:
```javascript
async function actualizarDashboard() {
  const stats = await fetch('http://localhost:8000/api/stats')
    .then(r => r.json());
  
  document.getElementById('precision').textContent = stats.precision + '%';
  document.getElementById('total').textContent = stats.total_clasificaciones;
  
  if (stats.precision < 90) {
    mostrarAlerta('Precisión baja: ' + stats.precision + '%');
  }
}

setInterval(actualizarDashboard, 30000);
```


---

## 🧪 TESTING

### Prueba Rápida

```bash
# Probar con factura de ejemplo
python scripts/test_api.py
```

**Salida Esperada**:
```
================================================================================
PRUEBA DE CLASIFICACIÓN XML + PDF
================================================================================

📋 XML: ejemplos/z09012928260082500000039/ad09012928260082500000039.xml
📄 PDF: ejemplos/z09012928260082500000039/fv09012928260082500000039.pdf

📊 EXTRACCIÓN:
   ✅ XML: 1234 caracteres (calidad: 67%)
   ⚖️  Peso XML: 60%
   ✅ PDF: 5678 caracteres
   ⚖️  Peso PDF: 40%

🏢 SUCURSAL:
   ✅ Clinica Medilaser S.A.S - Florencia
   📊 Score: 24
   🔑 Keywords: FLORENCIA, SEDE FLORENCIA

📦 UNIDAD FUNCIONAL:
   ✅ Almacén - FLA
   📊 Score: 35
   🔑 Keywords: FLO MED, FLORENCIA

================================================================================
RESULTADO
================================================================================
✅ CLASIFICACIÓN EXITOSA
   Sucursal: Clinica Medilaser S.A.S - Florencia
   Unidad: Almacén - FLA
   Fuentes: XML (60%) + PDF (40%)
```

### Prueba de API con cURL

```bash
# Health check
curl http://localhost:8000/api/health

# Clasificar factura
curl -X POST "http://localhost:8000/api/classify" \
  -F "xml_file=@ejemplos/z09012928260082500000039/ad09012928260082500000039.xml" \
  -F "pdf_file=@ejemplos/z09012928260082500000039/fv09012928260082500000039.pdf"

# Obtener estadísticas
curl http://localhost:8000/api/stats
```

### Tests Automatizados

```bash
# Ejecutar todos los tests
pytest tests/

# Test específico
pytest tests/test_api_integration.py
pytest tests/test_extraction.py
```

---

## 🛠️ MANTENIMIENTO

### Agregar Nuevas Keywords

**Opción 1: Directamente en Base de Datos**
```sql
-- Agregar keyword para sucursal
INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso) 
VALUES (3, 'NUEVA KEYWORD', 8);

-- Agregar keyword para unidad funcional
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso) 
VALUES (8, 'NUEVA KEYWORD', 7);
```

**Opción 2: Desde Sugerencias del Sistema**
Cuando una clasificación es incorrecta, el sistema sugiere keywords automáticamente.

### Ajustar Pesos de Keywords

```sql
-- Aumentar peso de keyword efectiva
UPDATE ocr_sucursal_keywords 
SET peso = 10 
WHERE keyword = 'FLORENCIA' AND sucursal_id = 3;

-- Disminuir peso de keyword poco efectiva
UPDATE ocr_unidad_keywords 
SET peso = 3 
WHERE keyword = 'HOSPITALIARIA';
```

### Desactivar Keywords

```sql
-- Desactivar keyword sin eliminarla
UPDATE ocr_sucursal_keywords 
SET activo = FALSE 
WHERE keyword = 'KEYWORD_OBSOLETA';
```

### Limpiar Historial Antiguo

```sql
-- Eliminar registros de más de 6 meses
DELETE FROM ocr_clasificacion_historial 
WHERE created_at < NOW() - INTERVAL '6 months';

-- O archivar en tabla histórica
INSERT INTO ocr_clasificacion_historial_archivo 
SELECT * FROM ocr_clasificacion_historial 
WHERE created_at < NOW() - INTERVAL '6 months';
```

### Backup de Base de Datos

```bash
# Backup completo
pg_dump -U postgres veritask_manager > backup_$(date +%Y%m%d).sql

# Backup solo de keywords
pg_dump -U postgres -t ocr_sucursal_keywords -t ocr_unidad_keywords veritask_manager > keywords_backup.sql

# Restaurar backup
psql -U postgres veritask_manager < backup_20241209.sql
```

### Monitoreo de Logs

```bash
# Ver logs de uvicorn
tail -f logs/uvicorn.log

# Ver logs de errores
grep "ERROR" logs/uvicorn.log

# Ver clasificaciones fallidas
psql -U postgres -d veritask_manager -c "
  SELECT archivo_nombre, created_at 
  FROM ocr_clasificacion_historial 
  WHERE sucursal_detectada_id IS NULL 
  ORDER BY created_at DESC 
  LIMIT 10;
"
```

---

## 🚨 TROUBLESHOOTING

### Problema: "Connection refused" al llamar API

**Causa**: API no está corriendo.

**Solución**:
```bash
# Verificar si está corriendo
curl http://localhost:8000/api/health

# Iniciar API
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

### Problema: "Database connection failed"

**Causa**: Credenciales incorrectas o PostgreSQL no está corriendo.

**Solución**:
```bash
# Verificar PostgreSQL
sudo systemctl status postgresql

# Iniciar PostgreSQL
sudo systemctl start postgresql

# Verificar credenciales en .env
cat .env

# Probar conexión manual
psql -U postgres -d veritask_manager -c "SELECT 1;"
```

### Problema: "No se pudo extraer texto"

**Causa**: Archivos XML/PDF corruptos o formato no soportado.

**Solución**:
```bash
# Verificar archivo XML
xmllint --noout factura.xml

# Verificar archivo PDF
pdfinfo factura.pdf

# Probar extracción manual
python -c "
from src.extractor import InvoiceExtractor
ext = InvoiceExtractor()
data = ext.extract_combined('factura.xml', 'factura.pdf')
print(data)
"
```

### Problema: Clasificación siempre incorrecta

**Causa**: Keywords insuficientes o pesos incorrectos.

**Solución**:
```sql
-- Ver keywords actuales
SELECT * FROM ocr_sucursal_keywords WHERE sucursal_id = 3;

-- Ver historial de clasificaciones
SELECT 
  archivo_nombre,
  sucursal_detectada_id,
  keywords_encontradas,
  clasificacion_correcta
FROM ocr_clasificacion_historial
ORDER BY created_at DESC
LIMIT 10;

-- Agregar más keywords
INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso) 
VALUES (3, 'NUEVA_KEYWORD', 8);
```

### Problema: Precisión baja (< 80%)

**Causa**: Sistema necesita más entrenamiento.

**Solución**:
1. Validar más clasificaciones usando `/api/validate`
2. Revisar keywords sugeridas por el sistema
3. Agregar keywords manualmente
4. Aumentar pesos de keywords efectivas

```sql
-- Ver estadísticas detalladas
SELECT 
  clasificacion_correcta,
  COUNT(*) as total,
  AVG(confianza_sucursal) as avg_confianza
FROM ocr_clasificacion_historial
WHERE clasificacion_correcta IS NOT NULL
GROUP BY clasificacion_correcta;
```

### Problema: API muy lenta

**Causa**: Archivos PDF muy grandes o muchas keywords.

**Solución**:
```python
# Configurar timeout en .env
TIMEOUT_PROCESAMIENTO_MS=30000

# Limitar tamaño de archivos
MAX_FILE_SIZE_MB=10

# Optimizar keywords (eliminar duplicados)
DELETE FROM ocr_sucursal_keywords 
WHERE id NOT IN (
  SELECT MIN(id) 
  FROM ocr_sucursal_keywords 
  GROUP BY sucursal_id, keyword
);
```

---

## 📊 MÉTRICAS Y KPIs

### Métricas Principales

1. **Precisión Global**: % de clasificaciones correctas
   ```sql
   SELECT 
     ROUND(
       COUNT(CASE WHEN clasificacion_correcta = true THEN 1 END) * 100.0 / 
       COUNT(*), 2
     ) as precision
   FROM ocr_clasificacion_historial
   WHERE clasificacion_correcta IS NOT NULL;
   ```

2. **Confianza Promedio**: Score promedio de clasificaciones
   ```sql
   SELECT 
     AVG(confianza_sucursal) as avg_sucursal,
     AVG(confianza_unidad) as avg_unidad
   FROM ocr_clasificacion_historial;
   ```

3. **Tasa de Clasificación Automática**: % de facturas con confianza > 70%
   ```sql
   SELECT 
     COUNT(CASE WHEN confianza_sucursal >= 70 THEN 1 END) * 100.0 / 
     COUNT(*) as tasa_automatica
   FROM ocr_clasificacion_historial;
   ```

4. **Tiempo de Procesamiento**: Tiempo promedio por factura
   ```sql
   SELECT AVG(tiempo_procesamiento_ms) as avg_tiempo_ms
   FROM ocr_clasificacion_historial;
   ```

### Dashboard SQL

```sql
-- Dashboard completo
SELECT 
  COUNT(*) as total_clasificaciones,
  COUNT(CASE WHEN clasificacion_correcta = true THEN 1 END) as correctas,
  COUNT(CASE WHEN clasificacion_correcta = false THEN 1 END) as incorrectas,
  ROUND(
    COUNT(CASE WHEN clasificacion_correcta = true THEN 1 END) * 100.0 / 
    NULLIF(COUNT(CASE WHEN clasificacion_correcta IS NOT NULL THEN 1 END), 0), 
    2
  ) as precision,
  ROUND(AVG(confianza_sucursal), 2) as avg_confianza_sucursal,
  ROUND(AVG(confianza_unidad), 2) as avg_confianza_unidad,
  COUNT(CASE WHEN confianza_sucursal >= 70 AND confianza_unidad >= 60 THEN 1 END) as alta_confianza,
  ROUND(AVG(tiempo_procesamiento_ms), 0) as avg_tiempo_ms
FROM ocr_clasificacion_historial;
```

---

## 🔐 SEGURIDAD

### Recomendaciones de Producción

1. **CORS Específico**
   ```python
   # En src/api.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://tudominio.com"],  # No usar "*"
       allow_credentials=True,
       allow_methods=["POST", "GET"],
       allow_headers=["*"],
   )
   ```

2. **Autenticación API**
   ```python
   from fastapi import Header, HTTPException
   
   async def verify_token(x_api_key: str = Header(...)):
       if x_api_key != os.getenv("API_KEY"):
           raise HTTPException(status_code=401, detail="Invalid API Key")
   
   @app.post("/api/classify", dependencies=[Depends(verify_token)])
   async def classify_invoice(...):
       ...
   ```

3. **Rate Limiting**
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   
   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   
   @app.post("/api/classify")
   @limiter.limit("10/minute")
   async def classify_invoice(...):
       ...
   ```

4. **Validación de Archivos**
   ```python
   MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
   ALLOWED_EXTENSIONS = {'.xml', '.pdf'}
   
   def validate_file(file: UploadFile):
       # Verificar extensión
       ext = Path(file.filename).suffix.lower()
       if ext not in ALLOWED_EXTENSIONS:
           raise HTTPException(400, "Formato no permitido")
       
       # Verificar tamaño
       file.file.seek(0, 2)
       size = file.file.tell()
       file.file.seek(0)
       if size > MAX_FILE_SIZE:
           raise HTTPException(400, "Archivo muy grande")
   ```

5. **HTTPS en Producción**
   ```bash
   # Con Nginx como proxy reverso
   server {
       listen 443 ssl;
       server_name api.tudominio.com;
       
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       
       location / {
           proxy_pass http://localhost:8000;
       }
   }
   ```

---

## 📈 ESCALABILIDAD

### Optimizaciones para Alto Volumen

1. **Caché de Resultados**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def classify_cached(text_hash):
       return classifier.classify(text)
   ```

2. **Procesamiento Asíncrono**
   ```python
   from celery import Celery
   
   celery = Celery('ocr', broker='redis://localhost:6379')
   
   @celery.task
   def classify_async(xml_path, pdf_path):
       # Procesar en background
       ...
   ```

3. **Múltiples Workers**
   ```bash
   # Con Gunicorn
   gunicorn src.api:app \
     -w 4 \
     -k uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000
   ```

4. **Base de Datos Optimizada**
   ```sql
   -- Índices adicionales
   CREATE INDEX idx_historial_fecha ON ocr_clasificacion_historial(created_at DESC);
   CREATE INDEX idx_keywords_peso ON ocr_sucursal_keywords(peso DESC);
   
   -- Particionamiento por fecha
   CREATE TABLE ocr_clasificacion_historial_2024_12 
   PARTITION OF ocr_clasificacion_historial
   FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
   ```

---

## 📞 SOPORTE Y CONTACTO

### Recursos

- **Documentación API**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Repositorio**: [URL del repositorio]
- **Issues**: [URL de issues]

### Logs y Debugging

```bash
# Activar modo debug
export MODO_DEBUG=true

# Ver logs detallados
python -m uvicorn src.api:app --reload --log-level debug
```

### Contribuir

Para contribuir al proyecto:
1. Fork del repositorio
2. Crear branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m "Agregar nueva funcionalidad"`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

---

## 📝 CHANGELOG

### v1.0.0 (2024-12-09)
- ✅ Extracción de XML y PDF con pesos dinámicos
- ✅ Clasificación por keywords parametrizables
- ✅ Sistema de auto-aprendizaje
- ✅ API REST completa
- ✅ Integración con Node.js
- ✅ Historial de clasificaciones
- ✅ Estadísticas y métricas

### Próximas Funcionalidades
- 🔄 Procesamiento por lotes
- 🔄 Dashboard web de administración
- 🔄 Exportación de reportes
- 🔄 Integración con servicios de almacenamiento (S3, Azure)
- 🔄 Notificaciones por email/webhook
- 🔄 API de gestión de keywords

---

## 📄 LICENCIA

[Especificar licencia del proyecto]

---

**Última actualización**: 9 de Diciembre, 2024
**Versión**: 1.0.0
**Autor**: [Tu nombre/equipo]