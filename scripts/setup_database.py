"""
Script para configurar las tablas OCR en la base de datos veritask_manager existente
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, inspect, text
from src.infrastructure.database import Base, OCRJobModel
from src.config import settings
import structlog

logger = structlog.get_logger()


def check_database_connection():
    """Verificar conexión a la base de datos"""
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info("database_connected", version=version)
            return True
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        return False


def check_existing_tables():
    """Verificar tablas existentes en veritask_manager"""
    try:
        engine = create_engine(settings.database_url)
        inspector = inspect(engine)
        
        # Obtener todas las tablas del schema public
        tables = inspector.get_table_names(schema='public')
        
        logger.info("existing_tables", count=len(tables), tables=tables[:10])
        
        # Verificar si la tabla ocr_jobs ya existe
        if 'ocr_jobs' in tables:
            logger.info("ocr_jobs_table_exists")
            return True
        else:
            logger.info("ocr_jobs_table_not_found")
            return False
            
    except Exception as e:
        logger.error("table_check_failed", error=str(e))
        return False


def create_enums():
    """Crear tipos ENUM necesarios"""
    try:
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            # Crear ENUMs si no existen
            enums = [
                ("file_type_enum", "('image', 'pdf')"),
                ("job_status_enum", "('pending', 'processing', 'completed', 'failed')"),
                ("processing_quality_enum", "('fast', 'balanced', 'accurate')")
            ]
            
            for enum_name, enum_values in enums:
                try:
                    conn.execute(text(f"""
                        DO $$ BEGIN
                            CREATE TYPE public.{enum_name} AS ENUM {enum_values};
                        EXCEPTION
                            WHEN duplicate_object THEN null;
                        END $$;
                    """))
                    conn.commit()
                    logger.info("enum_created", name=enum_name)
                except Exception as e:
                    logger.warning("enum_creation_skipped", name=enum_name, reason=str(e))
        
        return True
        
    except Exception as e:
        logger.error("enum_creation_failed", error=str(e))
        return False


def create_ocr_tables():
    """Crear tablas OCR en veritask_manager"""
    try:
        logger.info("creating_ocr_tables")
        
        # Primero crear los ENUMs
        if not create_enums():
            logger.error("enum_creation_failed")
            return False
        
        # Crear las tablas
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(bind=engine, checkfirst=True)
        
        logger.info("ocr_tables_created_successfully")
        return True
        
    except Exception as e:
        logger.error("table_creation_failed", error=str(e))
        return False


def create_indexes():
    """Crear índices para mejorar el rendimiento"""
    try:
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_ocr_jobs_status ON public.ocr_jobs(status)",
                "CREATE INDEX IF NOT EXISTS idx_ocr_jobs_created_at ON public.ocr_jobs(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_ocr_jobs_file_type ON public.ocr_jobs(file_type)"
            ]
            
            for index_sql in indexes:
                conn.execute(text(index_sql))
                conn.commit()
            
            logger.info("indexes_created")
            return True
            
    except Exception as e:
        logger.error("index_creation_failed", error=str(e))
        return False


def main():
    """Ejecutar configuración de base de datos"""
    logger.info("starting_database_setup", database="veritask_manager")
    
    # 1. Verificar conexión
    if not check_database_connection():
        logger.error("cannot_connect_to_database")
        sys.exit(1)
    
    # 2. Verificar tablas existentes
    logger.info("checking_existing_tables")
    check_existing_tables()
    
    # 3. Crear tablas OCR
    if not create_ocr_tables():
        logger.error("failed_to_create_tables")
        sys.exit(1)
    
    # 4. Crear índices
    if not create_indexes():
        logger.warning("failed_to_create_indexes")
    
    logger.info("database_setup_completed")
    print("\n✅ Base de datos configurada exitosamente!")
    print("📊 Tablas OCR creadas en veritask_manager")
    print("🚀 Puedes iniciar la aplicación con: uvicorn src.main:app --reload")


if __name__ == "__main__":
    main()
