"""
Configuración de base de datos PostgreSQL y aplicación
"""
import os
from dotenv import load_dotenv
from typing import List

# Cargar variables de entorno según el entorno
environment = os.getenv('ENVIRONMENT', 'development')

# Cargar .env base
load_dotenv()

# Cargar .env específico del entorno (sobrescribe valores)
if environment == 'production':
    load_dotenv('.env.production', override=True)
elif environment == 'development':
    load_dotenv('.env.development', override=True)


def get_db_config():
    """
    Obtiene la configuración de PostgreSQL desde variables de entorno
    
    Returns:
        dict: Configuración de conexión a PostgreSQL
    """
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'veritask_manager')
    }


def get_cors_origins() -> List[str]:
    """
    Obtiene los orígenes permitidos para CORS
    
    Returns:
        List[str]: Lista de orígenes permitidos
    """
    origins_str = os.getenv('CORS_ORIGINS', 'http://localhost:3000')
    return [origin.strip() for origin in origins_str.split(',')]


def is_production() -> bool:
    """
    Verifica si estamos en producción
    
    Returns:
        bool: True si es producción
    """
    return os.getenv('ENVIRONMENT', 'development') == 'production'


def is_debug() -> bool:
    """
    Verifica si el modo debug está activo
    
    Returns:
        bool: True si debug está activo
    """
    return os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
