"""
Script para iniciar el servidor API
Producción: gunicorn con múltiples workers para manejar 500+ facturas/día
"""
import uvicorn
import os

if __name__ == "__main__":
    environment = os.getenv('ENVIRONMENT', 'development')
    debug = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', 'localhost')
    # En producción usar 2-4 workers (VPS 4 vCPU / 8GB RAM)
    workers = int(os.getenv('WORKERS', 1 if debug else 3))

    print(f"🚀 Iniciando servidor en modo: {environment}")
    print(f"📍 Host: {host}:{port}  Workers: {workers}")

    if debug:
        uvicorn.run(
            "src.api:app",
            host=host,
            port=port,
            reload=True,
            log_level="debug"
        )
    else:
        # Producción: múltiples workers con gunicorn
        # Cada worker carga su propia KnowledgeBase en RAM (~15MB c/u)
        uvicorn.run(
            "src.api:app",
            host=host,
            port=port,
            workers=workers,
            log_level="info",
            access_log=True,
        )
