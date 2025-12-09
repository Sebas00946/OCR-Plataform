-- ============================================
-- DATOS DE EJEMPLO PARA OCR (PostgreSQL)
-- Basado en las sucursales y unidades funcionales existentes
-- ============================================

-- NOTA: Ajusta los IDs según tus sucursales y unidades funcionales reales
-- Ejecuta primero: SELECT id, nombre FROM sucursales;
-- Ejecuta primero: SELECT id, nombre FROM unidades_funcionales;

-- ============================================
-- KEYWORDS PARA SUCURSALES (EJEMPLOS)
-- ============================================

-- Estos son ejemplos genéricos. Ajusta los IDs según tu base de datos real
-- Puedes comentar estas líneas y ejecutar el script sync_from_nodejs.py

INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso, tipo_match) VALUES
(1, 'neiva', 10, 'contiene'),
(1, 'nva', 8, 'contiene'),
(1, 'huila', 7, 'contiene')
ON CONFLICT (sucursal_id, keyword) DO NOTHING;

-- ============================================
-- KEYWORDS PARA UNIDADES FUNCIONALES (EJEMPLOS)
-- ============================================

-- Almacén / Bodega
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(1, 'almacen', 10, 'contiene'),
(1, 'almacén', 10, 'contiene'),
(1, 'bodega', 9, 'contiene'),
(1, 'deposito', 8, 'contiene'),
(1, 'depósito', 8, 'contiene'),
(1, 'inventario', 7, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- Compras / Adquisiciones
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(2, 'compras', 10, 'contiene'),
(2, 'adquisiciones', 9, 'contiene'),
(2, 'procurement', 8, 'contiene'),
(2, 'suministros', 7, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- Farmacia
INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, tipo_match) VALUES
(5, 'farmacia', 10, 'contiene'),
(5, 'medicamentos', 9, 'contiene'),
(5, 'drogueria', 8, 'contiene'),
(5, 'droguería', 8, 'contiene'),
(5, 'farmaceutico', 7, 'contiene'),
(5, 'farmacéutico', 7, 'contiene')
ON CONFLICT (unidad_funcional_id, keyword) DO NOTHING;

-- ============================================
-- CONFIGURACIÓN DE PROVEEDORES COMUNES
-- ============================================

INSERT INTO ocr_proveedor_config (proveedor_id, nit, nombre_completo, alias, formato_preferido) VALUES
(1, '900433437', 'FARMAQUIRURGICOS JM SAS', '["FARMAQX", "FQX", "FARMAQUIRURGICOS"]', 'xml')
ON CONFLICT (proveedor_id) DO NOTHING;

-- ============================================
-- REGLAS DE CLASIFICACIÓN AUTOMÁTICA
-- ============================================

-- Regla: Facturas con palabras clave médicas van a Farmacia
INSERT INTO ocr_reglas_clasificacion (nombre, descripcion, tipo_regla, condicion, accion, prioridad) VALUES
('Medicamentos -> Farmacia',
 'Facturas que contienen palabras relacionadas con medicamentos',
 'unidad_funcional',
 '{"texto_contiene": ["medicamento", "farmaco", "fármaco", "droga", "ampolla", "tableta"]}',
 '{"asignar_unidad": "Farmacia", "confianza": 85}',
 8)
ON CONFLICT DO NOTHING;
