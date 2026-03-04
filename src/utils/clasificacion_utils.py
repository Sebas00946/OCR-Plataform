"""
Utilidades para clasificación de facturas
Funciones auxiliares para mejorar performance y legibilidad
"""
import re
from typing import Dict, List, Optional, Tuple
from functools import lru_cache


class SucursalDetector:
    """Detector de sucursales con múltiples estrategias"""
    
    # Mapeo de ciudades a códigos de sucursal (códigos numéricos de la BD)
    CIUDAD_SUCURSAL_MAP = {
        'NEIVA': '00004',
        'TUNJA': '00005',
        'FLORENCIA': '00006',
        'PITALITO': '00006',  # Pitalito
        'BOGOTA': '00001',  # Nacional
        'BOGOTÁ': '00001',
        'FACATATIVA': '00002',
        'DUITAMA': '00009',
        'MOCOA': '00010',
        'ABNER LOZANO': '00007',
        'MYRIAM PARRA': '00008'
    }
    
    # Mapeo de códigos internos a códigos de BD
    CODIGO_INTERNO_A_BD = {
        'NVA': '00004',  # Neiva
        'TJA': '00005',  # Tunja
        'FLA': '00006',  # Florencia
        'PTO': '00006',  # Pitalito (mismo que Florencia?)
        'BOG': '00001',  # Bogotá/Nacional
        'FAC': '00002',  # Facatativa
        'DUI': '00009',  # Duitama
        'KTA': '00001',  # Cartagena -> Nacional?
        'MOC': '00010',  # Mocoa
    }
    
    # Códigos internos válidos (para detección en texto)
    CODIGOS_INTERNOS = {'NVA', 'TJA', 'FLA', 'PTO', 'BOG', 'FAC', 'DUI', 'KTA', 'MOC'}
    
    # Códigos de BD válidos
    CODIGOS_BD = {'00001', '00002', '00003', '00004', '00005', '00006', '00007', '00008', '00009', '00010'}
    
    @staticmethod
    def extraer_de_ciudad(ciudad: str) -> Optional[str]:
        """Extrae código de sucursal desde nombre de ciudad"""
        if not ciudad:
            return None
        
        ciudad_upper = ciudad.upper().strip()
        return SucursalDetector.CIUDAD_SUCURSAL_MAP.get(ciudad_upper)
    
    @staticmethod
    def extraer_de_texto(texto: str) -> Optional[str]:
        """
        Extrae código de sucursal desde texto usando patrones
        
        Busca patrones como:
        - TJA, FLA, NVA, etc. (códigos internos)
        - CMC6434-TJA (código después de guión)
        - SUCURSAL TJA
        
        Returns:
            Código de BD (ej: '00005' para TJA)
        """
        if not texto:
            return None
        
        texto_upper = texto.upper()
        
        # Patrón 1: Código después de guión (ej: CMC6434-TJA)
        patron_guion = r'-([A-Z]{3})\b'
        matches = re.findall(patron_guion, texto_upper)
        for match in matches:
            if match in SucursalDetector.CODIGOS_INTERNOS:
                return SucursalDetector.CODIGO_INTERNO_A_BD.get(match)
        
        # Patrón 2: Código standalone (ej: TJA, FLA)
        patron_standalone = r'\b([A-Z]{3})\b'
        matches = re.findall(patron_standalone, texto_upper)
        for match in matches:
            if match in SucursalDetector.CODIGOS_INTERNOS:
                return SucursalDetector.CODIGO_INTERNO_A_BD.get(match)
        
        # Patrón 3: Buscar nombres de ciudades en el texto
        for ciudad, codigo in SucursalDetector.CIUDAD_SUCURSAL_MAP.items():
            if ciudad in texto_upper:
                return codigo
        
        return None
    
    @staticmethod
    def extraer_de_note_xml(note: str) -> Optional[str]:
        """
        Extrae código de sucursal del campo Note del XML
        
        Ejemplo: "OC115899-CE23292-CMC MEDICAL-CMC6434-TJA"
        Retorna: "00005" (código de BD para TJA)
        """
        if not note:
            return None
        
        # El código suele estar al final después del último guión
        partes = note.split('-')
        if partes:
            ultimo = partes[-1].strip().upper()
            if ultimo in SucursalDetector.CODIGOS_INTERNOS:
                return SucursalDetector.CODIGO_INTERNO_A_BD.get(ultimo)
        
        # Fallback: buscar en todo el texto
        return SucursalDetector.extraer_de_texto(note)


