-- ============================================
-- KEYWORDS PARA UNIDADES DE ADMINISTRACIÓN
-- ============================================

-- Administración - FLA (Florencia) - ID: 12
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(12, 'LECTURA RADIOGRAFIA', 10, 'contiene'),
(12, 'LECTURA TOMOGRAFIA', 10, 'contiene'),
(12, 'SEGUNDAS LECTURAS', 10, 'contiene'),
(12, 'RADIOLOGIA', 9, 'contiene'),
(12, 'SEDE FLORENCIA', 10, 'contiene'),
(12, 'INTELMED', 8, 'contiene'),
(12, 'SERVICIOS PRESTADOS', 7, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- Administración - NVA (Neiva) - ID: 11
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(11, 'LECTURA RADIOGRAFIA', 10, 'contiene'),
(11, 'LECTURA TOMOGRAFIA', 10, 'contiene'),
(11, 'SEGUNDAS LECTURAS', 10, 'contiene'),
(11, 'RADIOLOGIA', 9, 'contiene'),
(11, 'SEDE NEIVA', 10, 'contiene'),
(11, 'SERVICIOS PRESTADOS', 7, 'contiene'),
(11, 'ADMINISTRACION', 8, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- Administración - TJA (Tunja) - ID: 13
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(13, 'LECTURA RADIOGRAFIA', 10, 'contiene'),
(13, 'LECTURA TOMOGRAFIA', 10, 'contiene'),
(13, 'SEGUNDAS LECTURAS', 10, 'contiene'),
(13, 'RADIOLOGIA', 9, 'contiene'),
(13, 'SEDE TUNJA', 10, 'contiene'),
(13, 'SERVICIOS PRESTADOS', 7, 'contiene'),
(13, 'ADMINISTRACION', 8, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- Administración - KTA (Facatativa) - ID: 14
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(14, 'LECTURA RADIOGRAFIA', 10, 'contiene'),
(14, 'LECTURA TOMOGRAFIA', 10, 'contiene'),
(14, 'SEGUNDAS LECTURAS', 10, 'contiene'),
(14, 'RADIOLOGIA', 9, 'contiene'),
(14, 'SEDE FACATATIVA', 10, 'contiene'),
(14, 'SERVICIOS PRESTADOS', 7, 'contiene'),
(14, 'ADMINISTRACION', 8, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

COMMIT;
