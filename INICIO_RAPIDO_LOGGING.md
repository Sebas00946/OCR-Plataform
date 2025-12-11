# 🚀 Inicio Rápido - Sistema de Logging

## ⚡ En 3 Pasos

### 1️⃣ Iniciar el servidor
```bash
python run.py
```

El sistema de logging se activa **automáticamente**. No necesitas configurar nada.

### 2️⃣ Hacer peticiones al API
```bash
# Probar health check
curl http://localhost:8000/api/health

# Clasificar una factura
curl -X POST http://localhost:8000/api/classify \
  -F "xml_file=@factura.xml" \
  -F "pdf_file=@factura.pdf"
```

### 3️⃣ Ver los logs

**En consola:**
Verás mensajes como:
```
✅ Log guardado: /api/health [GET] - 200
✅ Log de archivo guardado: Factura 12345 - XML: factura.xml + PDF: factura.pdf
```

**En archivos:**
```bash
# Windows PowerShell
Get-Content logs/api_requests.log -Wait

# Windows CMD
type logs\api_requests.log
```

**Vía API:**
```bash
curl http://localhost:8000/api/logs
```

---

## 📊 ¿Qué se registra automáticamente?

### ✅ Todas las peticiones HTTP
- Endpoint y método (GET, POST, etc)
- Status code (200, 400, 500, etc)
- Duración en milisegundos
- IP del cliente

### ✅ Todos los archivos procesados
- ID de factura
- Archivos XML y PDF
- Sucursal y unidad detectadas
- Éxito o fallo

### ✅ Todas las validaciones
- Correctas o incorrectas
- Keywords reforzadas
- Observaciones del usuario

### ✅ Todos los errores
- Tipo de error
- Mensaje descriptivo
- Traceback completo

---

## 📁 Archivos de Log

Los logs se guardan automáticamente en:

```
logs/
├── api_requests.log      # Todas las peticiones HTTP
├── processed_files.log   # Todos los archivos procesados
└── statistics.log        # Consultas de estadísticas
```

---

## 🧪 Probar el Sistema

### Opción 1: Script de prueba automático
```bash
python scripts/test_logging.py
```

Este script:
- ✅ Prueba todos los endpoints
- ✅ Procesa una factura de ejemplo
- ✅ Valida la clasificación
- ✅ Muestra resumen de logs

### Opción 2: Prueba manual

**1. Health check:**
```bash
curl http://localhost:8000/api/health
```

**2. Clasificar factura:**
```bash
curl -X POST http://localhost:8000/api/classify \
  -F "xml_file=@ejemplos/z09012928260082500000039/ad09012928260082500000039.xml" \
  -F "pdf_file=@ejemplos/z09012928260082500000039/fv09012928260082500000039.pdf" \
  -F "factura_id=12345"
```

**3. Ver resumen de logs:**
```bash
curl http://localhost:8000/api/logs
```

---

## 📊 Consultar Estadísticas de Logs

### Vía API (recomendado):
```bash
curl http://localhost:8000/api/logs
```

**Respuesta:**
```json
{
  "success": true,
  "peticiones_por_endpoint": {
    "/": 5,
    "/api/classify": 10,
    "/api/validate": 8
  },
  "archivos_procesados": {
    "total_facturas": 10,
    "con_xml": 8,
    "con_pdf": 9,
    "exitosas": 9,
    "fallidas": 1
  }
}
```

### Vía Python:
```python
from src.logger import ocr_logger

# Contar peticiones
counts = ocr_logger.get_request_count()
print(f"Peticiones: {counts}")

# Estadísticas de archivos
stats = ocr_logger.get_file_processing_count()
print(f"Archivos procesados: {stats['total_facturas']}")
print(f"Exitosas: {stats['exitosas']}")
```

---

## 🔍 Buscar en Logs

### Windows PowerShell:

**Ver últimas 50 líneas:**
```powershell
Get-Content logs/api_requests.log | Select-Object -Last 50
```

**Buscar errores:**
```powershell
Select-String -Path logs/api_requests.log -Pattern "ERROR"
```

**Contar peticiones exitosas:**
```powershell
(Select-String -Path logs/api_requests.log -Pattern "Status: 200").Count
```

