from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from src.config import settings
from src.domain.entities import JobStatus, FileType, ProcessingQuality

Base = declarative_base()


class OCRJobModel(Base):
    """
    Modelo para trabajos de OCR en la base de datos veritask_manager.
    Esta tabla se creará en el schema public junto con las demás tablas existentes.
    """
    __tablename__ = "ocr_jobs"
    __table_args__ = {'schema': 'public'}  # Usar el schema public de veritask_manager
    
    id = Column(String, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    file_type = Column(SQLEnum(FileType, name='file_type_enum', schema='public'), nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(SQLEnum(JobStatus, name='job_status_enum', schema='public'), nullable=False, default=JobStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    language = Column(String, default="spa+eng")
    quality = Column(SQLEnum(ProcessingQuality, name='processing_quality_enum', schema='public'), default=ProcessingQuality.BALANCED)
    result_text = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    processing_time = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON stored as text


# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
