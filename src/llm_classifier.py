"""
Clasificador LLM usando Ollama como fallback de último recurso.
Fase 3 del plan de mejoras con IA.

Requiere Ollama corriendo localmente:
  winget install Ollama.Ollama
  ollama pull llama3.2:3b

Se activa SOLO cuando score de keywords < 50 Y Qdrant no encontró similitud.
"""
import logging
import os
import json
import re
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')
OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT_SECONDS', '15'))

class LLMClassifier:
    """
    Clasificador de último recurso usando LLM local (Ollama).
    Solo se activa cuando los métodos anteriores no tienen suficiente confianza.
    """

    def __init__(self):
        self._available = self._check_ollama()

    @property
    def available(self) -> bool:
        return self._available

    def classify(
        self,
        xml_data: Dict,
        pdf_text: str,
        unidades_disponibles: List[Dict]
    ) -> Optional[Dict]:
        """
        Clasifica usando el LLM.

        Args:
            xml_data: Datos estructurados del XML (proveedor, factura, cliente)
            pdf_text: Texto del PDF
            unidades_disponibles: Lista de unidades funcionales activas de la BD

        Returns:
            Dict con clasificación o None si falla
        """
        if not self._available:
            return None

        try:
            prompt = self._build_prompt(xml_data, pdf_text, unidades_disponibles)
            respuesta = self._call_ollama(prompt)

            if not respuesta:
                return None

            return self._parse_response(respuesta, unidades_disponibles)

        except Exception as e:
            logger.error(f"Error en LLMClassifier: {e}")
            return None

    def _build_prompt(
        self,
        xml_data: Dict,
        pdf_text: str,
        unidades: List[Dict]
    ) -> str:
        """Construye el prompt para el LLM."""
        proveedor = xml_data.get('proveedor', {})
        factura = xml_data.get('factura', {})
        cliente = xml_data.get('cliente', {})

        # Extraer ítems del PDF (primeras líneas relevantes)
        items_texto = self._extraer_items(pdf_text)

        # Construir lista de unidades
        unidades_str = '\n'.join(
            f"- {u['codigo']}: {u['nombre']}"
            for u in unidades
        )

        ciudad = cliente.get('ciudad', 'desconocida')

        prompt = f"""Eres un clasificador de facturas para una clínica médica colombiana llamada Clinica Medilaser.

FACTURA:
- Proveedor: {proveedor.get('nombre', 'desconocido')}
- NIT proveedor: {proveedor.get('nit', '')}
- Ciudad de entrega: {ciudad}
- Número factura: {factura.get('numero', '')}

ÍTEMS O DESCRIPCIÓN:
{items_texto}

UNIDADES FUNCIONALES DISPONIBLES:
{unidades_str}

REGLAS:
- Si los ítems son medicamentos, insumos médicos, material quirúrgico o dispositivos médicos → elige la unidad ALMACEN de la ciudad correspondiente
- Si son servicios, telecomunicaciones, mantenimiento, energía, agua, honorarios → elige ADMINISTRACION de la ciudad correspondiente
- La ciudad {ciudad} corresponde a la sucursal de esa ciudad

Responde ÚNICAMENTE con el código de la unidad funcional. Sin explicación. Solo el código.
Ejemplo de respuesta válida: ALMACEN-NVA"""

        return prompt

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Llama a la API de Ollama."""
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Baja temperatura = respuestas más deterministas
                        "num_predict": 20,   # Solo necesitamos el código, no texto largo
                    }
                },
                timeout=OLLAMA_TIMEOUT
            )

            if response.status_code == 200:
                return response.json().get('response', '').strip()
            else:
                logger.warning(f"Ollama respondió {response.status_code}")
                return None

        except requests.exceptions.ConnectionError:
            logger.warning(f"Ollama no disponible en {OLLAMA_URL}")
            self._available = False
            return None
        except requests.exceptions.Timeout:
            logger.warning(f"Ollama timeout ({OLLAMA_TIMEOUT}s)")
            return None

    def _parse_response(
        self,
        respuesta: str,
        unidades: List[Dict]
    ) -> Optional[Dict]:
        """
        Parsea la respuesta del LLM y la mapea a una unidad funcional real.
        El LLM puede responder con el código exacto o con texto libre.
        """
        respuesta_upper = respuesta.upper().strip()

        # Buscar coincidencia exacta con código de unidad
        for unidad in unidades:
            codigo = unidad.get('codigo', '').upper()
            if codigo and codigo in respuesta_upper:
                logger.info(f"LLM clasificó como: {unidad['nombre']} (código: {codigo})")
                return {
                    'success': True,
                    'id': unidad['id'],
                    'nombre': unidad['nombre'],
                    'codigo': unidad['codigo'],
                    'sucursal_id': unidad.get('sucursal_id'),
                    'score': 40,  # Score bajo porque es LLM fallback
                    'confidence': 0.6,
                    'method': 'llm_ollama',
                    'keywords': [f'llm_response={respuesta[:50]}']
                }

        # Buscar por nombre parcial si no hay código exacto
        for unidad in unidades:
            nombre = unidad.get('nombre', '').upper()
            # Detectar ALMACEN vs ADMINISTRACION en la respuesta
            if 'ALMAC' in respuesta_upper and 'ALMAC' in nombre:
                return {
                    'success': True,
                    'id': unidad['id'],
                    'nombre': unidad['nombre'],
                    'codigo': unidad['codigo'],
                    'sucursal_id': unidad.get('sucursal_id'),
                    'score': 30,
                    'confidence': 0.5,
                    'method': 'llm_ollama_partial',
                    'keywords': [f'llm_response={respuesta[:50]}']
                }

        logger.warning(f"LLM respondió algo no reconocible: '{respuesta}'")
        return None

    def _extraer_items(self, pdf_text: str) -> str:
        """Extrae las líneas más relevantes del PDF para el prompt."""
        if not pdf_text:
            return "(sin texto de PDF disponible)"

        lineas = pdf_text.split('\n')
        # Filtrar líneas que parecen ítems (tienen números, descripciones)
        relevantes = []
        for linea in lineas:
            linea = linea.strip()
            if len(linea) > 10 and not linea.startswith('http'):
                relevantes.append(linea)
            if len(relevantes) >= 15:
                break

        return '\n'.join(relevantes) if relevantes else pdf_text[:500]

    def _check_ollama(self) -> bool:
        """Verifica si Ollama está disponible."""
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
            if response.status_code == 200:
                modelos = [m['name'] for m in response.json().get('models', [])]
                if any(OLLAMA_MODEL in m for m in modelos):
                    logger.info(f"Ollama disponible con modelo {OLLAMA_MODEL}")
                    return True
                else:
                    logger.warning(
                        f"Ollama disponible pero modelo '{OLLAMA_MODEL}' no instalado. "
                        f"Modelos disponibles: {modelos}. "
                        f"Ejecuta: ollama pull {OLLAMA_MODEL}"
                    )
                    return False
        except Exception:
            pass
        return False


# Instancia global
_llm_classifier: Optional[LLMClassifier] = None


def get_llm_classifier() -> LLMClassifier:
    global _llm_classifier
    if _llm_classifier is None:
        _llm_classifier = LLMClassifier()
    return _llm_classifier