class ProveedorAnalyzer:
    """Analizador de proveedores con caché"""
    
    # Keywords para clasificación automática
    KEYWORDS_ALMACEN = {
        'FARMAQUIRURGICO', 'FARMA', 'DROGUERIA', 'MEDICAMENTO', 'DISPOSITIVO',
        'MEDICO', 'QUIRURGICO', 'HOSPITAL', 'CLINICA', 'SALUD', 'LABORATORIO',
        'INSUMO', 'SUMINISTRO', 'COFARMA', 'AUDIFARMA', 'EMSSANAR',
        'FARMACEUTICO', 'FARMACIA'
    }
    
    KEYWORDS_ADMINISTRACION = {
        'HOTEL', 'TELECOMUNICACIONES', 'TIGO', 'CLARO', 'MOVISTAR',
        'SERVICIOS', 'MANTENIMIENTO', 'LIMPIEZA', 'VIGILANCIA', 'SEGURIDAD',
        'TRANSPORTE', 'MENSAJERIA', 'PAPELERIA', 'SUMINISTROS OFICINA'
    }
    
    KEYWORDS_SERVICIOS_MEDICOS = {
        'LECTURA', 'RADIOGRAFIA', 'TOMOGRAFIA', 'ECOGRAFIA', 'LABORATORIO',
        'PATOLOGIA', 'IMAGENES', 'DIAGNOSTICO', 'INTERPRETACION'
    }
    
    @staticmethod
    @lru_cache(maxsize=256)
    def clasificar_por_nombre(nombre: str) -> Tuple[str, str]:
        """
        Clasifica proveedor por nombre
        
        Returns:
            Tuple (tipo_clasificacion, unidad_sugerida)
        """
        if not nombre:
            return ('GENERAL', 'ADMINISTRACION')
        
        nombre_upper = nombre.upper()
        
        # Contar coincidencias
        score_almacen = sum(1 for kw in ProveedorAnalyzer.KEYWORDS_ALMACEN if kw in nombre_upper)
        score_admin = sum(1 for kw in ProveedorAnalyzer.KEYWORDS_ADMINISTRACION if kw in nombre_upper)
        score_servicios = sum(1 for kw in ProveedorAnalyzer.KEYWORDS_SERVICIOS_MEDICOS if kw in nombre_upper)
        
        # Determinar clasificación
        if score_almacen > 0:
            if 'FARMA' in nombre_upper:
                return ('FARMACEUTICO', 'ALMACEN')
            else:
                return ('DISPOSITIVOS_MEDICOS', 'ALMACEN')
        elif score_servicios > 0:
            return ('SERVICIOS_MEDICOS', 'ADMINISTRACION')
        elif score_admin > 0:
            if 'HOTEL' in nombre_upper:
                return ('SERVICIOS_GENERALES', 'ADMINISTRACION')
            elif 'TIGO' in nombre_upper or 'TELECOMUNICACIONES' in nombre_upper:
                return ('TELECOMUNICACIONES', 'ADMINISTRACION')
            else:
                return ('SERVICIOS_GENERALES', 'ADMINISTRACION')
        
        return ('GENERAL', 'ADMINISTRACION')


class ScoreCalculator:
    """Calculador de scores con normalización"""
    
    @staticmethod
    def calcular_confidence(score_total: float, score_maximo: float = 2000.0) -> float:
        """
        Calcula confianza normalizada (0.0 a 1.0)
        
        Args:
            score_total: Score total obtenido
            score_maximo: Score máximo esperado (default: 2000)
        
        Returns:
            Confianza entre 0.0 y 1.0
        """
        if score_total <= 0:
            return 0.0
        
        # Normalizar con función sigmoide suave
        confidence = min(score_total / score_maximo, 1.0)
        
        # Aplicar curva para dar más peso a scores altos
        if confidence > 0.5:
            confidence = 0.5 + (confidence - 0.5) * 1.5
        
        return min(confidence, 1.0)
    
    @staticmethod
    def combinar_scores(scores: Dict[str, float], pesos: Dict[str, float]) -> float:
        """
        Combina múltiples scores con pesos
        
        Args:
            scores: Dict con scores por categoría
            pesos: Dict con pesos por categoría
        
        Returns:
            Score total ponderado
        """
        total = 0.0
        for categoria, score in scores.items():
            peso = pesos.get(categoria, 1.0)
            total += score * peso
        
        return total


class TextNormalizer:
    """Normalizador de texto para mejor matching"""
    
    @staticmethod
    @lru_cache(maxsize=512)
    def normalizar(texto: str) -> str:
        """
        Normaliza texto para matching
        
        - Convierte a mayúsculas
        - Elimina acentos
        - Elimina caracteres especiales
        - Normaliza espacios
        """
        if not texto:
            return ""
        
        # Mayúsculas
        texto = texto.upper()
        
        # Eliminar acentos
        replacements = {
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'Ñ': 'N', 'Ü': 'U'
        }
        for old, new in replacements.items():
            texto = texto.replace(old, new)
        
        # Normalizar espacios múltiples
        texto = re.sub(r'\s+', ' ', texto)
        
        return texto.strip()
    
    @staticmethod
    def limpiar_nit(nit: str) -> str:
        """Limpia NIT dejando solo números"""
        if not nit:
            return ""
        
        return re.sub(r'[^0-9]', '', str(nit))


