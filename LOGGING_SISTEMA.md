# 📝 Sistema de Logging - OCR Classification API

## Descripción

Sistema completo de logging que registra todas las peticiones HTTP, archivos procesados, validaciones y errores del sistema OCR.

## 📊 Archivos de Log Generados

### 1. `logs/api_requests.log`
Registra **todas las peticiones HTTP** a cualquier endpoint del API.

**Información registrada:**
- Timestamp
- Endpoint (ruta)
- Método HTTP (GET, POST, etc)
- Código de respuesta (200, 400, 500, etc)
- Duración en milisegundos
- IP del cliente
- Datos adicionales en formato JSON

**Ejemplo:**
```
2024-12-11 10:30:45 - OCR_API - INFO - [POST] /api/classify - Status: 200 - Duration: 1234.56ms - Data: {"timestamp": "2024-12-11T10:30:45", "endpoint": "/api/classify", "method": "POST", "status_code": 200, "duration_ms": 1234.56, "client_ip": "127.0.0.1"}
```

### 2. `logs/processed_files.log`
Registra **todos los archivos de facturas procesados** (XML y PDF).

**Información registrada:**
- Timestamp
- ID de factura
- Nombre del archivo XML (si existe)
- Nombre del archivo PDF (si existe)
- Sucursal detectada
- Unidad funcional detectada
- Éxito del procesamiento
- ID del historial

**Ejemplo:**
```
2024-12-11 10:30:45 - OCR_FILES - INFO - Factura procesada - ID: 12345 - Archivos: XML: factura.xml + PDF: factura.pdf - Sucursal: Clinica Medilaser - Florencia - Unidad: Almacén - FLA - Success: True - Data: {...}
```

### 3. `logs/statistics.log`
Registra **consultas de estadísticas** del sistema.

**Información registrada:**
- Timestamp
- Total de clasificaciones
- Precisión del sistema
- Confianza promedio

**Ejemplo:**
```
2024-12-11 10:35:00 - OCR_STATS - INFO - Estadísticas consultadas - Total: 150 - Precisión: 94.67% - Data: {...}
```

## 🎯 Características del Sistema de Logging

### ✅ Logging Automático
- **Middleware HTTP**: Registra automáticamente todas las peticiones
- **Sin configuración adicional**: Funciona desde el primer request
- **Mensajes en consola**: Cada log muestra confirmación en pantalla

### ✅ Información Detallada
- **Peticiones HTTP**: Endpoint, método, status, duración, IP
- **Archivos procesados**: Nombres, tipos, resultados de clasificación
- **Validaciones**: Correctas/incorrectas, observaciones
- **Errores**: Tipo, mensaje, traceback completo

### ✅ Múltiples Niveles
- **INFO**: Operaciones normales
- **WARNING**: Clasificaciones incorrectas, validaciones fallidas
- **ERROR**: Errores de procesamiento, excepciones

### ✅ Formato Estructurado
- **Timestamp**: Fecha y hora exacta
- **Logger name**: Identifica el tipo de log
- **Level**: INFO, WARNING, ERROR
- **Message**: Descripción legible
- **Data**: JSON con información completa

## 📡 Nuevo Endpoint: GET /api/logs

Obtiene un resumen de todos los logs del sistema.

**URL**: `http://localhost:8000/api/logs`

**Método**: GET

**Respuesta**:
```json
{
  "success": true,
  "peticiones_por_endpoint": {
    "/": 5,
    "/api/health": 3,
    "/api/classify": 10,
    "/api/validate": 8,
    "/api/stats": 2
  },
  "archivos_procesados": {
    "total_facturas": 10,
    "con_xml": 8,
    "con_pdf": 9,
    "con_ambos": 7,
    "exitosas": 9,
    "fallidas": 1
  },
  "archivos_log": {
    "api_requests": "logs/api_requests.log",
    "processed_files": "logs/processed_files.log",
    "statistics": "logs/statistics.log"
  }
}
```

## 🚀 Uso

### Iniciar el servidor
```bash
python run.py
```

El sistema de logging se activa automáticamente.

### Probar el sistema de logging
```bash
python scripts/test_logging.py
```

Este script:
1. Hace peticiones a todos los endpoints
2. Procesa una factura de ejemplo
3. Valida la clasificación
4. Muestra el resumen de logs

### Ver logs en tiempo real

**Windows (PowerShell):**
```powershell
Get-Content logs/api_requests.log -Wait
Get-Content logs/processed_files.log -Wait
```

**Windows (CMD):**
```cmd
type logs\api_requests.log
type logs\processed_files.log
```

**Linux/Mac:**
```bash
tail -f logs/api_requests.log
tail -f logs/processed_files.log
```

## 📋 Ejemplos de Logs

