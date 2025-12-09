-- ============================================
-- SCHEMA DE CONFIGURACIÓN OCR (PostgreSQL)
-- Sistema parametrizable de clasificación
-- ============================================

-- Tabla de configuración de palabras clave por sucursal
CREATE TABLE IF NOT EXISTS ocr_sucursal_keywords (
    id SERIAL PRIMARY KEY,
    sucursal_id INTEGER NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    peso INTEGER DEFAULT 1, -- Peso/prioridad de la palabra clave (1-10)
    activo BOOLEAN DEFAULT TRUE,
    case_sensitive BOOLEAN DEFAULT FALSE,
    tipo_match VARCHAR(20) DEFAULT 'contiene' CHECK (tipo_match IN ('exacto', 'contiene', 'regex')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (sucursal_id, keyword)
);

CREATE INDEX IF NOT EXISTS idx_sucursal_keywords_sucursal ON ocr_sucursal_keywords(sucursal_id);
CREATE INDEX IF NOT EXISTS idx_sucursal_keywords_keyword ON ocr_sucursal_keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_sucursal_keywords_activo ON ocr_sucursal_keywords(activo);

-- Tabla de configuración de palabras clave por unidad funcional
CREATE TABLE IF NOT EXISTS ocr_unidad_keywords (
    id SERIAL PRIMARY KEY,
    unidad_funcional_id INTEGER NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    peso INTEGER DEFAULT 1, -- Peso/prioridad de la palabra clave (1-10)
    activo BOOLEAN DEFAULT TRUE,
    case_sensitive BOOLEAN DEFAULT FALSE,
    tipo_match VARCHAR(20) DEFAULT 'contiene' CHECK (tipo_match IN ('exacto', 'contiene', 'regex')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (unidad_funcional_id, keyword)
);

CREATE INDEX IF NOT EXISTS idx_unidad_keywords_unidad ON ocr_unidad_keywords(unidad_funcional_id);
CREATE INDEX IF NOT EXISTS idx_unidad_keywords_keyword ON ocr_unidad_keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_unidad_keywords_activo ON ocr_unidad_keywords(activo);

-- Tabla de configuración de proveedores
CREATE TABLE IF NOT EXISTS ocr_proveedor_config (
    id SERIAL PRIMARY KEY,
    proveedor_id INTEGER NOT NULL,
    nit VARCHAR(20) NOT NULL,
    nombre_completo VARCHAR(255) NOT NULL,
    alias JSONB, -- Array de nombres alternativos del proveedor
    formato_preferido VARCHAR(20) DEFAULT 'ambos' CHECK (formato_preferido IN ('xml', 'pdf', 'ambos')),
    requiere_validacion BOOLEAN DEFAULT FALSE,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (proveedor_id)
);

CREATE INDEX IF NOT EXISTS idx_proveedor_config_nit ON ocr_proveedor_config(nit);
CREATE INDEX IF NOT EXISTS idx_proveedor_config_activo ON ocr_proveedor_config(activo);

-- Tabla de configuración de campos a extraer
CREATE TABLE IF NOT EXISTS ocr_campos_extraccion (
    id SERIAL PRIMARY KEY,
    nombre_campo VARCHAR(100) NOT NULL,
    xpath_xml VARCHAR(500), -- XPath para extraer del XML
    regex_pdf VARCHAR(500), -- Regex para extraer del PDF
    tipo_dato VARCHAR(20) DEFAULT 'texto' CHECK (tipo_dato IN ('texto', 'numero', 'fecha', 'decimal', 'boolean')),
    requerido BOOLEAN DEFAULT FALSE,
    valor_default VARCHAR(255),
    validacion_regex VARCHAR(500),
    activo BOOLEAN DEFAULT TRUE,
    orden INTEGER DEFAULT 0,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (nombre_campo)
);

CREATE INDEX IF NOT EXISTS idx_campos_extraccion_activo ON ocr_campos_extraccion(activo);
CREATE INDEX IF NOT EXISTS idx_campos_extraccion_orden ON ocr_campos_extraccion(orden);

-- Tabla de reglas de clasificación
CREATE TABLE IF NOT EXISTS ocr_reglas_clasificacion (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    tipo_regla VARCHAR(30) NOT NULL CHECK (tipo_regla IN ('sucursal', 'unidad_funcional', 'proveedor')),
    condicion JSONB, -- Condiciones de la regla en formato JSON
    accion JSONB, -- Acción a ejecutar cuando se cumple la regla
    prioridad INTEGER DEFAULT 0, -- Mayor número = mayor prioridad
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reglas_clasificacion_tipo ON ocr_reglas_clasificacion(tipo_regla);
CREATE INDEX IF NOT EXISTS idx_reglas_clasificacion_prioridad ON ocr_reglas_clasificacion(prioridad);
CREATE INDEX IF NOT EXISTS idx_reglas_clasificacion_activo ON ocr_reglas_clasificacion(activo);

-- Tabla de historial de clasificaciones
CREATE TABLE IF NOT EXISTS ocr_clasificacion_historial (
    id SERIAL PRIMARY KEY,
    factura_id INTEGER,
    archivo_nombre VARCHAR(255) NOT NULL,
    archivo_tipo VARCHAR(10) NOT NULL CHECK (archivo_tipo IN ('xml', 'pdf')),
    sucursal_detectada_id INTEGER,
    unidad_funcional_detectada_id INTEGER,
    proveedor_detectado_id INTEGER,
    confianza_sucursal DECIMAL(5,2), -- Porcentaje de confianza (0-100)
    confianza_unidad DECIMAL(5,2),
    confianza_proveedor DECIMAL(5,2),
    keywords_encontradas JSONB, -- Keywords que coincidieron
    datos_extraidos JSONB, -- Todos los datos extraídos del documento
    tiempo_procesamiento_ms INTEGER,
    errores JSONB, -- Errores encontrados durante el procesamiento
    usuario_validacion_id INTEGER, -- Usuario que validó/corrigió la clasificación
    clasificacion_correcta BOOLEAN, -- Si la clasificación automática fue correcta
    observaciones TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clasificacion_historial_factura ON ocr_clasificacion_historial(factura_id);
CREATE INDEX IF NOT EXISTS idx_clasificacion_historial_sucursal ON ocr_clasificacion_historial(sucursal_detectada_id);
CREATE INDEX IF NOT EXISTS idx_clasificacion_historial_unidad ON ocr_clasificacion_historial(unidad_funcional_detectada_id);
CREATE INDEX IF NOT EXISTS idx_clasificacion_historial_proveedor ON ocr_clasificacion_historial(proveedor_detectado_id);
CREATE INDEX IF NOT EXISTS idx_clasificacion_historial_fecha ON ocr_clasificacion_historial(created_at);

-- Tabla de configuración general del OCR
CREATE TABLE IF NOT EXISTS ocr_configuracion (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT NOT NULL,
    tipo_dato VARCHAR(20) DEFAULT 'string' CHECK (tipo_dato IN ('string', 'number', 'boolean', 'json')),
    descripcion TEXT,
    categoria VARCHAR(50) DEFAULT 'general',
    editable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_configuracion_categoria ON ocr_configuracion(categoria);
CREATE INDEX IF NOT EXISTS idx_configuracion_clave ON ocr_configuracion(clave);

-- Tabla de sinónimos para mejorar la detección
CREATE TABLE IF NOT EXISTS ocr_sinonimos (
    id SERIAL PRIMARY KEY,
    palabra_original VARCHAR(100) NOT NULL,
    sinonimo VARCHAR(100) NOT NULL,
    tipo VARCHAR(30) DEFAULT 'general' CHECK (tipo IN ('sucursal', 'unidad_funcional', 'general')),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sinonimos_original ON ocr_sinonimos(palabra_original);
CREATE INDEX IF NOT EXISTS idx_sinonimos_sinonimo ON ocr_sinonimos(sinonimo);
CREATE INDEX IF NOT EXISTS idx_sinonimos_tipo ON ocr_sinonimos(tipo);
CREATE INDEX IF NOT EXISTS idx_sinonimos_activo ON ocr_sinonimos(activo);

-- Tabla de patrones de orden de compra
CREATE TABLE IF NOT EXISTS ocr_patrones_oc (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    patron_regex VARCHAR(500) NOT NULL,
    descripcion TEXT,
    prioridad INTEGER DEFAULT 0,
    activo BOOLEAN DEFAULT TRUE,
    ejemplos JSONB, -- Ejemplos de OC que coinciden con este patrón
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_patrones_oc_prioridad ON ocr_patrones_oc(prioridad);
CREATE INDEX IF NOT EXISTS idx_patrones_oc_activo ON ocr_patrones_oc(activo);

-- ============================================
-- FUNCIÓN PARA ACTUALIZAR updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para actualizar updated_at automáticamente
CREATE TRIGGER update_ocr_sucursal_keywords_updated_at BEFORE UPDATE ON ocr_sucursal_keywords FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ocr_unidad_keywords_updated_at BEFORE UPDATE ON ocr_unidad_keywords FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ocr_proveedor_config_updated_at BEFORE UPDATE ON ocr_proveedor_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ocr_campos_extraccion_updated_at BEFORE UPDATE ON ocr_campos_extraccion FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ocr_reglas_clasificacion_updated_at BEFORE UPDATE ON ocr_reglas_clasificacion FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ocr_configuracion_updated_at BEFORE UPDATE ON ocr_configuracion FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ocr_sinonimos_updated_at BEFORE UPDATE ON ocr_sinonimos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ocr_patrones_oc_updated_at BEFORE UPDATE ON ocr_patrones_oc FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- DATOS INICIALES DE CONFIGURACIÓN
-- ============================================

-- Configuración general
INSERT INTO ocr_configuracion (clave, valor, tipo_dato, descripcion, categoria) VALUES
('min_confianza_sucursal', '70', 'number', 'Confianza mínima para aceptar clasificación de sucursal (%)', 'clasificacion'),
('min_confianza_unidad', '60', 'number', 'Confianza mínima para aceptar clasificación de unidad funcional (%)', 'clasificacion'),
('max_file_size_mb', '10', 'number', 'Tamaño máximo de archivo en MB', 'archivos'),
('formatos_permitidos', '["xml", "pdf"]', 'json', 'Formatos de archivo permitidos', 'archivos'),
('timeout_procesamiento_ms', '30000', 'number', 'Timeout para procesamiento en milisegundos', 'performance'),
('usar_cache', 'true', 'boolean', 'Usar caché para resultados de clasificación', 'performance'),
('cache_ttl_seconds', '3600', 'number', 'Tiempo de vida del caché en segundos', 'performance'),
('notificar_baja_confianza', 'true', 'boolean', 'Notificar cuando la confianza es baja', 'notificaciones'),
('email_notificaciones', 'admin@veritask.com', 'string', 'Email para notificaciones del sistema', 'notificaciones'),
('modo_debug', 'false', 'boolean', 'Activar modo debug con logs detallados', 'desarrollo')
ON CONFLICT (clave) DO NOTHING;

-- Patrones comunes de orden de compra
INSERT INTO ocr_patrones_oc (nombre, patron_regex, descripcion, prioridad, ejemplos) VALUES
('OC Numérica Simple', 'OC[\s\.:-]*([0-9]{4,10})', 'Orden de compra con formato OC seguido de números', 10, '["OC.12345", "OC-109553", "OC 54321"]'),
('OC con Guiones', 'OC[\s]*-[\s]*([0-9]{4,10})', 'OC con guión separador', 9, '["OC-12345", "OC - 54321"]'),
('Número entre Guiones', '(?:^|\s)([0-9]{4,10})(?:-|\s)', 'Número de 4-10 dígitos seguido de guión', 8, '["12345-PROVEEDOR", "109553-INNOMED"]'),
('OC Alfanumérica', 'OC[\s\.:-]*([A-Z0-9]{6,15})', 'OC con letras y números', 7, '["OC.ABC12345", "OC-XYZ789"]')
ON CONFLICT DO NOTHING;

-- Sinónimos comunes
INSERT INTO ocr_sinonimos (palabra_original, sinonimo, tipo) VALUES
-- Sinónimos de ciudades
('bogota', 'bogotá', 'sucursal'),
('bogota', 'santafe de bogota', 'sucursal'),
('bogota', 'bogota d.c.', 'sucursal'),
('medellin', 'medellín', 'sucursal'),
('cali', 'santiago de cali', 'sucursal'),
-- Sinónimos de áreas
('almacen', 'bodega', 'unidad_funcional'),
('almacen', 'deposito', 'unidad_funcional'),
('compras', 'adquisiciones', 'unidad_funcional'),
('contabilidad', 'contaduria', 'unidad_funcional'),
('facturacion', 'facturación', 'unidad_funcional')
ON CONFLICT DO NOTHING;

-- Campos de extracción estándar
INSERT INTO ocr_campos_extraccion (nombre_campo, xpath_xml, regex_pdf, tipo_dato, requerido, orden, descripcion) VALUES
('numero_factura', '//cbc:ID', 'FACTURA.*?N[°º\s]+([A-Z0-9]+)', 'texto', TRUE, 1, 'Número de la factura'),
('fecha_emision', '//cbc:IssueDate', 'Fecha[:\s]+(\d{2}/\d{2}/\d{4})', 'fecha', TRUE, 2, 'Fecha de emisión'),
('nit_proveedor', '//cac:AccountingSupplierParty//cbc:CompanyID', 'Nit[:\s]+(\d+)', 'texto', TRUE, 3, 'NIT del proveedor'),
('nombre_proveedor', '//cac:AccountingSupplierParty//cbc:RegistrationName', NULL, 'texto', TRUE, 4, 'Nombre del proveedor'),
('nit_cliente', '//cac:AccountingCustomerParty//cbc:CompanyID', NULL, 'texto', TRUE, 5, 'NIT del cliente'),
('nombre_cliente', '//cac:AccountingCustomerParty//cbc:RegistrationName', 'Tercero[:\s]+(.+?)(?:\n|Sucursal)', 'texto', TRUE, 6, 'Nombre del cliente'),
('direccion_cliente', '//cac:AccountingCustomerParty//cac:Address//cbc:Line', 'Dirección[:\s]+(.+?)(?:\n|Teléfono)', 'texto', FALSE, 7, 'Dirección del cliente'),
('ciudad_cliente', '//cac:AccountingCustomerParty//cac:Address//cbc:CityName', NULL, 'texto', FALSE, 8, 'Ciudad del cliente'),
('subtotal', '//cac:LegalMonetaryTotal//cbc:LineExtensionAmount', 'VALOR BRUTO[:\s]+\$?\s*([\d,\.]+)', 'decimal', TRUE, 9, 'Subtotal de la factura'),
('total', '//cac:LegalMonetaryTotal//cbc:PayableAmount', 'VALOR NETO.*?[:\s]+\$?\s*([\d,\.]+)', 'decimal', TRUE, 10, 'Total de la factura'),
('observaciones', '//cbc:Note', NULL, 'texto', FALSE, 11, 'Observaciones de la factura'),
('cufe', '//cbc:UUID', 'CUFE[:\s]+([a-f0-9]+)', 'texto', FALSE, 12, 'CUFE de la factura')
ON CONFLICT (nombre_campo) DO NOTHING;
