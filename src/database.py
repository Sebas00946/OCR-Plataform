"""
Módulo de gestión de base de datos con Pool de Conexiones
"""
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
import logging
from typing import Generator
import os
from .config import get_db_config

logger = logging.getLogger(__name__)

class DatabasePool:
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabasePool, cls).__new__(cls)
        return cls._instance

    def initialize(self):
        """Inicializa el pool de conexiones"""
        if self._pool is None:
            try:
                db_config = get_db_config()
                # ThreadedConnectionPool es mejor para entornos multi-hilo como FastAPI
                self._pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=20,
                    **db_config
                )
                logger.info("Pool de conexiones a base de datos inicializado exitosamente")
            except Exception as e:
                logger.error(f"Error inicializando pool de base de datos: {e}")
                raise

    def close(self):
        """Cierra todas las conexiones del pool"""
        if self._pool:
            self._pool.closeall()
            self._pool = None
            logger.info("Pool de conexiones cerrado")

    @contextmanager
    def get_connection(self) -> Generator:
        """
        Context manager para obtener una conexión del pool.
        Maneja automáticamente el retorno de la conexión al pool.
        """
        if self._pool is None:
            self.initialize()
            
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except Exception as e:
            logger.error(f"Error obteniendo conexión de base de datos: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)

# Instancia global
db = DatabasePool()

def get_db_connection():
    """Helper para usar como dependencia o directamente"""
    return db.get_connection()
