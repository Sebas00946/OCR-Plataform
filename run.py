"""
Script para iniciar el servidor API
"""
import uvicorn
import os

if __name__ == "__main__":
    # Obtener configuración del entorno
    environment = os.getenv('ENVIRONMENT', 'development')
    debug = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"🚀 Iniciando servidor en modo: {environment}")
    print(f"📍 Host: {host}:{port}")
    print(f"🐛 Debug: {debug}")
    
    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=debug,  # Solo reload en desarrollo
        log_level="debug" if debug else "info"
    )
