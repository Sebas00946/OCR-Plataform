-- Script SQL para crear las tablas necesarias para el módulo OCR
-- en la base de datos veritask_manager existente
-- Ejecutar este script en la base de datos veritask_manager

-- Conectar a la base de datos veritask_manager
\c veritask_manager;

-- Crear tipos ENUM si no existen
DO $$ BEGIN
    CREATE TYPE public.file_type_enum AS ENUM ('image', 'pdf');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE public.job_status_enum AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE public.processing_quality_enum AS ENUM ('fast', 'balanced', 'accurate');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Crear tabla ocr_jobs en el schema public
CREATE TABLE IF NOT EXISTS public.ocr_jobs (
    id VARCHAR PRIMARY KEY,
    file_name VARCHAR NOT NULL,
    file_type public.file_type_enum NOT NULL,
    file_size INTEGER NOT NULL,
    status public.job_status_enum NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    language VARCHAR DEFAULT 'spa+eng',
    quality public.processing_quality_enum DEFAULT 'balanced',
    result_text TEXT,
    confidence FLOAT,
    processing_time FLOAT,
    error_message TEXT,
    metadata TEXT
);

-- Crear índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_ocr_jobs_status ON public.ocr_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ocr_jobs_created_at ON public.ocr_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_ocr_jobs_file_type ON public.ocr_jobs(file_type);

-- Crear función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION public.update_ocr_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger para actualizar updated_at
DROP TRIGGER IF EXISTS trigger_update_ocr_jobs_updated_at ON public.ocr_jobs;
CREATE TRIGGER trigger_update_ocr_jobs_updated_at
    BEFORE UPDATE ON public.ocr_jobs
    FOR EACH ROW
    EXECUTE FUNCTION public.update_ocr_jobs_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE public.ocr_jobs IS 'Tabla para almacenar trabajos de OCR (Reconocimiento Óptico de Caracteres)';
COMMENT ON COLUMN public.ocr_jobs.id IS 'Identificador único del trabajo (UUID)';
COMMENT ON COLUMN public.ocr_jobs.file_name IS 'Nombre del archivo original';
COMMENT ON COLUMN public.ocr_jobs.file_type IS 'Tipo de archivo: image o pdf';
COMMENT ON COLUMN public.ocr_jobs.file_size IS 'Tamaño del archivo en bytes';
COMMENT ON COLUMN public.ocr_jobs.status IS 'Estado del trabajo: pending, processing, completed, failed';
COMMENT ON COLUMN public.ocr_jobs.language IS 'Idiomas para OCR (formato Tesseract, ej: spa+eng)';
COMMENT ON COLUMN public.ocr_jobs.quality IS 'Calidad de procesamiento: fast, balanced, accurate';
COMMENT ON COLUMN public.ocr_jobs.result_text IS 'Texto extraído del documento';
COMMENT ON COLUMN public.ocr_jobs.confidence IS 'Nivel de confianza del OCR (0-100)';
COMMENT ON COLUMN public.ocr_jobs.processing_time IS 'Tiempo de procesamiento en segundos';
COMMENT ON COLUMN public.ocr_jobs.error_message IS 'Mensaje de error si el trabajo falló';
COMMENT ON COLUMN public.ocr_jobs.metadata IS 'Metadatos adicionales en formato JSON';

-- Verificar que la tabla se creó correctamente
SELECT 
    table_schema,
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'ocr_jobs'
ORDER BY ordinal_position;

-- Mostrar mensaje de éxito
DO $$
BEGIN
    RAISE NOTICE 'Tablas OCR creadas exitosamente en veritask_manager';
END $$;