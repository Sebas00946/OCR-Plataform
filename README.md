# OCR API - Extracción Profesional de Texto

API REST profesional para extracción de texto desde imágenes y PDFs usando OCR (Reconocimiento Óptico de Caracteres), integrada con **Veritask Manager**.

> 📚 **[Ver Índice Completo de Documentación](INDEX.md)** | 🚀 **[Guía Rápida de Inicio](QUICKSTART.md)** | 🗄️ **[Integración con Veritask](README_VERITASK.md)**

## 🚀 Características

- **API REST con FastAPI**: Endpoints RESTful bien documentados
- **Soporte multi-idioma**: Español, inglés y más idiomas
- **Procesamiento de imágenes**: PNG, JPG, JPEG, WEBP
- **Procesamiento de PDFs**: 
  - PDFs con texto seleccionable (extracción directa)
  - PDFs escaneados (usando OCR)
- **Preprocesamiento inteligente**: Mejora automática de calidad de imagen
- **Procesamiento asíncrono**: Cola de tareas con Celery y Redis
- **Tres niveles de calidad**: Rápido, balanceado, preciso
- **Procesamiento por lotes**: Múltiples archivos simultáneamente
- **Historial completo**: Seguimiento de todos los trabajos
- **Autenticación con API Keys**: Seguridad integrada
- **Rate Limiting**: Prevención de abuso
- **Documentación automática**: Swagger UI y ReDoc

## 📋 Requisitos

- **Base de datos PostgreSQL existente**: `veritask_manager`
- Docker y Docker Compose (para Redis y servicios)
- O alternativamente:
  - Python 3.11+
  - PostgreSQL 15+ (con base de datos veritask_manager)
  - Redis 7+
  - Tesseract OCR

> **Nota**: Este proyecto se integra con la base de datos existente `veritask_manager`. No crea una nueva base de datos, sino que agrega tablas al schema `public` existente.

## 🛠️ Instalación

### Configuración Inicial

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd ocr-api
```

2. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con las credenciales de tu base de datos veritask_manager
nano .env
```

Asegúrate de configurar correctamente:
```bash
DATABASE_URL=postgresql://tu_usuario:tu_password@localhost:5432/veritask_manager
```

3. **Crear tablas OCR en veritask_manager**
```bash
# Opción A: Script Python (Recomendado)
python scripts/setup_database.py

# Opción B: Script SQL
psql -U postgres -d veritask_manager -f scripts/create_ocr_tables.sql
```

Este paso crea la tabla `ocr_jobs` en el schema `public` de tu base de datos existente.

### Opción 1: Docker (Recomendado)

4. **Iniciar servicios con Docker**
```bash
# Para desarrollo
docker-compose -f docker-compose.dev.yml up -d

# Para producción
docker-compose up -d
```

5. **Verificar que está funcionando**
```bash
curl http://localhost:8000/api/v1/health
```

La API estará disponible en `http://localhost:8000`

> **Nota**: Los contenedores Docker se conectan a tu base de datos PostgreSQL local usando `host.docker.internal`.

### Opción 2: Instalación Local (Sin Docker)

1. **Instalar Tesseract OCR**

En Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng poppler-utils
```

En macOS:
```bash
brew install tesseract tesseract-lang poppler
```

En Windows:
- Descargar desde: https://github.com/UB-Mannheim/tesseract/wiki
- Agregar al PATH

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar base de datos**
```bash
# Asegúrate de que PostgreSQL con veritask_manager está corriendo
python scripts/setup_database.py
```

5. **Iniciar Redis**
```bash
# Con Docker
docker run -d -p 6379:6379 redis:7-alpine

# O instalado localmente
redis-server
```

6. **Iniciar la API (Terminal 1)**
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

7. **Iniciar Celery Worker (Terminal 2)**
```bash
celery -A src.infrastructure.tasks.celery_app worker --loglevel=info
```

## 📖 Uso de la API

### Documentación Interactiva

Una vez iniciada la API, accede a:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Autenticación

Incluye tu API key en el header `X-API-Key` en todas las peticiones:

```bash
X-API-Key: your-secret-api-key-here
```

### Ejemplos de Uso

#### 1. Health Check

```bash
curl http://localhost:8000/api/v1/health
```

#### 2. Procesar una Imagen

```bash
curl -X POST "http://localhost:8000/api/v1/ocr/image" \
  -H "X-API-Key: your-secret-api-key-here" \
  -F "file=@imagen.png" \
  -F "language=spa+eng" \
  -F "quality=balanced"
```

Respuesta:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "imagen.png",
  "file_type": "image",
  "file_size": 245678,
  "status": "pending",
  "created_at": "2024-01-15T10:30:00",
  "language": "spa+eng",
  "quality": "balanced"
}
```

#### 3. Procesar un PDF

```bash
curl -X POST "http://localhost:8000/api/v1/ocr/pdf" \
  -H "X-API-Key: your-secret-api-key-here" \
  -F "file=@documento.pdf" \
  -F "language=spa" \
  -F "quality=accurate"
```

#### 4. Consultar Estado de un Trabajo

```bash
curl -X GET "http://localhost:8000/api/v1/ocr/jobs/{job_id}" \
  -H "X-API-Key: your-secret-api-key-here"
```

#### 5. Obtener Resultado

```bash
curl -X GET "http://localhost:8000/api/v1/ocr/jobs/{job_id}/result" \
  -H "X-API-Key: your-secret-api-key-here"
```

