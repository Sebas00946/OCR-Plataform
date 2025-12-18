-- ============================================
-- KEYWORDS MEJORADAS PARA TUNJA
-- Basadas en direcciones y ubicaciones específicas
-- ============================================

-- Keywords para Sucursal Tunja (ID: 5)
INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso, tipo_match) VALUES
-- Direcciones específicas
(5, 'CR 2 ESTE', 10, 'contiene'),
(5, 'CARRERA 2 ESTE', 10, 'contiene'),
(5, '67B 90', 9, 'contiene'),
(5, 'TUNJA/CR', 10, 'contiene'),
(5, 'CG CL MEDILASER TUNJA', 10, 'contiene'),

-- Variaciones del nombre
(5, 'MEDILASER TUNJA/CR', 10, 'contiene'),
(5, 'CL MEDILASER TUNJA', 10, 'contiene'),
(5, 'CLINICA MEDILASER TUNJA', 10, 'contiene')

ON CONFLICT (sucursal_id, keyword) DO UPDATE 
SET peso = EXCLUDED.peso;

-- Keywords para Administración - TJA (ID: 13)
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
-- Direcciones específicas
(13, 'CR 2 ESTE', 10, 'contiene'),
(13, 'CARRERA 2 ESTE', 10, 'contiene'),
(13, '67B 90', 9, 'contiene'),
(13, 'TUNJA/CR', 10, 'contiene'),
(13, 'CG CL MEDILASER TUNJA', 10, 'contiene'),

-- Servicios administrativos
(13, 'LECTURA', 10, 'contiene'),
(13, 'RADIOGRAFIA', 9, 'contiene'),
(13, 'TOMOGRAFIA', 9, 'contiene'),
(13, 'SEGUNDAS LECTURAS', 10, 'contiene'),
(13, 'SERVICIOS PRESTADOS', 9, 'contiene'),

-- Códigos y referencias
(13, 'MED-2025', 8, 'contiene'),
(13, 'AFE-', 7, 'contiene')

ON CONFLICT (unidad_funcional_id, keyword) DO UPDATE 
SET peso = EXCLUDED.peso;

-- ============================================
-- KEYWORDS PARA NEIVA (para evitar confusión)
-- ============================================

-- Reducir peso de keywords genéricas de Neiva
UPDATE ocr_sucursal_keywords 
SET peso = 5  -- Reducir de 10 a 5
WHERE sucursal_id = (SELECT id FROM sucursales WHERE nombre LIKE '%Neiva%' LIMIT 1)
AND keyword IN ('CLINICA MEDILASER', 'MEDILASER', 'CLINICA MEDILASER S.A.S');

-- Agregar keywords más específicas para Neiva
INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso, tipo_match)
SELECT 
    s.id,
    'NEIVA',
    10,
    'contiene'
FROM sucursales s
WHERE s.nombre LIKE '%Neiva%'
ON CONFLICT (sucursal_id, keyword) DO UPDATE 
SET peso = EXCLUDED.peso;

INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso, tipo_match)
SELECT 
    s.id,
    'HUILA',
    10,
    'contiene'
FROM sucursales s
WHERE s.nombre LIKE '%Neiva%'
ON CONFLICT (sucursal_id, keyword) DO UPDATE 
SET peso = EXCLUDED.peso;

INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso, tipo_match)
SELECT 
    s.id,
    'CR 7 11 65',
    10,
    'contiene'
FROM sucursales s
WHERE s.nombre LIKE '%Neiva%'
ON CONFLICT (sucursal_id, keyword) DO UPDATE 
SET peso = EXCLUDED.peso;

-- ============================================
-- KEYWORDS PARA FLORENCIA
-- ============================================

INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso, tipo_match)
SELECT 
    s.id,
    'FLORENCIA',
    10,
    'contiene'
FROM sucursales s
WHERE s.nombre LIKE '%Florencia%'
ON CONFLICT (sucursal_id, keyword) DO UPDATE 
SET peso = EXCLUDED.peso;

INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso, tipo_match)
SELECT 
    s.id,
    'SEDE FLORENCIA',
    10,
    'contiene'
FROM sucursales s
WHERE s.nombre LIKE '%Florencia%'
ON CONFLICT (sucursal_id, keyword) DO UPDATE 
SET peso = EXCLUDED.peso;

-- ============================================
-- KEYWORDS PARA FACATATIVA
-- ============================================

INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso, tipo_match)
SELECT 
    s.id,
    'FACATATIVA',
    10,
    'contiene'
FROM sucursales s
WHERE s.nombre LIKE '%Facatativa%'
ON CONFLICT (sucursal_id, keyword) DO UPDATE 
SET peso = EXCLUDED.peso;

INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso, tipo_match)
SELECT 
    s.id,
    'FACA',
    10,
    'contiene'
FROM sucursales s
WHERE s.nombre LIKE '%Facatativa%'
ON CONFLICT (sucursal_id, keyword) DO UPDATE 
SET peso = EXCLUDED.peso;

COMMIT;
