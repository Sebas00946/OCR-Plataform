"""
Utilidades para validación de datos
"""
import re


def is_valid_keyword(keyword: str, keywords_ignorar: set) -> bool:
    """
    Verifica si una keyword es válida (no es genérica o numérica)
    
    Args:
        keyword: Keyword a validar
        keywords_ignorar: Set de keywords a ignorar
    
    Returns:
        True si es válida, False si no
    """
    keyword_upper = keyword.upper().strip()
    
    # Ignorar keywords en la lista negra
    if keyword_upper in keywords_ignorar:
        return False
    
    # Ignorar keywords que son solo números
    if keyword_upper.isdigit():
        return False
    
    # Ignorar keywords muy cortas (menos de 3 caracteres)
    if len(keyword_upper) < 3:
        return False
    
    # Ignorar keywords que son principalmente números (más del 70% dígitos)
    digits = sum(c.isdigit() for c in keyword_upper)
    if len(keyword_upper) > 0 and digits / len(keyword_upper) > 0.7:
        return False
    
    return True


def is_valid_numero_factura(numero: str, text: str) -> bool:
    """
    Valida que un número de factura sea válido
    
    Args:
        numero: Número de factura candidato
        text: Texto completo del PDF para contexto
    
    Returns:
        True si parece válido, False si no
    """
    if not numero or len(numero) < 3:
        return False
    
    # Debe tener al menos un dígito
    if not any(c.isdigit() for c in numero):
        return False
    
    # Si tiene letras, debe tener al menos 2 letras al inicio (prefijo)
    if any(c.isalpha() for c in numero):
        letras_inicio = 0
        for c in numero:
            if c.isalpha():
                letras_inicio += 1
            else:
                break
        
        if letras_inicio < 2:
            return False
        
        # El prefijo no debe ser una palabra común
        prefijo = numero[:letras_inicio]
        palabras_invalidas_prefijo = [
            'FACTURA', 'TOTAL', 'SUBTOTAL', 'IVA', 'VALOR', 'FECHA',
            'VENCIMIENTO', 'PAGO', 'CREDITO', 'CONTADO', 'CLIENTE',
            'PROVEEDOR', 'NIT', 'TELEFONO', 'EMAIL', 'DIRECCION',
            'CIUDAD', 'DEPARTAMENTO', 'CODIGO', 'PRODUCTO', 'CANTIDAD',
            'PRECIO', 'DESCUENTO', 'IMPUESTO', 'RETENCION', 'NETO',
            'BRUTO', 'BASE', 'TARIFA'
        ]
        
        if prefijo in palabras_invalidas_prefijo:
            return False
    
    # Debe tener al menos 3 dígitos
    digitos = sum(1 for c in numero if c.isdigit())
    if digitos < 3:
        return False
    
    # Si el número aparece cerca de palabras clave de factura, es más probable que sea válido
    try:
        pos = text.upper().find(numero.upper())
        if pos != -1:
            contexto = text[max(0, pos-150):min(len(text), pos+len(numero)+150)].upper()
            
            palabras_clave_factura = [
                'FACTURA', 'ELECTRÓNICA', 'ELECTRONICA', 'VENTA', 
                'N°', 'NO.', 'NRO', 'NÚMERO', 'NUMERO',
                'INVOICE', 'BILL'
            ]
            
            palabras_clave_negativas = [
                'PEDIDO', 'ORDEN', 'REMISION', 'GUIA', 'COTIZACION',
                'PRESUPUESTO', 'PROFORMA', 'RECIBO', 'COMPROBANTE'
            ]
            
            tiene_contexto_factura = any(palabra in contexto for palabra in palabras_clave_factura)
            tiene_contexto_negativo = any(palabra in contexto for palabra in palabras_clave_negativas)
            
            if tiene_contexto_factura and not tiene_contexto_negativo:
                return True
            
            if tiene_contexto_negativo:
                return False
    except:
        pass
    
    # Si tiene un formato típico de factura (2-5 letras + 4+ dígitos), aceptar
    if re.match(r'^[A-Z]{2,5}\d{4,}$', numero.upper()):
        return True
    
    # Si solo tiene dígitos y está en contexto de factura, aceptar
    if numero.isdigit() and len(numero) >= 5:
        return True
    
    return False


def is_valid_orden_compra(orden: str) -> bool:
    """
    Valida que una orden de compra tenga un formato razonable
    
    Args:
        orden: Número de orden de compra candidato
    
    Returns:
        True si parece válida, False si no
    """
    if not orden or len(orden) < 3:
        return False
    
    has_letter = any(c.isalpha() for c in orden)
    has_digit = any(c.isdigit() for c in orden)
    
    if not (has_letter and has_digit):
        return False
    
    if orden.replace('-', '').replace('/', '').isdigit():
        return False
    
    if len(orden) > 50:
        return False
    
    palabras_invalidas = ['FACTURA', 'TOTAL', 'SUBTOTAL', 'IVA', 'FECHA', 'VENCIMIENTO']
    if any(palabra in orden.upper() for palabra in palabras_invalidas):
        return False
    
    return True