**Ver facturas procesadas:**
```powershell
Get-Content logs/processed_files.log
```

**Buscar facturas fallidas:**
```powershell
Select-String -Path logs/processed_files.log -Pattern "Success: False"
```

### Windows CMD:

**Ver archivo completo:**
```cmd
type logs\api_requests.log
type logs\processed_files.log
```

**Ver últimas líneas:**
```cmd
powershell "Get-Content logs/api_requests.log | Select-Object -Last 20"
```

---

## 💡 Ejemplos de Uso

### Monitorear en tiempo real
```powershell
# Ver logs en tiempo real
Get-Content logs/api_requests.log -Wait
```

### Analizar rendimiento
```powershell
# Buscar peticiones lentas (>2000ms)
Select-String -Path logs/api_requests.log -Pattern "Duration: [2-9][0-9]{3}"
```

### Auditoría de archivos
```powershell
# Ver todas las facturas procesadas hoy
$fecha = Get-Date -Format "yyyy-MM-dd"
Select-String -Path logs/processed_files.log -Pattern $fecha
```

### Detectar problemas
```powershell
# Ver todos los errores
Select-String -Path logs/api_requests.log -Pattern "ERROR"

# Ver clasificaciones fallidas
Select-String -Path logs/processed_files.log -Pattern "Success: False"
```

---

## 📝 Salida en Consola

Cuando el sistema está funcionando, verás mensajes como:

```
✅ Log guardado: /api/classify [POST] - 200
✅ Log de archivo guardado: Factura 12345 - XML: factura.xml + PDF: factura.pdf
✅ Log de validación guardado: Historial 123 - CORRECTA ✓
✅ Log de estadísticas guardado: Precisión 94.67%
❌ Log de error guardado: /api/classify - No se pudo extraer texto
```

Estos mensajes confirman que cada operación se está registrando correctamente.

---

## 🎯 Casos de Uso Comunes

### 1. Verificar que el sistema está funcionando
```bash
curl http://localhost:8000/api/health
# Verás: ✅ Log guardado: /api/health [GET] - 200
```

### 2. Ver cuántas facturas se han procesado
```bash
curl http://localhost:8000/api/logs
# Verás: "total_facturas": 10
```

### 3. Detectar errores recientes
```powershell
Select-String -Path logs/api_requests.log -Pattern "ERROR" | Select-Object -Last 10
```

### 4. Analizar tiempos de respuesta
```powershell
Select-String -Path logs/api_requests.log -Pattern "Duration:" | Select-Object -Last 20
```

### 5. Ver qué endpoints son más usados
```bash
curl http://localhost:8000/api/logs
# Verás: "peticiones_por_endpoint": {...}
```

---

## 🔧 Configuración (Opcional)

El sistema funciona sin configuración, pero puedes personalizar:

### Cambiar nivel de logging
```python
# En src/logger.py, línea 30
self.logger.setLevel(logging.DEBUG)  # Más detallado
self.logger.setLevel(logging.WARNING)  # Solo warnings y errores
```

### Cambiar ubicación de logs
```python
# En src/logger.py, línea 15
LOGS_DIR = Path("mi_carpeta_logs")
```

---

## 📚 Documentación Completa

- **Guía detallada**: `LOGGING_SISTEMA.md`
- **Resumen de implementación**: `RESUMEN_LOGGING.md`
- **Ejemplo de salida**: `EJEMPLO_LOGS_CONSOLA.txt`
- **README principal**: `README.md`

---

## ✅ Checklist Rápido

- [ ] Servidor iniciado (`python run.py`)
- [ ] Hacer una petición de prueba
- [ ] Ver mensaje de confirmación en consola
- [ ] Verificar que se creó la carpeta `logs/`
- [ ] Abrir `logs/api_requests.log` y ver el registro
- [ ] Consultar resumen con `curl http://localhost:8000/api/logs`

---

## 🎉 ¡Listo!

El sistema de logging está funcionando. Cada operación se registra automáticamente y puedes consultarlos cuando quieras.

**¿Necesitas ayuda?**
- Ver documentación completa: `LOGGING_SISTEMA.md`
- Ejecutar pruebas: `python scripts/test_logging.py`
- Consultar API: `http://localhost:8000/docs`
