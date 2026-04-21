"""
Extractor de datos de Comprobantes de Egreso en PDF.

Extrae de cualquier comprobante de egreso:
- Consecutivo
- Fecha
- Estado
- Valor
- NIT del beneficiario
- Nombre del beneficiario
- Banco
- Detalle / Planilla
- Facturas afectadas
- Detalle del movimiento contable
"""

import pdfplumber
import re
import os
from typing import Dict, List, Optional
from .logger import ocr_logger


class ComprobanteEgresoExtractor:
    """Extrae datos estructurados de comprobantes de egreso en PDF"""

    def extract(self, pdf_path: str) -> Dict:
        """
        Extrae todos los datos de un comprobante de egreso PDF.
        Solo procesa archivos que contengan "COMPROBANTE DE EGRESO" en su contenido.

        Args:
            pdf_path: Ruta al archivo PDF

        Returns:
            Dict con los datos extraídos
        """
        if not os.path.exists(pdf_path):
            return {'success': False, 'error': f'Archivo no encontrado: {pdf_path}'}

        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    return {'success': False, 'error': 'PDF sin páginas'}

                # Extraer tablas de la primera página
                page = pdf.pages[0]
                tables = page.extract_tables()
                text = page.extract_text() or ''

                # Validar que sea un comprobante de egreso
                if not self._es_comprobante_egreso(text):
                    return {
                        'success': False,
                        'error': 'El documento no es un Comprobante de Egreso',
                        'tipo_documento': 'NO_COMPROBANTE_EGRESO'
                    }

                datos = self._inicializar_datos()

                # Estrategia 1: Extraer desde tablas (más preciso)
                if tables:
                    self._extraer_desde_tablas(tables, datos)

                # Estrategia 2: Complementar con texto si faltan campos
                if not datos['consecutivo'] or not datos['beneficiario_nit']:
                    self._extraer_desde_texto(text, datos)

                # Si hay más páginas, buscar facturas adicionales
                for page_extra in pdf.pages[1:]:
                    tables_extra = page_extra.extract_tables()
                    if tables_extra:
                        self._extraer_facturas_extra(tables_extra, datos)

                datos['success'] = bool(datos['consecutivo'] and datos['valor'] > 0)

                return datos

        except Exception as e:
            ocr_logger.log_error(
                endpoint="ComprobanteEgresoExtractor.extract",
                error_message=str(e),
                error_type=type(e).__name__
            )
            return {'success': False, 'error': str(e)}

    def extract_multiple(self, pdf_paths: List[str]) -> Dict:
        """
        Extrae datos de múltiples comprobantes de egreso.

        Args:
            pdf_paths: Lista de rutas a PDFs

        Returns:
            Dict con resumen y lista de comprobantes
        """
        comprobantes = []
        errores = []

        for path in pdf_paths:
            resultado = self.extract(path)
            resultado['archivo'] = os.path.basename(path)

            if resultado.get('success'):
                comprobantes.append(resultado)
            else:
                errores.append(resultado)

        valor_total = sum(c.get('valor', 0) for c in comprobantes)

        return {
            'success': True,
            'total_procesados': len(pdf_paths),
            'exitosos': len(comprobantes),
            'con_errores': len(errores),
            'valor_total': valor_total,
            'valor_total_formatted': f"${valor_total:,.2f}",
            'comprobantes': comprobantes,
            'errores': errores
        }

    # ============================================
    # MÉTODOS PRIVADOS
    # ============================================

    def _es_comprobante_egreso(self, text: str) -> bool:
        """
        Valida que el PDF sea un Comprobante de Egreso.
        Busca la frase 'COMPROBANTE DE EGRESO' en el texto del documento.
        """
        text_upper = text.upper()
        return 'COMPROBANTE DE EGRESO' in text_upper

    def _inicializar_datos(self) -> Dict:
        return {
            'success': False,
            'consecutivo': '',
            'fecha': '',
            'estado': '',
            'valor': 0,
            'valor_formatted': '',
            'beneficiario_nit': '',
            'beneficiario_nombre': '',
            'banco': '',
            'detalle': '',
            'planilla': '',
            'impuesto_x_mil': 0,
            'movimientos': [],
            'facturas': []
        }

    def _extraer_desde_tablas(self, tables: List, datos: Dict):
        """Extrae datos desde las tablas del PDF"""

        for table in tables:
            if not table:
                continue

            header = str(table[0][0] or '').upper() if table[0] else ''

            # TABLA: DATOS GENERALES
            if 'DATOS GENERALES' in header or any(
                'Consecutivo' in str(row[0] or '') for row in table if row and row[0]
            ):
                self._parse_datos_generales(table, datos)

            # TABLA: DATOS DEL PAGO
            elif 'PAGO' in header and 'NOTA' in header:
                self._parse_datos_pago(table, datos)

            # TABLA: DETALLE DEL MOVIMIENTO
            elif 'DETALLE DEL MOVIMIENTO' in header or (
                len(table) > 1 and table[1] and 'CONCEPTO' in str(table[1][0] or '').upper()
            ):
                self._parse_movimientos(table, datos)

            # TABLA: FACTURAS AFECTADAS
            elif 'FACTURAS AFECTADAS' in header or (
                len(table) > 1 and table[1] and 'FACTURA' in str(table[1][0] or '').upper()
            ):
                self._parse_facturas(table, datos)

    def _parse_datos_generales(self, table: List, datos: Dict):
        """Parsea la tabla DATOS GENERALES"""
        for row in table:
            if not row or not row[0]:
                continue

            cell0 = str(row[0]).strip()

            # Consecutivo
            if 'Consecutivo' in cell0:
                datos['consecutivo'] = str(row[1]).strip() if row[1] else ''
                if len(row) > 3 and row[3]:
                    datos['estado'] = str(row[3]).strip()

            # Fecha y Valor
            elif 'Fecha' in cell0 and 'Documento' in cell0:
                datos['fecha'] = str(row[1]).strip() if row[1] else ''
                if len(row) > 3 and row[3]:
                    datos['valor_formatted'] = str(row[3]).strip()
                    datos['valor'] = self._parse_valor_colombiano(str(row[3]))

            # Beneficiario
            elif 'Beneficiario' in cell0:
                beneficiario = str(row[1]).strip() if row[1] else ''
                m = re.match(r'(\d+)\s*-\s*(.+)', beneficiario)
                if m:
                    datos['beneficiario_nit'] = m.group(1).strip()
                    datos['beneficiario_nombre'] = m.group(2).strip()
                else:
                    datos['beneficiario_nombre'] = beneficiario

            # Banco
            elif 'Banco' in cell0 and 'Valor' not in cell0:
                datos['banco'] = str(row[1]).strip() if row[1] else ''

            # Detalle
            elif 'Detalle' in cell0:
                detalle = str(row[1]).strip() if row[1] else ''
                datos['detalle'] = detalle
                # Extraer número de planilla
                m = re.search(r'Planilla.*?No\s*(\d+)', detalle, re.IGNORECASE)
                if not m:
                    m = re.search(r'Planilla\D*(\d+)', detalle, re.IGNORECASE)
                if m:
                    datos['planilla'] = m.group(1)

    def _parse_datos_pago(self, table: List, datos: Dict):
        """Parsea la tabla DATOS DEL PAGO NOTA DEBITO"""
        for row in table:
            if not row or not row[0]:
                continue

            cell0 = str(row[0]).strip()

            if 'Banco' in cell0 and row[1]:
                banco = str(row[1]).strip()
                if banco and not datos['banco']:
                    datos['banco'] = banco

            if 'Impuesto' in cell0 and 'Mil' in cell0:
                for cell in row:
                    if cell and '$' in str(cell):
                        datos['impuesto_x_mil'] = self._parse_valor_colombiano(str(cell))
                        break

    def _parse_movimientos(self, table: List, datos: Dict):
        """Parsea la tabla DETALLE DEL MOVIMIENTO"""
        for row in table:
            if not row or not row[0]:
                continue

            cell0 = str(row[0]).strip()
            if cell0 in ('DETALLE DEL MOVIMIENTO', 'CONCEPTO', ''):
                continue

            concepto = cell0
            tercero = str(row[1]).strip() if len(row) > 1 and row[1] else ''
            cuenta = str(row[2]).strip() if len(row) > 2 and row[2] else ''
            debito = self._parse_valor_colombiano(str(row[3])) if len(row) > 3 and row[3] else 0
            credito = self._parse_valor_colombiano(str(row[4])) if len(row) > 4 and row[4] else 0

            if concepto and (debito > 0 or credito > 0):
                datos['movimientos'].append({
                    'concepto': concepto.replace('\n', ' '),
                    'tercero': tercero,
                    'cuenta': cuenta,
                    'debito': debito,
                    'credito': credito
                })

    def _parse_facturas(self, table: List, datos: Dict):
        """Parsea la tabla FACTURAS AFECTADAS"""
        skip = ('FACTURAS AFECTADAS', 'FACTURA', 'PREPARADO', 'C.C. N.I.T', '')

        for row in table:
            if not row or not row[0]:
                continue

            cell0 = str(row[0]).strip()
            if cell0.upper() in skip:
                continue

            factura_num = cell0
            detalle = str(row[1]).strip().replace('\n', ' ') if len(row) > 1 and row[1] else ''

            # Buscar valor en la última columna con $
            valor_str = ''
            for cell in reversed(row):
                if cell and '$' in str(cell):
                    valor_str = str(cell).strip()
                    break

            datos['facturas'].append({
                'numero': factura_num,
                'detalle': detalle,
                'valor': self._parse_valor_colombiano(valor_str),
                'valor_formatted': valor_str
            })

    def _extraer_facturas_extra(self, tables: List, datos: Dict):
        """Extrae facturas de páginas adicionales"""
        for table in tables:
            if not table:
                continue
            header = str(table[0][0] or '').upper() if table[0] else ''
            if 'FACTURAS' in header or (
                len(table) > 1 and table[1] and 'FACTURA' in str(table[1][0] or '').upper()
            ):
                self._parse_facturas(table, datos)

    def _extraer_desde_texto(self, text: str, datos: Dict):
        """Fallback: extrae datos desde texto plano si las tablas no funcionaron"""

        if not datos['consecutivo']:
            m = re.search(r'Consecutivo\s*:?\s*(\d+)', text)
            if m:
                datos['consecutivo'] = m.group(1)

        if not datos['beneficiario_nit']:
            m = re.search(r'Beneficiario\s*:?\s*(\d+)\s*-\s*(.+?)(?:\n|$)', text)
            if m:
                datos['beneficiario_nit'] = m.group(1).strip()
                datos['beneficiario_nombre'] = m.group(2).strip()

        if datos['valor'] == 0:
            m = re.search(r'Valor\s*:?\s*\$\s*([\d.,]+)', text)
            if m:
                datos['valor'] = self._parse_valor_colombiano(m.group(1))
                datos['valor_formatted'] = f"$ {m.group(1)}"

        if not datos['estado']:
            m = re.search(r'Estado\s*:?\s*(\w+)', text)
            if m:
                datos['estado'] = m.group(1)

        if not datos['fecha']:
            m = re.search(r'Fecha del Documento\s*:?\s*(.+?)(?:\n|Valor)', text)
            if m:
                datos['fecha'] = m.group(1).strip()

    def _parse_valor_colombiano(self, valor_str: str) -> float:
        """
        Parsea un valor en formato colombiano: $ 11.610.299,00
        Puntos = miles, coma = decimal
        """
        if not valor_str:
            return 0

        # Limpiar: quitar $, espacios
        nums = re.sub(r'[^\d,.]', '', str(valor_str))

        if not nums:
            return 0

        try:
            
            if ',' in nums:
                partes = nums.rsplit(',', 1)
                entero = partes[0].replace('.', '')
                decimal = partes[1] if len(partes) > 1 else '00'
                return float(f"{entero}.{decimal}")
            else:
                # Sin coma, solo puntos como miles
                return float(nums.replace('.', ''))
        except (ValueError, IndexError):
            return 0
