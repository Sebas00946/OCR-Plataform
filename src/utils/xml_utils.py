"""
Utilidades para procesamiento de XML
"""
import xml.etree.ElementTree as ET
from typing import Optional, List


# Namespaces comunes en facturas electrónicas colombianas
NAMESPACES = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    'sts': 'dian:gov:co:facturaelectronica:Structures-2-1',
    'fe': 'http://www.dian.gov.co/contratos/facturaelectronica/v1'
}


def extract_text(root: ET.Element, xpaths: List[str]) -> str:
    """
    Extrae texto del primer xpath que encuentre
    
    Args:
        root: Elemento raíz del XML
        xpaths: Lista de xpaths a buscar
    
    Returns:
        Texto encontrado o string vacío
    """
    for xpath in xpaths:
        elem = root.find(xpath, NAMESPACES)
        if elem is not None and elem.text:
            return elem.text.strip()
    return ""


def extract_all_text(root: ET.Element, xpaths: List[str]) -> List[str]:
    """
    Extrae texto de todos los elementos que coincidan
    
    Args:
        root: Elemento raíz del XML
        xpaths: Lista de xpaths a buscar
    
    Returns:
        Lista de textos encontrados
    """
    texts = []
    for xpath in xpaths:
        elems = root.findall(xpath, NAMESPACES)
        for elem in elems:
            if elem.text:
                texts.append(elem.text.strip())
    return texts


def extract_embedded_invoice(root: ET.Element) -> Optional[ET.Element]:
    """
    Extrae el Invoice embebido en el CDATA del AttachedDocument
    
    Args:
        root: Root del XML AttachedDocument
    
    Returns:
        Root del Invoice embebido o None si no existe
    """
    try:
        description = root.find('.//cac:Attachment//cac:ExternalReference//cbc:Description', NAMESPACES)
        
        if description is not None and description.text:
            invoice_xml = description.text.strip()
            invoice_root = ET.fromstring(invoice_xml)
            return invoice_root
    except Exception:
        pass
    
    return None
