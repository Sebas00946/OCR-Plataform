# 📚 Índice de Documentación - OCR API

Bienvenido a la documentación completa del proyecto OCR API integrado con Veritask Manager.

## 🚀 Inicio Rápido

¿Primera vez aquí? Empieza por estos documentos:

1. **[QUICKSTART.md](QUICKSTART.md)** - Guía rápida de 5 minutos
2. **[README.md](README.md)** - Documentación principal completa
3. **[README_VERITASK.md](README_VERITASK.md)** - Integración con Veritask Manager

## 📖 Documentación por Tema

### 🎯 Conceptos Básicos

- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Resumen ejecutivo del proyecto
  - Descripción general
  - Arquitectura
  - Características principales
  - Casos de uso

### 🔧 Instalación y Configuración

- **[QUICKSTART.md](QUICKSTART.md)** - Instalación rápida
  - Pre-requisitos
  - Instalación en 5 pasos
  - Primera prueba
  - Troubleshooting básico

- **[README.md](README.md)** - Instalación completa
  - Instalación con Docker
  - Instalación local
  - Configuración detallada
  - Ejemplos de uso

- **[WINDOWS_SETUP.md](WINDOWS_SETUP.md)** - Guía específica para Windows
  - Instalación de Tesseract en Windows
  - Configuración de PATH
  - Scripts .bat para Windows
  - Troubleshooting Windows

### 🗄️ Base de Datos

- **[README_VERITASK.md](README_VERITASK.md)** - Integración con Veritask Manager
  - Conexión a veritask_manager
  - Estructura de tabla ocr_jobs
  - Scripts de configuración
  - Consultas SQL útiles
  - Relación con tablas existentes

- **[scripts/create_ocr_tables.sql](scripts/create_ocr_tables.sql)** - Script SQL
  - Creación de tipos ENUM
  - Creación de tabla ocr_jobs
  - Índices y triggers
  - Comentarios de documentación

### 🏗️ Arquitectura

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Arquitectura del sistema
  - Arquitectura hexagonal
  - Capas del sistema
  - Patrones de diseño
  - Flujo de datos
  - Tecnologías por capa
  - Escalabilidad
  - Seguridad

### 🚀 Despliegue

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Guía de despliegue
  - Despliegue con Docker Compose
  - Despliegue en VPS
  - Despliegue en Kubernetes
  - Despliegue en AWS ECS
  - Configuración de Nginx
  - SSL con Let's Encrypt
  - Monitoreo y logs
  - Backups

### 📝 Ejemplos y Scripts

#### Ejemplos de Uso

- **[examples/python_client.py](examples/python_client.py)** - Cliente Python
  - Clase OCRClient completa
  - Ejemplos de uso
  - Manejo de errores
  - Espera de resultados

- **[examples/curl_examples.sh](examples/curl_examples.sh)** - Ejemplos con curl
  - Procesar imagen
  - Procesar PDF
  - Procesamiento por lotes
  - Consultar estado
  - Obtener resultados

#### Scripts de Utilidad

- **[scripts/setup_database.py](scripts/setup_database.py)** - Configurar base de datos
  - Verificar conexión
  - Crear ENUMs
  - Crear tablas
  - Crear índices

- **[scripts/cleanup.py](scripts/cleanup.py)** - Limpieza de archivos
  - Eliminar trabajos antiguos
  - Limpiar archivos temporales
  - Automatización con cron

- **[scripts/test_ocr.py](scripts/test_ocr.py)** - Probar OCR localmente
  - Crear imagen de prueba
  - Probar diferentes calidades
  - Ver resultados

- **[scripts/init_db.py](scripts/init_db.py)** - Inicializar base de datos
  - Script simple de inicialización

#### Scripts para Windows

- **[start_all.bat](start_all.bat)** - Iniciar todos los servicios
  - Inicia Redis
  - Inicia API
  - Inicia Celery Worker
  - Abre documentación

- **[stop_all.bat](stop_all.bat)** - Detener todos los servicios
  - Detiene API y Worker
  - Detiene Redis

### 🔧 Configuración

- **[.env.example](.env.example)** - Ejemplo de configuración
  - Variables de aplicación
  - Configuración de base de datos
  - Configuración de OCR
  - Seguridad
  - Límites y timeouts

- **[docker-compose.yml](docker-compose.yml)** - Configuración Docker producción
  - Servicios: API, Celery, Redis
  - Volúmenes
  - Redes
  - Health checks

- **[docker-compose.dev.yml](docker-compose.dev.yml)** - Configuración Docker desarrollo
  - Hot reload
  - Logs detallados
  - Montaje de código fuente

- **[Dockerfile](Dockerfile)** - Imagen Docker
  - Instalación de Tesseract
  - Dependencias del sistema
  - Configuración de Python

### 📦 Dependencias

- **[requirements.txt](requirements.txt)** - Dependencias Python
  - FastAPI y Uvicorn
  - Tesseract y procesamiento
  - Celery y Redis
  - SQLAlchemy y PostgreSQL
  - Testing

### 🧪 Testing

- **[tests/test_api.py](tests/test_api.py)** - Tests de API
  - Health check
  - Endpoints OCR
  - Autenticación
  - Validación

- **[tests/test_ocr_service.py](tests/test_ocr_service.py)** - Tests de servicio OCR
  - Procesamiento de imágenes
  - Diferentes calidades
  - Fixtures

- **[pytest.ini](pytest.ini)** - Configuración de pytest

