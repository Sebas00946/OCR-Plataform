# Sistema OCR - Clasificación Automática de Facturas

Sistema de clasificación automática de facturas que lee XML + PDF y aprende de las validaciones del usuario.

## 🚀 Inicio Rápido

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar base de datos
```bash
# Crear tablas
psql -U postgres -d veritask_manager -f database/schema.sql

# Insertar keywords
psql -U postgres -d veritask_manager -f database/keywords.sql
psql -U postgres -d veritask_manager -f database/add_admin_keywords.sql
```

### 3. Configurar variables de entorno
Crear archivo `.env`:
```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=tu_password
DB_NAME=veritask_manager
```

### 4. Iniciar API
```bash
python -m uvicorn src.api:app --reload
```

API disponible en: `http://localhost:8000`  
Documentación: `http://localhost:8000/docs`

## 📡 Endpoints Principales

### Clasificar Factura
```bash
POST /api/classify
```
Sube XML y/o PDF para clasificar automáticamente y extraer datos del proveedor y valores monetarios.

**Respuesta incluye:**
- Datos del proveedor (nombre, NIT, ciudad)
- Número de factura, fecha, CUFE
- **Valores monetarios**: subtotal, IVA, retenciones, valor neto 💰
- Clasificación (sucursal y unidad funcional)

### Validar Clasificación (Auto-aprendizaje)
```bash
POST /api/validate
```
Valida una clasificación y el sistema aprende automáticamente.

### Estadísticas
```bash
GET /api/stats
```
Obtiene estadísticas del sistema.

### Logs del Sistema
```bash
GET /api/logs
```
Obtiene resumen de logs y archivos procesados.

### Health Check
```bash
GET /api/health
```
Verifica estado del servicio.

## 🔧 Integración con Node.js

Ver documentación completa en: [INTEGRACION_NODEJS.md](INTEGRACION_NODEJS.md)

### Ejemplo básico
```javascript
const FormData = require('form-data');
const fs = require('fs');

async function clasificarFactura(xmlPath, pdfPath) {
  const formData = new FormData();
  formData.append('xml_file', fs.createReadStream(xmlPath));
  formData.append('pdf_file', fs.createReadStream(pdfPath));
  
  const response = await fetch('http://localhost:8000/api/classify', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}
```

## 🧪 Pruebas

### Prueba rápida
```bash
python scripts/test_api.py
```

### Prueba del sistema de logging
```bash
python scripts/test_logging.py
```

### Prueba de extracción de proveedor
```bash
python scripts/test_proveedor.py
```

### Prueba de extracción de valores monetarios 💰
```bash
# Demo completo del sistema (recomendado)
python scripts/demo_completo.py

# Extraer valores de cualquier factura
python scripts/extraer_valores.py <ruta_xml> [ruta_pdf]

# Ejemplo
python scripts/extraer_valores.py ejemplos/FQE142584/ad09004334370002500036584.xml
```

### Prueba completa de API
```bash
python test_api_complete.py
```

## 📊 Características

- ✅ Lee XML (60%) + PDF (40%) con pesos inteligentes
- ✅ Clasifica sucursal y unidad funcional automáticamente
- ✅ Extrae datos del proveedor (nombre, NIT, dirección, ciudad, teléfono, email)
- ✅ **Extrae valores monetarios** (subtotal, IVA, retenciones, valor neto) 💰
- ✅ Sistema de auto-aprendizaje
- ✅ Keywords parametrizables en base de datos
- ✅ API REST lista para Node.js
- ✅ Historial completo de clasificaciones
- ✅ Sistema de logging completo (peticiones, archivos, errores)
- ✅ Monitoreo en tiempo real

## 📁 Estructura del Proyecto