class KeywordMatcher:
    """Matcher de keywords con optimizaciones"""
    
    @staticmethod
    def contar_matches(texto: str, keywords: List[str]) -> Tuple[int, List[str]]:
        """
        Cuenta cuántas keywords coinciden en el texto
        
        Returns:
            Tuple (cantidad, lista_de_matches)
        """
        if not texto or not keywords:
            return (0, [])
        
        texto_norm = TextNormalizer.normalizar(texto)
        matches = []
        
        for keyword in keywords:
            keyword_norm = TextNormalizer.normalizar(keyword)
            if keyword_norm and keyword_norm in texto_norm:
                matches.append(keyword)
        
        return (len(matches), matches)
    
    @staticmethod
    def calcular_score_keywords(texto: str, keywords_con_peso: List[Tuple[str, int]]) -> Tuple[float, List[str]]:
        """
        Calcula score basado en keywords con peso
        
        Args:
            texto: Texto donde buscar
            keywords_con_peso: Lista de tuplas (keyword, peso)
        
        Returns:
            Tuple (score_total, keywords_matched)
        """
        if not texto or not keywords_con_peso:
            return (0.0, [])
        
        texto_norm = TextNormalizer.normalizar(texto)
        score = 0.0
        matches = []
        
        for keyword, peso in keywords_con_peso:
            keyword_norm = TextNormalizer.normalizar(keyword)
            if keyword_norm and keyword_norm in texto_norm:
                score += peso
                matches.append(keyword)
        
        return (score, matches)


class UnidadFuncionalHelper:
    """Helper para trabajar con unidades funcionales"""
    
    @staticmethod
    def extraer_tipo(nombre_unidad: str) -> str:
        """
        Extrae el tipo de unidad funcional
        
        Ejemplo: "ALMACEN-TJA" -> "ALMACEN"
        """
        if not nombre_unidad:
            return ""
        
        # Separar por guión y tomar la primera parte
        partes = nombre_unidad.split('-')
        if partes:
            return partes[0].strip().upper()
        
        return nombre_unidad.upper()
    
    @staticmethod
    def es_coherente(unidad_sucursal_id: int, sucursal_id: int) -> bool:
        """Verifica si la unidad pertenece a la sucursal"""
        return unidad_sucursal_id == sucursal_id
    
    @staticmethod
    def priorizar_por_tipo(unidades: List[Dict], tipo_preferido: str) -> Optional[Dict]:
        """
        Prioriza unidades por tipo
        
        Args:
            unidades: Lista de unidades funcionales
            tipo_preferido: Tipo preferido (ALMACEN, ADMINISTRACION, etc.)
        
        Returns:
            Unidad que coincide con el tipo o None
        """
        for unidad in unidades:
            tipo = UnidadFuncionalHelper.extraer_tipo(unidad.get('nombre', ''))
            if tipo_preferido in tipo:
                return unidad
        
        return None


# Funciones de utilidad general
def validar_nit(nit: str) -> bool:
    """Valida formato de NIT colombiano"""
    if not nit:
        return False
    
    nit_limpio = TextNormalizer.limpiar_nit(nit)
    
    # NIT debe tener entre 6 y 10 dígitos
    return 6 <= len(nit_limpio) <= 10


def extraer_numero_factura(texto: str) -> Optional[str]:
    """
    Extrae número de factura del texto
    
    Busca patrones como: FQE149030, FAC-12345, etc.
    """
    if not texto:
        return None
    
    # Patrón: Letras seguidas de números
    patron = r'\b([A-Z]{2,4}[-]?\d{4,10})\b'
    matches = re.findall(patron, texto.upper())
    
    if matches:
        return matches[0]
    
    return None


def formatear_resultado_clasificacion(sucursal: Dict, unidad: Dict) -> Dict:
    """
    Formatea resultado de clasificación para respuesta consistente
    
    Returns:
        Dict con formato estandarizado
    """
    return {
        'sucursal': {
            'success': sucursal.get('success', False),
            'id': sucursal.get('id'),
            'nombre': sucursal.get('nombre'),
            'codigo': sucursal.get('codigo'),
            'confidence': sucursal.get('confidence', 0.0),
            'metodo': sucursal.get('method', 'unknown')
        },
        'unidad_funcional': {
            'success': unidad.get('success', False),
            'id': unidad.get('id'),
            'nombre': unidad.get('nombre'),
            'codigo': unidad.get('codigo'),
            'confidence': unidad.get('confidence', 0.0),
            'score_total': unidad.get('score_total', 0.0),
            'metodo': unidad.get('method', 'unknown')
        }
    }
