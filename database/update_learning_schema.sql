-- ============================================
-- ACTUALIZACIÓN DE SCHEMA PARA AUTO-APRENDIZAJE
-- ============================================

-- Agregar campos faltantes a ocr_clasificacion_historial
ALTER TABLE ocr_clasificacion_historial 
ADD COLUMN IF NOT EXISTS sucursal_correcta_id INTEGER,
ADD COLUMN IF NOT EXISTS unidad_correcta_id INTEGER,
ADD COLUMN IF NOT EXISTS fecha_validacion TIMESTAMP;

-- Crear índices para mejorar performance
CREATE INDEX IF NOT EXISTS idx_historial_sucursal_correcta 
ON ocr_clasificacion_historial(sucursal_correcta_id);

CREATE INDEX IF NOT EXISTS idx_historial_unidad_correcta 
ON ocr_clasificacion_historial(unidad_correcta_id);

CREATE INDEX IF NOT EXISTS idx_historial_fecha_validacion 
ON ocr_clasificacion_historial(fecha_validacion);

CREATE INDEX IF NOT EXISTS idx_historial_clasificacion_correcta 
ON ocr_clasificacion_historial(clasificacion_correcta);

-- Tabla de log de aprendizaje automático
CREATE TABLE IF NOT EXISTS ocr_learning_log (
    id SERIAL PRIMARY KEY,
    historial_id INTEGER REFERENCES ocr_clasificacion_historial(id),
    accion VARCHAR(50) NOT NULL, -- 'keyword_added', 'keyword_updated', 'weight_increased', 'weight_decreased'
    tipo VARCHAR(20) NOT NULL, -- 'sucursal', 'unidad'
    entity_id INTEGER NOT NULL,
    keyword VARCHAR(100),
    peso_anterior INTEGER,
    peso_nuevo INTEGER,
    razon TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_learning_log_historial 
ON ocr_learning_log(historial_id);

CREATE INDEX IF NOT EXISTS idx_learning_log_accion 
ON ocr_learning_log(accion);

CREATE INDEX IF NOT EXISTS idx_learning_log_fecha 
ON ocr_learning_log(created_at);

-- Vista para análisis de aprendizaje
CREATE OR REPLACE VIEW v_learning_stats AS
SELECT 
    DATE(created_at) as fecha,
    accion,
    tipo,
    COUNT(*) as total,
    AVG(peso_nuevo - COALESCE(peso_anterior, 0)) as cambio_promedio_peso
FROM ocr_learning_log
GROUP BY DATE(created_at), accion, tipo
ORDER BY fecha DESC;

-- Vista para keywords más efectivas
CREATE OR REPLACE VIEW v_keywords_efectivas AS
SELECT 
    'sucursal' as tipo,
    s.nombre as entidad,
    sk.keyword,
    sk.peso,
    COUNT(CASE WHEN h.clasificacion_correcta = TRUE THEN 1 END) as veces_correcta,
    COUNT(CASE WHEN h.clasificacion_correcta = FALSE THEN 1 END) as veces_incorrecta,
    ROUND(
        COUNT(CASE WHEN h.clasificacion_correcta = TRUE THEN 1 END) * 100.0 / 
        NULLIF(COUNT(*), 0), 
        2
    ) as efectividad
FROM ocr_sucursal_keywords sk
JOIN sucursales s ON s.id = sk.sucursal_id
LEFT JOIN ocr_clasificacion_historial h ON 
    h.sucursal_detectada_id = sk.sucursal_id 
    AND h.keywords_encontradas::jsonb->'sucursal' ? sk.keyword
WHERE sk.activo = TRUE
GROUP BY s.nombre, sk.keyword, sk.peso

UNION ALL

SELECT 
    'unidad' as tipo,
    uf.nombre as entidad,
    uk.keyword,
    uk.peso,
    COUNT(CASE WHEN h.clasificacion_correcta = TRUE THEN 1 END) as veces_correcta,
    COUNT(CASE WHEN h.clasificacion_correcta = FALSE THEN 1 END) as veces_incorrecta,
    ROUND(
        COUNT(CASE WHEN h.clasificacion_correcta = TRUE THEN 1 END) * 100.0 / 
        NULLIF(COUNT(*), 0), 
        2
    ) as efectividad
FROM ocr_unidad_keywords uk
JOIN unidades_funcionales uf ON uf.id = uk.unidad_funcional_id
LEFT JOIN ocr_clasificacion_historial h ON 
    h.unidad_funcional_detectada_id = uk.unidad_funcional_id 
    AND h.keywords_encontradas::jsonb->'unidad' ? uk.keyword
WHERE uk.activo = TRUE
GROUP BY uf.nombre, uk.keyword, uk.peso
ORDER BY efectividad DESC NULLS LAST;

-- Comentarios
COMMENT ON TABLE ocr_learning_log IS 'Log de todas las acciones de aprendizaje automático';
COMMENT ON COLUMN ocr_clasificacion_historial.sucursal_correcta_id IS 'ID de la sucursal correcta (si fue reclasificada)';
COMMENT ON COLUMN ocr_clasificacion_historial.unidad_correcta_id IS 'ID de la unidad correcta (si fue reclasificada)';
COMMENT ON COLUMN ocr_clasificacion_historial.fecha_validacion IS 'Fecha en que el usuario validó la clasificación';

COMMIT;