```
OCR-Plataform/
├── src/
│   ├── api.py              # API REST principal
│   ├── classifier.py       # Clasificador con keywords
│   ├── extractor.py        # Extractor XML + PDF
│   ├── learning.py         # Sistema de auto-aprendizaje
│   ├── logger.py           # Sistema de logging
│   └── config.py           # Configuración
├── database/
│   ├── schema.sql          # Estructura de BD
│   ├── keywords.sql        # Keywords iniciales
│   └── add_admin_keywords.sql
├── scripts/
│   ├── test_api.py         # Prueba rápida
│   ├── test_logging.py     # Prueba de logging
│   └── classify.py         # Clasificación directa
├── logs/                   # Logs del sistema
│   ├── api_requests.log    # Peticiones HTTP
│   ├── processed_files.log # Archivos procesados
│   └── statistics.log      # Estadísticas
├── ejemplos/               # Facturas de ejemplo
├── test_api_complete.py    # Prueba completa
└── requirements.txt        # Dependencias
```

## 🎯 Cómo Funciona

1. **Extracción**: Lee XML (datos estructurados) y PDF (contexto adicional)
2. **Clasificación**: Busca keywords en el texto combinado con pesos
3. **Aprendizaje**: Guarda en historial y aprende de validaciones
4. **Mejora continua**: Keywords se refuerzan automáticamente

## 📈 Auto-aprendizaje

El sistema mejora automáticamente de dos formas:

### 1. Validación Manual (API)
- ✅ **Clasificación correcta**: Aumenta peso de keywords (+1)
- ❌ **Clasificación incorrecta**: Sugiere nuevas keywords

### 2. Auto-aprendizaje Masivo (Buzón Compartido)

Sistema automatizado que procesa correos del buzón compartido para entrenar el OCR.

**📁 Ubicación**: `auto_learning/`

**Uso rápido:**
```bash
# Prueba (10 correos)
python auto_learning/test_auto_learning.py

# Procesamiento completo (~52,942 correos, 36-40 horas)
python auto_learning/auto_learning_from_mailbox.py
```

**Características:**
- ✅ Procesa ~52,942 correos del 2025 automáticamente
- ✅ Extrae XML/PDF de archivos ZIP
- ✅ Aprende de clasificaciones manuales en carpetas
- ✅ Guarda progreso cada 50 correos (puede reanudar)
- ✅ Verifica duplicados por CUFE
- ✅ Manejo robusto de errores

**Ver documentación completa**: `auto_learning/README.md`

## 🔒 Producción

Para producción, configurar:
- CORS específico en `src/api.py`
- Variables de entorno seguras
- Servidor HTTPS
- Monitoreo y logs
- Backup de base de datos

## 📝 Sistema de Logging

El sistema registra automáticamente:
- ✅ Todas las peticiones HTTP (endpoint, método, status, duración)
- ✅ Archivos procesados (XML, PDF, resultados)
- ✅ Validaciones (correctas/incorrectas)
- ✅ Errores con traceback completo

**Ver logs en tiempo real:**
```bash
# Windows PowerShell
Get-Content logs/api_requests.log -Wait

# Ver resumen de logs
curl http://localhost:8000/api/logs
```

**Documentación completa**: Ver `LOGGING_SISTEMA.md`

## 📞 Soporte

- **Documentación API**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Logs del Sistema**: http://localhost:8000/api/logs

**📚 Documentación:**
- **⭐ Guía Node.js - Valores**: `GUIA_NODEJS_VALORES.md` - **EMPIEZA AQUÍ** 💰
- **📋 Índice General**: `INDICE_DOCUMENTACION.md` - Ver toda la documentación
- **Resumen para Node.js**: `RESUMEN_PARA_NODEJS.md`
- **Guía completa Node.js**: `GUIA_INTEGRACION_NODEJS.md`
- **Arquitectura del Sistema**: `ARQUITECTURA_SISTEMA.md`
- **Extracción de Proveedor**: `EXTRACCION_PROVEEDOR.md`
- **Extracción de Valores Monetarios**: `EXTRACCION_VALORES_MONETARIOS.md`
- **Sistema de Logging**: `LOGGING_SISTEMA.md`
- **Resumen de Clasificación**: `RESUMEN_CLASIFICACION.md`
