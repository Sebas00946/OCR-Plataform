"""
Configuración de base de datos PostgreSQL
"""
import os
from dotenv import load_dotenv

load_dotenv()


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
