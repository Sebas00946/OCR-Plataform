"""
Script para inicializar la base de datos
"""
from src.infrastructure.database import init_db
import structlog

logger = structlog.get_logger()


def main():
    """Inicializar base de datos"""
    try:
        logger.info("Inicializando base de datos...")
        init_db()
        logger.info("Base de datos inicializada correctamente")
    except Exception as e:
        logger.error("Error al inicializar base de datos", error=str(e))
        raise


if __name__ == "__main__":
    main()
