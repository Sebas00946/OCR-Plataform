-- ============================================
-- AGREGAR UNIDAD FUNCIONAL: CONTABILIDAD
-- Para Red Médica (Honorarios, Cuentas, Consultas)
-- Sucursal: Medilaser Nacional (ID: 1)
-- ============================================

-- 1. Insertar la nueva unidad funcional "Contabilidad"
INSERT INTO unidades_funcionales (sucursal_id, codigo, nombre) 
VALUES (
    1,                              -- Medilaser Nacional
    'CONT',                         -- Código de la unidad
    'Contabilidad - Nacional'       -- Nombre descriptivo
)
ON CONFLICT DO NOTHING
RETURNING id, nombre;

-- 2. Agregar keywords relacionadas a Red Médica y Contabilidad
-- Nota: Reemplaza el SELECT con el ID real si ya conoces el ID de Contabilidad

-- Keywords de Red Médica (peso alto: 10)
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match, activo) VALUES
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'red medica', 10, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'red médica', 10, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'redmedica', 10, 'contiene', TRUE),

-- Honorarios médicos (peso alto: 10)
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'honorarios medicos', 10, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'honorarios médicos', 10, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'honorarios', 9, 'contiene', TRUE),

-- Cuentas médicas (peso: 9)
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'cuentas medicas', 9, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'cuentas médicas', 9, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'cuenta medica', 9, 'contiene', TRUE),

-- Consultas médicas (peso: 8-9)
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'consulta medica', 9, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'consulta médica', 9, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'consultas', 8, 'contiene', TRUE),

-- Contabilidad general (peso: 10)
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'contabilidad', 10, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'contaduria', 9, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'contaduría', 9, 'contiene', TRUE),

-- Servicios médicos (peso: 8)
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'servicios medicos', 8, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'servicios médicos', 8, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'atencion medica', 8, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'atención médica', 8, 'contiene', TRUE),

-- Profesionales de la salud (peso: 7)
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'medico', 7, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'médico', 7, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'doctor', 7, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'especialista', 7, 'contiene', TRUE),

-- Procedimientos (peso: 7)
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'procedimiento', 7, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'cirugia', 7, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'cirugía', 7, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'intervencion', 7, 'contiene', TRUE),
((SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1), 'intervención', 7, 'contiene', TRUE)

ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- 3. Verificar la configuración
SELECT 
    uf.id,
    uf.codigo,
    uf.nombre AS unidad_funcional,
    s.nombre AS sucursal,
    COUNT(uk.id) AS total_keywords
FROM unidades_funcionales uf
LEFT JOIN sucursales s ON uf.sucursal_id = s.id
LEFT JOIN ocr_unidad_keywords uk ON uf.id = uk.unidad_funcional_id
WHERE uf.codigo = 'CONT'
GROUP BY uf.id, uf.codigo, uf.nombre, s.nombre;

-- 4. Mostrar las keywords agregadas (Top 15)
SELECT 
    uk.keyword,
    uk.peso,
    uk.tipo_match,
    uk.activo
FROM ocr_unidad_keywords uk
JOIN unidades_funcionales uf ON uk.unidad_funcional_id = uf.id
WHERE uf.codigo = 'CONT'
ORDER BY uk.peso DESC, uk.keyword
LIMIT 15;

-- ============================================
-- RESULTADO DE LA CONFIGURACIÓN
-- ============================================
-- 
-- ✅ Unidad Funcional Creada:
--    ID:        19
--    Código:    CONT
--    Nombre:    Contabilidad - Nacional
--    Sucursal:  Clinica Medilaser S.A.S - Nacional (ID: 1)
--    Keywords:  28
-- 
-- ✅ Keywords Configuradas (Top 15 por peso):
--    1. contabilidad (peso: 10)
--    2. honorarios medicos / honorarios médicos (peso: 10)
--    3. red medica / red médica / redmedica (peso: 10)
--    4. consulta medica / consulta médica (peso: 9)
--    5. contaduria / contaduría (peso: 9)
--    6. cuenta medica / cuentas medicas / cuentas médicas (peso: 9)
--    7. honorarios (peso: 9)
--    8. atencion medica / atención médica (peso: 8)
--    9. consultas (peso: 8)
--    10. servicios medicos / servicios médicos (peso: 8)
--    ... y 18 keywords más
-- 
-- ============================================
-- USO Y CLASIFICACIÓN AUTOMÁTICA
-- ============================================
-- 
-- El sistema OCR ahora clasificará automáticamente las facturas que contengan
-- estas keywords a la unidad de Contabilidad - Nacional.
-- 
-- Ejemplos de facturas que se clasificarán aquí:
--   • Facturas con "Red Médica" en el texto
--   • Facturas con "Honorarios médicos"
--   • Facturas con "Cuentas médicas"
--   • Facturas con "Consultas médicas"
--   • Facturas con "Servicios médicos"
-- 
-- ============================================
-- AGREGAR MÁS KEYWORDS EN EL FUTURO
-- ============================================
-- 
-- Para agregar nuevas keywords:
-- 
-- INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match, activo)
-- VALUES (
--     (SELECT id FROM unidades_funcionales WHERE codigo = 'CONT' LIMIT 1),
--     'nueva_keyword',
--     8,              -- Peso (1-10, mayor = más importante)
--     'contiene',     -- Tipo: 'exacto', 'contiene', 'regex'
--     TRUE            -- Activo
-- )
-- ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;
-- 
-- ============================================