### Petición exitosa
```
2024-12-11 10:30:45 - OCR_API - INFO - [POST] /api/classify - Status: 200 - Duration: 1234.56ms - Data: {"timestamp": "2024-12-11T10:30:45", "endpoint": "/api/classify", "method": "POST", "status_code": 200, "duration_ms": 1234.56, "client_ip": "127.0.0.1"}
✅ Log guardado: /api/classify [POST] - 200
```

### Archivo procesado
```
2024-12-11 10:30:45 - OCR_FILES - INFO - Factura procesada - ID: 12345 - Archivos: XML: factura.xml + PDF: factura.pdf - Sucursal: Clinica Medilaser - Florencia - Unidad: Almacén - FLA - Success: True
✅ Log de archivo guardado: Factura 12345 - XML: factura.xml + PDF: factura.pdf
```

### Validación correcta
```
2024-12-11 10:31:00 - OCR_API - INFO - Validación - Historial ID: 123 - CORRECTA ✓
✅ Log de validación guardado: Historial 123 - CORRECTA ✓
```

### Validación incorrecta
```
2024-12-11 10:31:15 - OCR_API - WARNING - Validación - Historial ID: 124 - INCORRECTA ✗
✅ Log de validación guardado: Historial 124 - INCORRECTA ✗
```

### Error
```
2024-12-11 10:32:00 - OCR_API - ERROR - ERROR en /api/classify - No se pudo extraer texto de los archivos
❌ Log de error guardado: /api/classify - No se pudo extraer texto de los archivos
```

## 🔍 Análisis de Logs

### Contar peticiones por endpoint
```python
from src.logger import ocr_logger

counts = ocr_logger.get_request_count()
print(counts)
# {'/', 5, '/api/classify': 10, '/api/health': 3}
```

### Estadísticas de archivos procesados
```python
from src.logger import ocr_logger

stats = ocr_logger.get_file_processing_count()
print(stats)
# {
#   'total_facturas': 10,
#   'con_xml': 8,
#   'con_pdf': 9,
#   'con_ambos': 7,
#   'exitosas': 9,
#   'fallidas': 1
# }
```

## 📊 Integración con Herramientas de Monitoreo

Los logs están en formato estándar y pueden integrarse con:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk**
- **Datadog**
- **Grafana + Loki**
- **CloudWatch** (AWS)

## 🔧 Configuración Avanzada

### Cambiar nivel de logging
```python
# En src/logger.py
self.logger.setLevel(logging.DEBUG)  # Más detallado
self.logger.setLevel(logging.WARNING)  # Solo warnings y errores
```

### Rotación de logs
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'logs/api_requests.log',
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5  # Mantener 5 archivos
)
```

### Logs en JSON puro
```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage()
        })
```

## 📈 Métricas Disponibles

El sistema registra:

1. **Peticiones HTTP**
   - Total por endpoint
   - Códigos de respuesta
   - Tiempos de respuesta
   - IPs de clientes

2. **Archivos Procesados**
   - Total de facturas
   - Archivos XML vs PDF
   - Tasa de éxito
   - Clasificaciones por sucursal/unidad

3. **Validaciones**
   - Correctas vs incorrectas
   - Keywords reforzadas
   - Sugerencias generadas

4. **Errores**
   - Tipos de error
   - Endpoints afectados
   - Tracebacks completos

## 🎯 Casos de Uso

### Monitoreo en producción
```bash
# Ver últimas 50 líneas
type logs\api_requests.log | Select-Object -Last 50

# Buscar errores
Select-String -Path logs\api_requests.log -Pattern "ERROR"

# Contar peticiones exitosas
(Select-String -Path logs\api_requests.log -Pattern "Status: 200").Count
```

### Análisis de rendimiento
```bash
# Buscar peticiones lentas (>2000ms)
Select-String -Path logs\api_requests.log -Pattern "Duration: [2-9][0-9]{3}"
```

### Auditoría de archivos
```bash
# Ver todas las facturas procesadas
type logs\processed_files.log

# Buscar facturas fallidas
Select-String -Path logs\processed_files.log -Pattern "Success: False"
```

## ✅ Ventajas del Sistema

1. **Trazabilidad completa**: Cada operación queda registrada
2. **Debugging facilitado**: Logs detallados con tracebacks
3. **Análisis de uso**: Estadísticas de endpoints y archivos
4. **Auditoría**: Registro de todas las validaciones
5. **Monitoreo**: Detección de errores y problemas
6. **Optimización**: Identificar endpoints lentos

## 🔒 Consideraciones de Seguridad

- ❌ **No registrar**: Contraseñas, tokens, datos sensibles
- ✅ **Registrar**: IPs, timestamps, resultados de operaciones
- ✅ **Rotar logs**: Evitar archivos muy grandes
- ✅ **Permisos**: Restringir acceso a archivos de log

## 📞 Soporte

Para más información sobre el sistema de logging:
- Ver código fuente: `src/logger.py`
- Ejecutar pruebas: `python scripts/test_logging.py`
- Consultar API: `GET /api/logs`
