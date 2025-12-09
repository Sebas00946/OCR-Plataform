-- ============================================
-- KEYWORDS POR UNIDAD FUNCIONAL
-- Basadas en análisis de PDFs reales
-- ============================================

-- Limpiar keywords anteriores
DELETE FROM ocr_unidad_keywords;

-- ============================================
-- ALMACÉN - FLA (Florencia) - ID: 8
-- ============================================
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(8, 'FLO MED', 10, 'contiene'),
(8, 'FLORENCIA', 9, 'contiene'),
(8, '0055', 8, 'contiene'),
(8, 'FACTURACION MAOS MEDILASER FLORENCIA', 9, 'contiene'),
(8, 'WMD-MED FLORENCIA', 8, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- ============================================
-- ALMACÉN - TJA (Tunja) - ID: 9
-- ============================================
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(9, 'TJA MED', 10, 'contiene'),
(9, 'CONSIG. MEDLASER TUNJA', 10, 'contiene'),
(9, 'MEDLASER TUNJA', 9, 'contiene'),
(9, '0012', 8, 'contiene'),
(9, 'T&T-ELEC', 7, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- ============================================
-- ALMACÉN - NVA (Neiva) - ID: 5
-- ============================================
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(5, 'NVA MED', 10, 'contiene'),
(5, 'FACTURACION MAOS MEDILASER NEIVA', 10, 'contiene'),
(5, 'MEDILASER NEIVA', 9, 'contiene'),
(5, '0053', 8, 'contiene'),
(5, 'IMM-INVENTARIO MENTOR NEIVA', 9, 'contiene'),
(5, '0110', 8, 'contiene'),
(5, 'ORTOMAC', 7, 'contiene'),
(5, 'MENTOR', 7, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- ============================================
-- ALMACÉN - KTA (Facatativa) - ID: 2
-- ============================================
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(2, 'FCA MFA', 10, 'contiene'),
(2, 'FACTURACION MAOS MEDILASER FACA', 10, 'contiene'),
(2, 'MEDILASER FACA', 9, 'contiene'),
(2, '0056', 8, 'contiene'),
(2, 'LOGYSMED', 7, 'contiene'),
(2, 'INNOMED', 8, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- ============================================
-- ACTIVO FIJOS - FLA (Florencia) - ID: 1
-- ============================================
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(1, 'ACTIVO FIJO', 10, 'contiene'),
(1, 'ACTIVOS FIJOS', 10, 'contiene'),
(1, 'EQUIPO', 8, 'contiene'),
(1, 'EQUIPOS', 8, 'contiene'),
(1, 'MAQUINARIA', 7, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- ============================================
-- CENTRAL DE COMPRAS - NVA (Neiva) - ID: 10
-- ============================================
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(10, 'CENTRAL DE COMPRAS', 10, 'contiene'),
(10, 'COMPRAS NVA', 9, 'contiene'),
(10, 'EAL', 8, 'contiene'),
(10, 'CMI', 8, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- ============================================
-- KEYWORDS COMUNES (HOSPITALIARIA)
-- ============================================
-- Estas aparecen en todas las facturas, así que tienen peso bajo
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(2, 'HOSPITALIARIA', 3, 'contiene'),
(5, 'HOSPITALIARIA', 3, 'contiene'),
(8, 'HOSPITALIARIA', 3, 'contiene'),
(9, 'HOSPITALIARIA', 3, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

COMMIT;