Respuesta:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "Texto extraído del documento...",
  "confidence": 95.5,
  "processing_time": 2.34,
  "metadata": {
    "language": "spa+eng",
    "quality": "balanced",
    "word_count": 150
  }
}
```

#### 6. Procesamiento por Lotes

```bash
curl -X POST "http://localhost:8000/api/v1/ocr/batch" \
  -H "X-API-Key: your-secret-api-key-here" \
  -F "files=@imagen1.png" \
  -F "files=@imagen2.jpg" \
  -F "files=@documento.pdf" \
  -F "language=spa+eng" \
  -F "quality=balanced"
```

#### 7. Ver Historial

```bash
curl -X GET "http://localhost:8000/api/v1/ocr/history?skip=0&limit=10" \
  -H "X-API-Key: your-secret-api-key-here"
```

### Ejemplo con Python

```python
import requests

API_URL = "http://localhost:8000"
API_KEY = "your-secret-api-key-here"

headers = {"X-API-Key": API_KEY}

# Subir imagen
with open("imagen.png", "rb") as f:
    files = {"file": f}
    data = {
        "language": "spa+eng",
        "quality": "balanced"
    }
    response = requests.post(
        f"{API_URL}/api/v1/ocr/image",
        headers=headers,
        files=files,
        data=data
    )
    job = response.json()
    job_id = job["id"]
    print(f"Job creado: {job_id}")

# Esperar y obtener resultado
import time
while True:
    response = requests.get(
        f"{API_URL}/api/v1/ocr/jobs/{job_id}",
        headers=headers
    )
    status = response.json()["status"]
    print(f"Estado: {status}")
    
    if status == "completed":
        # Obtener resultado
        response = requests.get(
            f"{API_URL}/api/v1/ocr/jobs/{job_id}/result",
            headers=headers
        )
        result = response.json()
        print(f"Texto extraído: {result['text']}")
        print(f"Confianza: {result['confidence']}%")
        break
    elif status == "failed":
        print("Error en el procesamiento")
        break
    
    time.sleep(2)
```

## ⚙️ Configuración

### Variables de Entorno Principales

| Variable | Descripción | Valor por Defecto |
|----------|-------------|-------------------|
| `DATABASE_URL` | URL de conexión a PostgreSQL | `sqlite:///./ocr.db` |
| `REDIS_URL` | URL de conexión a Redis | `redis://localhost:6379/0` |
| `TESSERACT_CMD` | Ruta al ejecutable de Tesseract | `/usr/bin/tesseract` |
| `OCR_LANGUAGES` | Idiomas para OCR | `spa+eng` |
| `MAX_FILE_SIZE_MB` | Tamaño máximo de archivo | `50` |
| `API_KEY_ENABLED` | Habilitar autenticación | `True` |
| `API_KEYS` | API keys válidas (separadas por coma) | - |
| `RATE_LIMIT_REQUESTS` | Límite de peticiones | `100` |
| `RATE_LIMIT_PERIOD_SECONDS` | Período del límite | `3600` |

Ver `.env.example` para todas las opciones disponibles.

### Niveles de Calidad

- **fast**: Procesamiento rápido, menor precisión
- **balanced**: Balance entre velocidad y precisión (recomendado)
- **accurate**: Máxima precisión, más lento

### Idiomas Soportados

Configura los idiomas en formato Tesseract:
- `eng`: Inglés
- `spa`: Español
- `spa+eng`: Español e inglés
- `fra`: Francés
- `deu`: Alemán
- Y más...

## 🧪 Testing

### Ejecutar Tests

```bash
# Con pytest
pytest

# Con cobertura
pytest --cov=src --cov-report=html

# Tests específicos
pytest tests/test_api.py
pytest tests/test_ocr_service.py
```

## 📊 Monitoreo

### Logs

Los logs se generan en formato JSON estructurado:

```bash
# Ver logs de la API
docker-compose logs -f api

# Ver logs de Celery
docker-compose logs -f celery_worker
```

### Métricas

- Tiempo de procesamiento por trabajo
- Confianza promedio del OCR
- Tasa de éxito/fallo
- Tamaño de archivos procesados

## 🔒 Seguridad

- **Autenticación con API Keys**: Protege tus endpoints
- **Validación de archivos**: Verifica tipo MIME y extensión
- **Límite de tamaño**: Previene ataques de denegación de servicio
- **Rate Limiting**: Limita peticiones por cliente
- **CORS configurable**: Control de orígenes permitidos
- **Sanitización de inputs**: Validación con Pydantic

## 🚀 Despliegue en Producción

### Recomendaciones

1. **Usar PostgreSQL** en lugar de SQLite
2. **Configurar HTTPS** con certificados SSL
3. **Usar un proxy reverso** (Nginx, Traefik)
4. **Escalar workers de Celery** según carga
5. **Configurar backups** de la base de datos
6. **Monitorear recursos** (CPU, memoria, disco)
7. **Implementar logging centralizado** (ELK, Grafana)

### Ejemplo con Nginx

```nginx
server {
    listen 80;
    server_name api.tudominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🐛 Troubleshooting

### Tesseract no encontrado

```bash
# Verificar instalación
tesseract --version

# Configurar ruta en .env
TESSERACT_CMD=/usr/local/bin/tesseract
```

### Error de conexión a PostgreSQL

```bash
# Verificar que PostgreSQL está corriendo
docker-compose ps

# Ver logs
docker-compose logs postgres
```

### Celery no procesa trabajos

```bash
# Verificar que Redis está corriendo
docker-compose ps redis

# Reiniciar worker
docker-compose restart celery_worker
```

## 📝 Licencia

Este proyecto está bajo la licencia MIT.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📧 Soporte

Para reportar bugs o solicitar features, abre un issue en GitHub.

## 🙏 Agradecimientos

- [FastAPI](https://fastapi.tiangolo.com/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [Celery](https://docs.celeryproject.org/)
- [OpenCV](https://opencv.org/)
