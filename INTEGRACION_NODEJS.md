## 🚀 INTEGRACIÓN CON NODE.JS

Sistema OCR listo para integrarse con tu backend de Node.js

---

## 📋 CONFIGURACIÓN RÁPIDA

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar Base de Datos

El archivo `.env` ya está configurado:
```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=0946
DB_NAME=veritask_manager
```

### 3. Iniciar API

```bash
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en: `http://localhost:8000`

---

## 📡 ENDPOINTS DISPONIBLES

### 1. **Clasificar Factura** (Principal)

```http
POST /api/classify
Content-Type: multipart/form-data
```

**Parámetros:**
- `xml_file`: Archivo XML (opcional)
- `pdf_file`: Archivo PDF (opcional)
- `factura_id`: ID de la factura en tu sistema (opcional)

**Respuesta:**
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
  "metadata": {
    "xml_quality": 0.5,
    "xml_weight": 0.6,
    "pdf_weight": 0.4,
    "has_xml": true,
    "has_pdf": true
  }
}
```

### 2. **Validar Clasificación** (Auto-aprendizaje)

```http
POST /api/validate
Content-Type: application/json
```

**Body:**
```json
{
  "historial_id": 123,
  "es_correcta": true,
  "sucursal_correcta_id": null,
  "unidad_correcta_id": null,
  "observaciones": "Clasificación correcta"
}
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Keywords reforzadas exitosamente",
  "learning": {
    "weights_adjusted": true,
    "keywords_suggested": [],
    "message": "Keywords reforzadas exitosamente"
  }
}
```

### 3. **Estadísticas**

```http
GET /api/stats
```

**Respuesta:**
```json
{
  "success": true,
  "stats": {
    "total_clasificaciones": 150,
    "correctas": 142,
    "incorrectas": 8,
    "precision": 94.67,
    "confianza_promedio": {
      "sucursal": 28.5,
      "unidad": 35.2
    }
  }
}
```

### 4. **Health Check**

```http
GET /api/health
```

---

## 💻 EJEMPLO DE INTEGRACIÓN EN NODE.JS

### Usando Axios

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

// Clasificar factura
async function clasificarFactura(xmlPath, pdfPath, facturaId) {
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
  
  try {
    const response = await axios.post(
      'http://localhost:8000/api/classify',
      formData,
      {
        headers: formData.getHeaders()
      }
    );
    
    return response.data;
  } catch (error) {
    console.error('Error al clasificar:', error.response?.data);
    throw error;
  }
}

// Validar clasificación
async function validarClasificacion(historialId, esCorrecta, observaciones) {
  try {
    const response = await axios.post(
      'http://localhost:8000/api/validate',
      {
        historial_id: historialId,
        es_correcta: esCorrecta,
        observaciones: observaciones
      }
    );
    
    return response.data;
  } catch (error) {
    console.error('Error al validar:', error.response?.data);
    throw error;
  }
}

// Uso
(async () => {
  // Clasificar
  const resultado = await clasificarFactura(
    './factura.xml',
    './factura.pdf',
    12345
  );
  
  console.log('Sucursal:', resultado.sucursal.nombre);
  console.log('Unidad:', resultado.unidad_funcional.nombre);
  
  // Validar (después de que el usuario confirme)
  await validarClasificacion(
    resultado.historial_id,
    true,
    'Clasificación correcta'
  );
})();
```

### Usando Fetch (Nativo)

```javascript
const FormData = require('form-data');
const fs = require('fs');

async function clasificarFactura(xmlPath, pdfPath) {
  const formData = new FormData();
  
  if (xmlPath) {
    formData.append('xml_file', fs.createReadStream(xmlPath));
  }
  
  if (pdfPath) {
    formData.append('pdf_file', fs.createReadStream(pdfPath));
  }
  
  const response = await fetch('http://localhost:8000/api/classify', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}
```

---

## 🤖 SISTEMA DE AUTO-APRENDIZAJE

### Cómo Funciona

1. **Usuario clasifica factura** → Sistema guarda en historial
2. **Usuario valida resultado** → Sistema aprende:
   - ✅ Si es correcta: aumenta peso de keywords (+1)
   - ❌ Si es incorrecta: sugiere nuevas keywords

### Flujo Recomendado

```javascript
// 1. Clasificar factura
const clasificacion = await clasificarFactura(xml, pdf, facturaId);

// 2. Mostrar al usuario para validación
mostrarEnUI(clasificacion);

// 3. Usuario valida (botón "Correcto" o "Incorrecto")
if (usuarioConfirma) {
  await validarClasificacion(historialId, true);
  // Sistema refuerza keywords automáticamente
} else {
  // Usuario corrige manualmente
  const sucursalCorrecta = usuarioSelecciona();
  await validarClasificacion(
    historialId,
    false,
    sucursalCorrecta.id,
    unidadCorrecta.id
  );
  // Sistema sugiere nuevas keywords
}
```

---

## 📊 MONITOREO

### Ver Estadísticas

```javascript
const stats = await axios.get('http://localhost:8000/api/stats');
console.log(`Precisión: ${stats.data.stats.precision}%`);
```

### Ver Keywords de una Sucursal

```javascript
const keywords = await axios.get(
  'http://localhost:8000/api/keywords/sucursales/3'
);
console.log(keywords.data.keywords);
```

---

## 🔧 CONFIGURACIÓN AVANZADA

### Variables de Entorno

```env
# API
API_HOST=0.0.0.0
API_PORT=8000

# Base de Datos
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=0946
DB_NAME=veritask_manager

# CORS (para Node.js)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Iniciar en Producción

```bash
# Con Gunicorn (recomendado)
gunicorn src.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Con PM2 (Node.js)
pm2 start "uvicorn src.api:app --host 0.0.0.0 --port 8000" --name ocr-api
```

---

## ✅ CHECKLIST DE INTEGRACIÓN

- [ ] Instalar dependencias Python
- [ ] Configurar `.env` con credenciales correctas
- [ ] Iniciar API en puerto 8000
- [ ] Probar endpoint `/api/health`
- [ ] Probar clasificación con factura de prueba
- [ ] Integrar en tu backend de Node.js
- [ ] Implementar validación de usuario
- [ ] Monitorear estadísticas

---

## 🆘 TROUBLESHOOTING

**Error: Connection refused**
→ Verificar que la API esté corriendo en puerto 8000

**Error: Database connection failed**
→ Verificar credenciales en `.env`

**Error: No se pudo extraer texto**
→ Verificar que los archivos XML/PDF sean válidos

**Clasificación incorrecta**
→ Usar endpoint `/api/validate` para que el sistema aprenda

---

## 📞 SOPORTE

- Documentación API: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/health`
- Logs: Revisar consola donde corre uvicorn