### 📋 Otros Archivos

- **[Makefile](Makefile)** - Comandos útiles
  - make install
  - make dev
  - make test
  - make docker-up/down

- **[alembic.ini](alembic.ini)** - Configuración de migraciones
  - Configuración de Alembic
  - Logging

- **[.gitignore](.gitignore)** - Archivos ignorados por Git
- **[.dockerignore](.dockerignore)** - Archivos ignorados por Docker

## 🎓 Rutas de Aprendizaje

### Para Desarrolladores Nuevos

1. Lee [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) para entender el proyecto
2. Sigue [QUICKSTART.md](QUICKSTART.md) para instalación rápida
3. Revisa [ARCHITECTURE.md](ARCHITECTURE.md) para entender la estructura
4. Explora [examples/python_client.py](examples/python_client.py) para ver ejemplos

### Para Administradores de Sistemas

1. Lee [DEPLOYMENT.md](DEPLOYMENT.md) para opciones de despliegue
2. Revisa [docker-compose.yml](docker-compose.yml) para configuración
3. Consulta [README_VERITASK.md](README_VERITASK.md) para integración con BD
4. Configura monitoreo según [DEPLOYMENT.md](DEPLOYMENT.md)

### Para Usuarios de Windows

1. Sigue [WINDOWS_SETUP.md](WINDOWS_SETUP.md) paso a paso
2. Usa [start_all.bat](start_all.bat) para iniciar servicios
3. Consulta troubleshooting en [WINDOWS_SETUP.md](WINDOWS_SETUP.md)

### Para Integración con Veritask

1. Lee [README_VERITASK.md](README_VERITASK.md) completamente
2. Ejecuta [scripts/setup_database.py](scripts/setup_database.py)
3. Revisa [scripts/create_ocr_tables.sql](scripts/create_ocr_tables.sql)
4. Consulta ejemplos de consultas SQL en [README_VERITASK.md](README_VERITASK.md)

## 🔍 Búsqueda Rápida

### Por Tema

| Tema | Documento |
|------|-----------|
| Instalación rápida | [QUICKSTART.md](QUICKSTART.md) |
| Instalación completa | [README.md](README.md) |
| Windows | [WINDOWS_SETUP.md](WINDOWS_SETUP.md) |
| Base de datos | [README_VERITASK.md](README_VERITASK.md) |
| Arquitectura | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Despliegue | [DEPLOYMENT.md](DEPLOYMENT.md) |
| Resumen | [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) |

### Por Tarea

| Tarea | Documento/Script |
|-------|------------------|
| Crear tablas OCR | [scripts/setup_database.py](scripts/setup_database.py) |
| Probar OCR | [scripts/test_ocr.py](scripts/test_ocr.py) |
| Limpiar archivos | [scripts/cleanup.py](scripts/cleanup.py) |
| Cliente Python | [examples/python_client.py](examples/python_client.py) |
| Ejemplos curl | [examples/curl_examples.sh](examples/curl_examples.sh) |
| Iniciar en Windows | [start_all.bat](start_all.bat) |

### Por Problema

| Problema | Solución |
|----------|----------|
| Error de conexión a BD | [README_VERITASK.md](README_VERITASK.md) - Troubleshooting |
| Tesseract no encontrado | [WINDOWS_SETUP.md](WINDOWS_SETUP.md) - Instalación Tesseract |
| Tabla no existe | [scripts/setup_database.py](scripts/setup_database.py) |
| Error en Windows | [WINDOWS_SETUP.md](WINDOWS_SETUP.md) - Troubleshooting |
| Configuración Docker | [docker-compose.yml](docker-compose.yml) |

## 📊 Estructura de Código Fuente

```
src/
├── domain/                    # Lógica de negocio
│   ├── entities.py           # Entidades del dominio
│   ├── repositories.py       # Interfaces de repositorios
│   ├── services.py           # Interfaces de servicios
│   └── exceptions.py         # Excepciones personalizadas
├── infrastructure/           # Implementaciones
│   ├── database.py          # SQLAlchemy
│   ├── repositories_impl.py # Repositorios
│   ├── ocr_service_impl.py  # Servicio OCR
│   ├── storage_service_impl.py # Almacenamiento
│   └── tasks.py             # Celery
├── presentation/            # API REST
│   ├── routers/            # Endpoints
│   │   ├── ocr.py         # Rutas OCR
│   │   └── health.py      # Health check
│   ├── schemas.py         # Modelos Pydantic
│   ├── dependencies.py    # Inyección de dependencias
│   └── middleware.py      # Middleware
├── config.py              # Configuración
└── main.py               # Punto de entrada
```

## 🌐 Enlaces Externos

- **Documentación API**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Tesseract OCR**: https://github.com/tesseract-ocr/tesseract
- **FastAPI**: https://fastapi.tiangolo.com/
- **Celery**: https://docs.celeryproject.org/
- **Docker**: https://docs.docker.com/

## 📞 Soporte

Para problemas o preguntas:

1. Revisa la sección de Troubleshooting en el documento relevante
2. Consulta [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Problemas Comunes
3. Revisa los logs: `docker-compose logs -f`
4. Abre un issue en GitHub

## 🔄 Actualizaciones

Este índice se actualiza con cada nueva versión del proyecto. Última actualización: 2024

---

**Tip**: Usa Ctrl+F (Cmd+F en Mac) para buscar términos específicos en este índice.
