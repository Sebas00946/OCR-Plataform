"""
Utilidades para procesamiento de texto
"""
import re
from typing import Optional


def limpiar_nit(nit: str) -> str:
    """
    Limpia un NIT removiendo caracteres no numéricos
    
    Args:
        nit: NIT con formato variable
    
    Returns:
        NIT solo con números
    """
    if not nit:
        return ""
    return re.sub(r'[^0-9]', '', str(nit))


def clean_pdf_text(text: str) -> str:
    """
    Limpia el texto extraído del PDF manteniendo información útil
    
    Args:
        text: Texto crudo del PDF
    
    Returns:
        Texto limpio
    """
    if not text:
        return ""
    
    # Remover caracteres de control excepto saltos de línea y espacios
    text = ''.join(char for char in text if char.isprintable() or char in '\n\r\t ')
    
    # Normalizar espacios múltiples
    text = re.sub(r' +', ' ', text)
    
    # Normalizar saltos de línea múltiples
    text = re.sub(r'\n\n+', '\n\n', text)
    
    return text.strip()


def parse_money(s: str) -> Optional[float]:
    """
    Parsea un string de dinero a float
    Maneja formatos colombianos: $1.234.567,89 o $1,234,567.89
    
    Args:
        s: String con valor monetario
    
    Returns:
        Valor como float o None si no se puede parsear
    """
    if not s:
        return None
    
    s = s.replace('COP', '').replace('$', '').replace(' ', '')
    s = s.replace('\u00A0', '')
    
    if s.count(',') > 1 and '.' not in s:
        s = s.replace(',', '')
    elif s.count('.') > 1 and ',' not in s:
        s = s.replace('.', '')
    
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    else:
        if ',' in s and '.' not in s:
            s = s.replace('.', '').replace(',', '.')
        elif '.' in s and ',' not in s:
            s = s.replace(',', '')
    
    s = re.sub(r'[^\d\.]', '', s)
    
    try:
        return float(s) if s else None
    except Exception:
        return None


def extract_amount_near(text: str, labels: list) -> Optional[float]:
    """
    Extrae un monto cerca de una etiqueta específica
    
    Args:
        text: Texto donde buscar
        labels: Lista de patrones regex de etiquetas
    
    Returns:
        Monto encontrado o None
    """
    txt = text.upper()
    for label in labels:
        for m in re.finditer(label, txt):
            start = max(0, m.start() - 80)
            end = min(len(txt), m.end() + 80)
            ctx = txt[start:end]
            nums = re.findall(r'[$]?\s*[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?', ctx)
            if nums:
                for n in reversed(nums):
                    val = parse_money(n)
                    if val is not None:
                        return val
    return None
