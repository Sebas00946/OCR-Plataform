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
Sube XML y/o PDF para clasificar automáticamente.

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

### Prueba completa de API
```bash
python test_api_complete.py
```

## 📊 Características

- ✅ Lee XML (60%) + PDF (40%) con pesos inteligentes
- ✅ Clasifica sucursal y unidad funcional automáticamente
- ✅ Sistema de auto-aprendizaje
- ✅ Keywords parametrizables en base de datos
- ✅ API REST lista para Node.js
- ✅ Historial completo de clasificaciones

## 📁 Estructura del Proyecto

```
OCR-Plataform/
├── src/
│   ├── api.py              # API REST principal
│   ├── classifier.py       # Clasificador con keywords
│   ├── extractor.py        # Extractor XML + PDF
│   ├── learning.py         # Sistema de auto-aprendizaje
│   └── config.py           # Configuración
├── database/
│   ├── schema.sql          # Estructura de BD
│   ├── keywords.sql        # Keywords iniciales
│   └── add_admin_keywords.sql
├── scripts/
│   ├── test_api.py         # Prueba rápida
│   └── classify.py         # Clasificación directa
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

El sistema mejora automáticamente:
- ✅ **Clasificación correcta**: Aumenta peso de keywords (+1)
- ❌ **Clasificación incorrecta**: Sugiere nuevas keywords

## 🔒 Producción

Para producción, configurar:
- CORS específico en `src/api.py`
- Variables de entorno seguras
- Servidor HTTPS
- Monitoreo y logs
- Backup de base de datos

## 📞 Soporte

- **Documentación API**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Integración Node.js**: Ver `INTEGRACION_NODEJS.md`
