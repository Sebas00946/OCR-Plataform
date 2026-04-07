"""
Extractor de texto de XML y PDF
Extrae datos estructurados de facturas electrónicas colombianas
Optimizado para pdfplumber con extracción mejorada
"""
import xml.etree.ElementTree as ET
import pdfplumber
import re
import traceback
import os
from typing import Dict, Tuple, Optional
from .logger import ocr_logger


class InvoiceExtractor:
    """Extrae texto y datos estructurados de facturas XML y PDF"""
    
    # Namespaces comunes en facturas electrónicas colombianas
    NAMESPACES = {
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
        'sts': 'dian:gov:co:facturaelectronica:Structures-2-1',
        'fe': 'http://www.dian.gov.co/contratos/facturaelectronica/v1'
    }
    
    # Patrones regex para extraer datos del PDF
    PATTERNS = {
        # NIT con diferentes formatos
        'nit': [
            r'NIT[:\s]*[:\.]?\s*(\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[\s-]*\d?)',  # NIT: 900.123.456-7
            r'NIT[:\s]*(\d{9,10}[\s-]*\d?)',  # NIT: 9001234567
            r'Nit[:\s]*[:\.]?\s*(\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[\s-]*\d?)',
            r'N\.?I\.?T\.?[:\s]*(\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[\s-]*\d?)',
        ],
        # Número de factura
        'numero_factura': [
            r'(?:FACTURA|FE|FV|FVE|FEPN|FQE|No\.?|N[°º])[:\s]*([A-Z]*\s*\d+)',
            r'Nro\.?\s*Doc\.?[:\s]*([A-Z]?\d+)',
            r'(?:FACTURA ELECTR[OÓ]NICA)[^\d]*(\d+)',
            r'No\.\s*(?:FE|FV|FVE|FEPN|FQE)\s*(\d+)',
            r'N[°º]\s*(?:FE|FV|FVE|FEPN|FQE)\s*(\d+)',
        ],
        # Razón social / Nombre del proveedor (al inicio del documento)
        'razon_social': [
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.]+(?:S\.?A\.?S\.?|LTDA\.?|S\.?A\.?))',
            r'Raz[oó]n\s*social/?Nombre[:\s]*([^\n]+)',
            r'Datos\s+del\s+Emisor[^\n]*\n[^\n]*Raz[oó]n\s*social/?Nombre[:\s]*([^\n]+)',
        ],
        # Orden de Compra (múltiples formatos - GENÉRICO)
        'orden_compra': [
            # Formato 1: "ORDEN DE COMPRA No. XXX-2026-139"
            r'ORDEN\s+DE\s+COMPRA\s+No\.?\s*[:\s]*([A-Z0-9\-/]+)',
            # Formato 2: "Orden de Compra: XXX-2025-6327"
            r'Orden\s+de\s+Compra[:\s]+([A-Z0-9\-/]+)',
            # Formato 3: "O.C: XXX" o "OC: XXX"
            r'\bO\.?\s*C\.?\s*[:\s]+([A-Z0-9\-/]+)',
            # Formato 4: "Purchase Order: XXX" o "P.O: XXX"
            r'(?:Purchase\s+Order|P\.?\s*O\.?)\s*[:\s]+([A-Z0-9\-/]+)',
            # Formato 5: "Pedido:" o "Pedido No:"
            r'Pedido\s*(?:No\.?|N[°º])?\s*[:\s]+([A-Z0-9\-/]+)',
            # Formato 6: "Ref:" o "Referencia:"
            r'(?:Ref|Referencia)[:\s]+([A-Z0-9\-/]+)',
        ],
    }
    
    def extract_from_xml(self, xml_path: str) -> Tuple[str, float, Dict]:
        """
        Extrae texto del XML y datos estructurados del proveedor
        
        Returns:
            Tuple[str, float, Dict]: (texto_extraido, calidad_0_a_1, datos_estructurados)
        """
        if not os.path.exists(xml_path):
            ocr_logger.log_error("InvoiceExtractor", f"Archivo XML no encontrado: {xml_path}")
            return "", 0.0, {'proveedor': {}, 'factura': {}, 'cliente': {}}

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Intentar extraer el Invoice embebido en CDATA
            embedded_invoice_root = self._extract_embedded_invoice(root)
            if embedded_invoice_root is not None:
                # Si hay Invoice embebido, usarlo como root principal
                invoice_root = embedded_invoice_root
            else:
                # Si no hay embebido, usar el root actual
                invoice_root = root
            
            parts = []
            quality_score = 0
            max_quality = 8  # Número de campos importantes
            
            # Diccionario para datos estructurados
            structured_data = {
                'proveedor': {},
                'factura': {},
                'cliente': {}
            }
            
            # ============================================
            # DATOS DEL PROVEEDOR (EMISOR)
            # ============================================
            
            # Nombre/Razón Social del proveedor
            supplier = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:PartyLegalEntity//cbc:RegistrationName',
                './/cac:AccountingSupplierParty//cac:Party//cac:PartyName//cbc:Name',
                './/cac:SenderParty//cac:PartyLegalEntity//cbc:RegistrationName',
                './/cac:SenderParty//cbc:RegistrationName',
            ])
            if supplier:
                parts.append(supplier)
                quality_score += 1
                structured_data['proveedor']['nombre'] = supplier.strip()
                structured_data['proveedor']['razon_social'] = supplier.strip()
            
            # NIT del proveedor (múltiples ubicaciones posibles)
            supplier_nit = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:PartyTaxScheme//cbc:CompanyID',
                './/cac:AccountingSupplierParty//cac:Party//cac:PartyIdentification//cbc:ID',
                './/cac:AccountingSupplierParty//cac:Party//cac:PartyLegalEntity//cbc:CompanyID',
                './/cac:SenderParty//cac:PartyTaxScheme//cbc:CompanyID',
            ])
            if supplier_nit:
                structured_data['proveedor']['nit_original'] = supplier_nit.strip()
                structured_data['proveedor']['nit'] = self._limpiar_nit(supplier_nit)
                quality_score += 1
            
            # Dirección del proveedor
            supplier_address = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:PhysicalLocation//cac:Address//cbc:Line',
                './/cac:AccountingSupplierParty//cac:Party//cac:PostalAddress//cbc:Line',
                './/cac:AccountingSupplierParty//cac:Party//cac:PartyLegalEntity//cac:RegistrationAddress//cbc:Line',
            ])
            if supplier_address:
                structured_data['proveedor']['direccion'] = supplier_address.strip()
            
            # Ciudad del proveedor
            supplier_city = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:PhysicalLocation//cac:Address//cbc:CityName',
                './/cac:AccountingSupplierParty//cac:Party//cac:PostalAddress//cbc:CityName',
            ])
            if supplier_city:
                structured_data['proveedor']['ciudad'] = supplier_city.strip()
            
            # Teléfono del proveedor
            supplier_phone = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:Contact//cbc:Telephone',
            ])
            if supplier_phone:
                structured_data['proveedor']['telefono'] = supplier_phone.strip()
            
            # Email del proveedor
            supplier_email = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:Contact//cbc:ElectronicMail',
            ])
            if supplier_email:
                structured_data['proveedor']['email'] = supplier_email.strip()
            
            # ============================================
            # DATOS DE LA FACTURA
            # ============================================
            
            # Número de factura - buscar en múltiples ubicaciones
            # Prioridad: ParentDocumentID > Note > ID
            invoice_number = None
            
            # 1. Buscar en ParentDocumentID (para AttachedDocument)
            parent_doc_id = self._extract_text(root, [
                './/cbc:ParentDocumentID',
            ])
            if parent_doc_id:
                invoice_number = parent_doc_id.strip()
            
            # 2. Si no hay ParentDocumentID, buscar en Note que contenga el número
            if not invoice_number:
                notes_list = self._extract_all_text(root, ['.//cbc:Note'])
                for note in notes_list:
                    # Buscar patrones como "FEPN1746", "FE 356", etc.
                    match = re.search(r'(?:FEPN|FE|FV|FVE)\s*(\d+)', note, re.IGNORECASE)
                    if match:
                        prefix_match = re.search(r'(FEPN|FE|FV|FVE)', note, re.IGNORECASE)
                        prefix = prefix_match.group(1) if prefix_match else ''
                        invoice_number = f"{prefix}{match.group(1)}"
                        break
            
            # 3. Si aún no hay, buscar en el Invoice embebido (dentro de CDATA)
            if not invoice_number:
                # Buscar en el texto completo del XML por patrones de factura
                try:
                    import re
                    xml_content = ET.tostring(root, encoding='unicode')
                    # Buscar <cbc:ID> dentro del Invoice embebido
                    # Patrón para encontrar el ID de la factura real (no el del AttachedDocument)
                    invoice_match = re.search(r'<Invoice[^>]*>.*?<cbc:ID>([A-Z]*\d+)</cbc:ID>', xml_content, re.DOTALL)
                    if invoice_match:
                        invoice_number = invoice_match.group(1)
                except:
                    pass
            
            # 4. Último recurso: usar cbc:ID pero solo si parece un número de factura válido
            if not invoice_number:
                doc_id = self._extract_text(root, ['.//cbc:ID'])
                if doc_id:
                    # Solo usar si tiene formato de factura (no es un número muy largo como CUFE)
                    if len(doc_id) <= 15 and not doc_id.isdigit():
                        invoice_number = doc_id.strip()
                    elif len(doc_id) <= 10:
                        invoice_number = doc_id.strip()
            
            if invoice_number:
                structured_data['factura']['numero'] = invoice_number
                quality_score += 1
            
            # Fecha de emisión
            invoice_date = self._extract_text(root, [
                './/cbc:IssueDate',
            ])
            if invoice_date:
                structured_data['factura']['fecha'] = invoice_date.strip()
            
            # CUFE
            cufe = self._extract_text(root, [
                './/cbc:UUID',
            ])
            if cufe:
                structured_data['factura']['cufe'] = cufe.strip()
            
            # Orden de Compra (puede estar en OrderReference)
            orden_compra = self._extract_text(invoice_root, [
                './/cac:OrderReference//cbc:ID',
            ])
            if orden_compra:
                structured_data['factura']['orden_compra'] = orden_compra.strip()
            
            # Note (puede contener información importante como código de sucursal)
            note = self._extract_text(invoice_root, [
                './/cbc:Note',
            ])
            if note:
                structured_data['factura']['note'] = note.strip()
                structured_data['factura']['notas'] = note.strip()  # Alias
                # Agregar al texto para búsqueda
                parts.append(note)
            
            # ============================================
            # VALORES MONETARIOS
            # ============================================
            
            valores = {}
            
            # Subtotal (LineExtensionAmount) - Valor antes de impuestos
            subtotal = self._extract_text(invoice_root, [
                './/cac:LegalMonetaryTotal//cbc:LineExtensionAmount',
            ])
            if subtotal:
                try:
                    valores['subtotal'] = float(subtotal.strip())
                    valores['subtotal_formatted'] = f"${float(subtotal.strip()):,.2f}"
                except:
                    pass
            
            # Total sin impuestos (TaxExclusiveAmount)
            tax_exclusive = self._extract_text(invoice_root, [
                './/cac:LegalMonetaryTotal//cbc:TaxExclusiveAmount',
            ])
            if tax_exclusive:
                try:
                    valores['tax_exclusive'] = float(tax_exclusive.strip())
                except:
                    pass
            
            # Total con impuestos (TaxInclusiveAmount)
            tax_inclusive = self._extract_text(invoice_root, [
                './/cac:LegalMonetaryTotal//cbc:TaxInclusiveAmount',
            ])
            if tax_inclusive:
                try:
                    valores['tax_inclusive'] = float(tax_inclusive.strip())
                except:
                    pass
            
            # Total a pagar (PayableAmount) - Este es el valor final
            total = self._extract_text(invoice_root, [
                './/cac:LegalMonetaryTotal//cbc:PayableAmount',
            ])
            if total:
                try:
                    valores['total'] = float(total.strip())
                    valores['total_formatted'] = f"${float(total.strip()):,.2f}"
                except:
                    pass
            
            # IVA (TaxAmount del TaxTotal)
            iva = self._extract_text(invoice_root, [
                './/cac:TaxTotal//cbc:TaxAmount',
            ])
            if iva:
                try:
                    valores['iva'] = float(iva.strip())
                    valores['iva_formatted'] = f"${float(iva.strip()):,.2f}"
                except:
                    pass
            
            # Retenciones (WithholdingTaxTotal) - Solo del nivel de Invoice, no de líneas
            retenciones = []
            retenciones_agrupadas = {}  # Para agrupar por tipo
            
            # Buscar solo las retenciones a nivel de Invoice (no dentro de InvoiceLine)
            # Primero, obtener todos los WithholdingTaxTotal que NO estén dentro de InvoiceLine
            for wht in invoice_root.findall('.//cac:WithholdingTaxTotal', self.NAMESPACES):
                # Verificar que no esté dentro de un InvoiceLine
                parent = wht
                is_in_invoice_line = False
                
                # Recorrer hacia arriba para ver si está dentro de InvoiceLine
                # Como ElementTree no tiene parent, usaremos una búsqueda diferente
                # Buscaremos solo los WithholdingTaxTotal que sean hijos directos del Invoice
                
                # Obtener el path del elemento
                try:
                    # Verificar si el padre es Invoice (no InvoiceLine)
                    # Buscar en el nivel correcto
                    invoice_wht = invoice_root.findall('./cac:WithholdingTaxTotal', self.NAMESPACES)
                    if wht in invoice_wht:
                        # Este es un WithholdingTaxTotal a nivel de Invoice
                        tax_amount_elem = wht.find('.//cbc:TaxAmount', self.NAMESPACES)
                        if tax_amount_elem is not None and tax_amount_elem.text:
                            try:
                                # Obtener el tipo de retención
                                tax_category = wht.find('.//cac:TaxCategory//cac:TaxScheme//cbc:Name', self.NAMESPACES)
                                tax_name = tax_category.text if tax_category is not None else 'Retención'
                                
                                # Obtener el porcentaje
                                percent_elem = wht.find('.//cac:TaxCategory//cbc:Percent', self.NAMESPACES)
                                percent = float(percent_elem.text) if percent_elem is not None and percent_elem.text else 0
                                
                                valor = float(tax_amount_elem.text.strip())
                                
                                # Agrupar por nombre y porcentaje
                                key = f"{tax_name}_{percent}"
                                if key not in retenciones_agrupadas:
                                    retenciones_agrupadas[key] = {
                                        'nombre': tax_name,
                                        'porcentaje': percent,
                                        'valor': 0
                                    }
                                retenciones_agrupadas[key]['valor'] += valor
                            except:
                                pass
                except:
                    pass
            
            # Convertir a lista y formatear
            if retenciones_agrupadas:
                for ret_data in retenciones_agrupadas.values():
                    ret_data['valor_formatted'] = f"${ret_data['valor']:,.2f}"
                    retenciones.append(ret_data)
                
                valores['retenciones'] = retenciones
                valores['total_retenciones'] = sum(r['valor'] for r in retenciones)
                valores['total_retenciones_formatted'] = f"${sum(r['valor'] for r in retenciones):,.2f}"
            
            # Calcular IVA si no está explícito
            if 'iva' not in valores and 'subtotal' in valores and 'total' in valores:
                iva_calculado = valores['total'] - valores['subtotal']
                if iva_calculado > 0:
                    valores['iva'] = iva_calculado
                    valores['iva_formatted'] = f"${iva_calculado:,.2f}"
            
            # Calcular valor neto (total - retenciones) y redondear
            if 'total' in valores and 'total_retenciones' in valores:
                # Guardar el total original de la factura (con IVA)
                total_factura_original = valores['total']
                valores['total_factura'] = total_factura_original
                valores['total_factura_formatted'] = f"${total_factura_original:,.2f}"
                
                # Calcular valor neto (lo que realmente se paga)
                valor_neto = valores['total'] - valores['total_retenciones']
                # Redondear al peso más cercano para coincidir con PDFs
                valor_neto_redondeado = round(valor_neto)
                valores['valor_neto'] = valor_neto_redondeado
                valores['valor_neto_exacto'] = valor_neto  # Guardar valor exacto también
                valores['valor_neto_formatted'] = f"${valor_neto_redondeado:,.2f}"
                
                # ⚠️ IMPORTANTE: Reemplazar 'total' con 'valor_neto' para que la API de Node.js
                # guarde el valor correcto (lo que se paga) en trazabilidad_facturas.valor_total
                valores['total'] = valor_neto_redondeado
                valores['total_formatted'] = f"${valor_neto_redondeado:,.2f}"
                
                # También actualizar tax_inclusive si existe (debe ser igual al valor neto)
                if 'tax_inclusive' in valores:
                    valores['tax_inclusive_original'] = valores['tax_inclusive']
                    valores['tax_inclusive'] = valor_neto_redondeado
                    valores['tax_inclusive_formatted'] = f"${valor_neto_redondeado:,.2f}"
            
            # Agregar valores a la estructura
            if valores:
                structured_data['factura']['valores'] = valores
            
            # ============================================
            # DATOS DEL CLIENTE (RECEPTOR)
            # ============================================
            
            customer = self._extract_text(root, [
                './/cac:AccountingCustomerParty//cac:Party//cac:PartyLegalEntity//cbc:RegistrationName',
                './/cac:AccountingCustomerParty//cac:Party//cac:PartyName//cbc:Name',
                './/cac:ReceiverParty//cbc:RegistrationName',
            ])
            if customer:
                parts.append(customer)
                quality_score += 1
                structured_data['cliente']['nombre'] = customer.strip()
            
            # NIT del cliente
            customer_nit = self._extract_text(root, [
                './/cac:AccountingCustomerParty//cac:Party//cac:PartyTaxScheme//cbc:CompanyID',
                './/cac:AccountingCustomerParty//cac:Party//cac:PartyIdentification//cbc:ID',
            ])
            if customer_nit:
                structured_data['cliente']['nit'] = self._limpiar_nit(customer_nit)
            
            # ============================================
            # DIRECCIÓN DE ENTREGA (IMPORTANTE PARA CLASIFICACIÓN)
            # ============================================
            
            # Dirección de entrega (PESO ALTO - 3x para priorizar)
            address = self._extract_text(root, [
                './/cac:Delivery//cac:DeliveryLocation//cac:Address//cbc:Line',
                './/cac:Delivery//cac:DeliveryAddress//cbc:Line',
                './/cac:AccountingCustomerParty//cac:Party//cac:PhysicalLocation//cac:Address//cbc:Line',
                './/cac:AccountingCustomerParty//cac:Party//cac:PostalAddress//cbc:Line',
            ])
            if address:
                parts.extend([address] * 3)  # Repetir 3 veces para dar más peso
                quality_score += 1
                structured_data['cliente']['direccion'] = address.strip()
            
            # Ciudad de entrega (PESO ALTO - 3x para priorizar)
            city = self._extract_text(root, [
                './/cac:Delivery//cac:DeliveryLocation//cac:Address//cbc:CityName',
                './/cac:Delivery//cac:DeliveryAddress//cbc:CityName',
                './/cac:AccountingCustomerParty//cac:Party//cac:PhysicalLocation//cac:Address//cbc:CityName',
                './/cac:AccountingCustomerParty//cac:Party//cac:PostalAddress//cbc:CityName',
            ])
            if city:
                parts.extend([city] * 3)  # Repetir 3 veces para dar más peso
                quality_score += 1
                structured_data['cliente']['ciudad'] = city.strip()
            
            # ============================================
            # OBSERVACIONES E ITEMS
            # ============================================
            
            # Observaciones/Notas
            notes = self._extract_all_text(root, ['.//cbc:Note', './/cbc:Description'])
            if notes:
                parts.extend(notes)
                quality_score += 1
            
            # Items/Productos
            items = self._extract_all_text(root, [
                './/cac:InvoiceLine//cbc:Description',
                './/cac:Item//cbc:Description'
            ])
            if items:
                parts.extend(items[:10])  # Máximo 10 items
                quality_score += 1
            
            # Calcular calidad (0.0 a 1.0)
            quality = quality_score / max_quality
            
            # Unir todo el texto
            text = ' '.join(filter(None, parts))
            
            return text.upper(), quality, structured_data
            
        except Exception as e:
            ocr_logger.log_error(
                endpoint="InvoiceExtractor.extract_from_xml",
                error_message=str(e),
                error_type=type(e).__name__,
                traceback_info=traceback.format_exc()
            )
            return "", 0.0, {'proveedor': {}, 'factura': {}, 'cliente': {}}
    
    def extract_from_pdf(self, pdf_path: str) -> Tuple[str, Dict]:
        """
        Extrae texto del PDF, con fallback OCR si no hay texto seleccionable
        """
        if not os.path.exists(pdf_path):
            ocr_logger.log_error("InvoiceExtractor", f"Archivo PDF no encontrado: {pdf_path}")
            return "", {'proveedor': {}, 'factura': {}}

        try:
            text_parts = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Extraer texto normal
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)
                    
                    # Intentar extraer tablas (mejora la extracción de datos estructurados)
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            # Convertir tabla a texto
                            for row in table:
                                if row:
                                    row_text = ' '.join([str(cell) if cell else '' for cell in row])
                                    text_parts.append(row_text)
            
            # Combinar todo el texto
            full_text = '\n'.join(text_parts)
            
            # Limpiar texto (remover caracteres problemáticos pero mantener estructura)
            full_text = self._clean_pdf_text(full_text)
            

            # Fallback OCR si el texto es insuficiente
            if len(full_text.strip()) < 100:
                ocr_text = self._ocr_pdf(pdf_path)
                if ocr_text:
                    full_text = self._clean_pdf_text(ocr_text)
            
            ocr_logger.logger.info(f"PDF extraido: {len(full_text)} caracteres")

            
            # Extraer datos estructurados
            structured_data = self._extract_pdf_structured_data(full_text)
            valores = self._extract_pdf_values(full_text)
            if valores:
                structured_data['factura']['valores'] = valores
            
            return full_text.upper(), structured_data
            
        except Exception as e:
            ocr_logger.log_error(
                endpoint="InvoiceExtractor.extract_from_pdf",
                error_message=str(e),
                error_type=type(e).__name__,
                traceback_info=traceback.format_exc()
            )
            return "", {'proveedor': {}, 'factura': {}}
    
    def _clean_pdf_text(self, text: str) -> str:
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
    
    def _extract_pdf_structured_data(self, text: str) -> Dict:
        """
        Extrae datos estructurados del texto del PDF usando regex
        
        Args:
            text: Texto extraído del PDF
        
        Returns:
            Dict con datos estructurados
        """
        structured_data = {
            'proveedor': {},
            'factura': {}
        }
        
        # Buscar NIT del proveedor
        nit = self._extract_nit_from_text(text)
        if nit:
            structured_data['proveedor']['nit'] = nit
        
        # Buscar número de factura
        numero_factura = self._extract_numero_factura(text)
        if numero_factura:
            structured_data['factura']['numero'] = numero_factura
        
        # Buscar razón social del proveedor (generalmente al inicio)
        razon_social = self._extract_razon_social(text)
        if razon_social:
            structured_data['proveedor']['nombre'] = razon_social
            structured_data['proveedor']['razon_social'] = razon_social
        
        # Buscar orden de compra
        orden_compra = self._extract_orden_compra(text)
        if orden_compra:
            structured_data['factura']['orden_compra'] = orden_compra
        
        return structured_data
    
    def _ocr_pdf(self, pdf_path: str) -> str:
        try:
            from pdf2image import convert_from_path
            import pytesseract
            import cv2
            import numpy as np
        except Exception:
            return ""
        
        try:
            images = convert_from_path(pdf_path, dpi=300)
            ocr_text_parts = []
            for img in images:
                open_cv_image = np.array(img.convert('RGB'))[:, :, ::-1]
                gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
                gray = cv2.bilateralFilter(gray, 9, 75, 75)
                _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                ocr_text = pytesseract.image_to_string(thr, lang='spa')
                ocr_text_parts.append(ocr_text or "")
            return '\n'.join(ocr_text_parts)
        except Exception:
            return ""
    
    def _parse_money(self, s: str) -> Optional[float]:
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
    
    def _extract_amount_near(self, text: str, labels: list) -> Optional[float]:
        txt = text.upper()
        for label in labels:
            for m in re.finditer(label, txt):
                start = max(0, m.start() - 80)
                end = min(len(txt), m.end() + 80)
                ctx = txt[start:end]
                nums = re.findall(r'[$]?\s*[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?', ctx)
                if nums:
                    for n in reversed(nums):
                        val = self._parse_money(n)
                        if val is not None:
                            return val
        return None
    
    def _extract_pdf_values(self, text: str) -> Dict:
        valores = {}
        total_labels = [
            r'TOTAL\s+A\s+PAGAR', r'TOTAL\s+FACTURA', r'VALOR\s+TOTAL', r'TOTAL\s*:$', r'^TOTAL\s'
        ]
        subtotal_labels = [
            r'SUBTOTAL', r'VALOR\s+BRUTO', r'TOTAL\s+SIN\s+IMPUESTOS', r'BASE\s+IMPONIBLE'
        ]
        iva_labels = [
            r'IVA', r'IMPUESTO\s+AL\s+VALOR\s+AGREGADO', r'TAX'
        ]
        
        total = self._extract_amount_near(text, total_labels)
        if total is not None:
            valores['total'] = total
            valores['total_formatted'] = f"${total:,.2f}"
        
        subtotal = self._extract_amount_near(text, subtotal_labels)
        if subtotal is not None:
            valores['subtotal'] = subtotal
            valores['subtotal_formatted'] = f"${subtotal:,.2f}"
        
        iva = self._extract_amount_near(text, iva_labels)
        if iva is not None:
            valores['iva'] = iva
            valores['iva_formatted'] = f"${iva:,.2f}"
        
        if 'iva' not in valores and 'subtotal' in valores and 'total' in valores:
            iva_calc = valores['total'] - valores['subtotal']
            if iva_calc > 0:
                valores['iva'] = iva_calc
                valores['iva_formatted'] = f"${iva_calc:,.2f}"
        
        return valores
    
    def _extract_nit_from_text(self, text: str) -> Optional[str]:
        """
        Extrae el NIT del proveedor del texto
        Busca específicamente el NIT DEL EMISOR (proveedor), no del adquiriente
        """
        # PRIORIDAD 1: Buscar "NIT DEL EMISOR" explícitamente
        pattern_emisor = r'NIT\s+DEL\s+EMISOR[:\s]*(\d{3}[\.\s]?\d{3}[\.\s]?\d{3}|\d{9,10})\s*[-\s]*(\d)?'
        match = re.search(pattern_emisor, text, re.IGNORECASE)
        if match:
            nit_base = match.group(1)
            nit_limpio = self._limpiar_nit(nit_base)
            if len(nit_limpio) >= 9:
                return nit_limpio
        
        # PRIORIDAD 2: Buscar NIT cerca de "EMISOR" o "VENDEDOR" (primeros 2000 caracteres)
        texto_inicio = text[:2000]
        
        # Patrones para NIT del emisor
        patterns = [
            # NIT: 900.462.203 - 5 o NIT: 900.462.203-5
            r'NIT[:\s]*[:\.]?\s*(\d{3}[\.\s]?\d{3}[\.\s]?\d{3})\s*[-\s]*(\d)?',
            # Nit: 900462203-5
            r'Nit[:\s]*[:\.]?\s*(\d{9,10})\s*[-\s]*(\d)?',
            # N.I.T.: 900462203
            r'N\.?I\.?T\.?[:\s]*(\d{9,10})\s*[-\s]*(\d)?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto_inicio, re.IGNORECASE)
            if match:
                nit_base = match.group(1)
                # Limpiar el NIT
                nit_limpio = self._limpiar_nit(nit_base)
                if len(nit_limpio) >= 9:  # NIT válido tiene al menos 9 dígitos
                    return nit_limpio
        
        return None
    
    def _extract_numero_factura(self, text: str) -> Optional[str]:
        """
        Extrae el número de factura del texto del PDF.
        Busca diferentes formatos comunes en facturas colombianas.
        
        Formatos soportados:
        - FQE151179
        - 5808- 31443638 (con guión y espacio)
        - FEL-43853 (prefijo con guión)
        - FEPN-12345
        """
        # PRIORIDAD MÁXIMA: "NÚMERO DE FACTURA:" con captura hasta palabra en mayúsculas
        # Esto captura correctamente "FEL-43853" y "5808- 31443638" antes de "FORMA DE PAGO"
        pattern_numero_factura = r'N[ÚU]MERO\s+DE\s+FACTURA[:\s]+([A-Z0-9][-A-Z0-9\s]*?)(?=\s+[A-Z]{4,}|$)'
        match = re.search(pattern_numero_factura, text, re.IGNORECASE)
        if match:
            numero = match.group(1).strip()
            # Limpiar espacios múltiples internos pero mantener guiones y espacios únicos
            numero = re.sub(r'\s+', ' ', numero)
            numero = numero.upper()
            
            # Validar que sea un número de factura válido
            if self._is_valid_numero_factura(numero, text):
                return numero
        
        # Patrones ordenados por PRIORIDAD (más específicos primero)
        patterns = [
            # PRIORIDAD 2: Patrones con contexto de "FACTURA ELECTRÓNICA"
            (r'FACTURA\s+ELECTR[OÓ]NICA[^\n]*N[°º]\s*([A-Z0-9]{2,5}[-\s]?\d+(?:[-\s]\d+)?)', 2, 'FACTURA ELECTRONICA N°'),
            
            # PRIORIDAD 3: Patrones con "N°" o "No."
            (r'N[°º]\.?\s*(?:FACTURA[:\s]+)?([A-Z0-9]{2,5}[-\s]?\d+(?:[-\s]\d+)?)', 3, 'N°'),
            (r'No\.?\s*(?:FACTURA[:\s]+)?([A-Z0-9]{2,5}[-\s]?\d+(?:[-\s]\d+)?)', 4, 'No.'),
            
            # PRIORIDAD 4: Prefijos específicos con guión (FEL-43853, FEPN-12345)
            (r'\b([A-Z]{2,5}[-]\d+)\b', 5, 'Prefijo-Número'),
            
            # PRIORIDAD 5: Números con guión y espacio (5808- 31443638)
            (r'\b(\d{3,5}[-\s]+\d{5,})\b', 6, 'Número-Número'),
            
            # PRIORIDAD 6: Prefijos específicos de 3+ letras sin guión
            (r'\b(FEPN\d+)\b', 7, 'FEPN'),
            (r'\b(FQE\d+)\b', 8, 'FQE'),
            (r'\b(FVE\d+)\b', 9, 'FVE'),
            (r'\b(FEL\d+)\b', 10, 'FEL'),
            
            # PRIORIDAD 7: Prefijos de 2 letras (con lookbehind/lookahead)
            (r'(?<![A-Z])\b(FE\d+)\b(?![A-Z])', 11, 'FE'),
            (r'(?<![A-Z])\b(FV\d+)\b(?![A-Z])', 12, 'FV'),
            
            # PRIORIDAD 8: Nro. Doc. o Número Factura
            (r'Nro\.?\s*Doc\.?[:\s]*([A-Z0-9]{1,5}[-\s]?\d+(?:[-\s]\d+)?)', 13, 'Nro. Doc.'),
            
            # PRIORIDAD 9: Patrón genérico (último recurso)
            (r'\b([A-Z]{2,5}\d{4,})\b', 14, 'Genérico'),
        ]
        
        # Buscar con cada patrón y recolectar candidatos
        candidates = []
        
        for pattern, priority, name in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    numero = match.strip() if isinstance(match, str) else match[0].strip()
                    numero = numero.upper()
                    
                    # Validar que sea un número de factura válido
                    if self._is_valid_numero_factura(numero, text):
                        candidates.append({
                            'numero': numero,
                            'priority': priority,
                            'pattern': name,
                            'length': len(numero)
                        })
        
        if not candidates:
            return None
        
        # Ordenar candidatos por:
        # 1. Prioridad (menor es mejor)
        # 2. Longitud (más largo es mejor - más específico)
        candidates.sort(key=lambda x: (x['priority'], -x['length']))
        
        # Retornar el mejor candidato
        return candidates[0]['numero']
    
    def _is_valid_numero_factura(self, numero: str, text: str) -> bool:
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
            # Contar letras al inicio
            letras_inicio = 0
            for c in numero:
                if c.isalpha():
                    letras_inicio += 1
                else:
                    break
            
            # Debe tener al menos 2 letras de prefijo
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
                # Contexto: 150 caracteres antes y después
                contexto = text[max(0, pos-150):min(len(text), pos+len(numero)+150)].upper()
                
                # Palabras clave que indican que es una factura
                palabras_clave_factura = [
                    'FACTURA', 'ELECTRÓNICA', 'ELECTRONICA', 'VENTA', 
                    'N°', 'NO.', 'NRO', 'NÚMERO', 'NUMERO',
                    'INVOICE', 'BILL'
                ]
                
                # Palabras que indican que NO es una factura
                # NOTA: "ORDEN" y "PEDIDO" removidos porque "ORDEN DE PEDIDO" es un campo estándar en facturas colombianas
                palabras_clave_negativas = [
                    'REMISION', 'GUIA', 'COTIZACION',
                    'PRESUPUESTO', 'PROFORMA', 'RECIBO CAJA', 'COMPROBANTE EGRESO'
                ]
                
                tiene_contexto_factura = any(palabra in contexto for palabra in palabras_clave_factura)
                tiene_contexto_negativo = any(palabra in contexto for palabra in palabras_clave_negativas)
                
                # Si tiene contexto de factura y NO tiene contexto negativo, es válido
                if tiene_contexto_factura and not tiene_contexto_negativo:
                    return True
                
                # Si tiene contexto negativo, rechazar
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
    
    def _extract_razon_social(self, text: str) -> Optional[str]:
        """
        Extrae la razón social del proveedor.
        Generalmente está al inicio del documento o después de "Razón social".
        """
        lines = text.split('\n')
        
        # Buscar en las primeras líneas (el proveedor suele estar arriba)
        for i, line in enumerate(lines[:25]):
            line_original = line.strip()
            line = line_original.upper()
            
            # Patrón 1: "RAZÓN SOCIAL: XXXX" — limpiar el prefijo
            match = re.search(r'RAZ[OÓ]N\s*SOCIAL[:\s]+(.+)', line, re.IGNORECASE)
            if match:
                razon = match.group(1).strip()
                # Limpiar prefijos adicionales
                razon = re.sub(r'^(RAZÓN\s*SOCIAL[:\s]*)+', '', razon, flags=re.IGNORECASE).strip()
                # Verificar que no sea el CUFE (código largo hexadecimal)
                if len(razon) > 5 and not re.match(r'^[A-F0-9]{60,}$', razon):
                    return razon
            
            # Patrón 2: "NOMBRE COMERCIAL: XXXX"
            match = re.search(r'NOMBRE\s*COMERCIAL[:\s]+(.+)', line, re.IGNORECASE)
            if match:
                nombre = match.group(1).strip()
                if len(nombre) > 5 and not re.match(r'^[A-F0-9]{60,}$', nombre):
                    return nombre
            
            # Patrón 3: Línea que termina en S.A.S, LTDA, E.S.P., BIC, etc.
            if re.search(r'\b(S\.?A\.?S\.?|LTDA\.?|S\.?A\.?|E\.?S\.?P\.?|B\.?I\.?C\.?)\s*$', line, re.IGNORECASE):
                # Verificar que no sea el cliente (CLINICA MEDILASER)
                if 'MEDILASER' not in line and 'CLIENTE' not in line and 'ADQUIRIENTE' not in line:
                    # Limpiar prefijos comunes
                    razon = re.sub(r'^(RAZÓN\s*SOCIAL[:\s]*|NOMBRE[:\s]*)+', '', line_original, flags=re.IGNORECASE).strip()
                    # Verificar que no sea CUFE
                    if not re.match(r'^[A-F0-9]{60,}$', razon.upper()):
                        return razon
            
            # Patrón 4: Nombre de empresa en mayúsculas después de "DATOS DEL EMISOR"
            if i >= 2 and len(line) > 10 and line.isupper():
                # Verificar que parece un nombre de empresa
                if not any(x in line for x in ['FACTURA', 'NIT', 'FECHA', 'DIREC', 'CLIENTE', 'SEÑOR', 'DATOS', 'DOCUMENTO', 'CUFE', 'CÓDIGO']):
                    # Verificar que tiene al menos 3 letras consecutivas
                    if re.search(r'[A-Z]{3,}', line):
                        # Verificar que no es el CUFE (código hexadecimal largo)
                        if not re.match(r'^[A-F0-9]{60,}$', line):
                            # Limpiar prefijos
                            razon = re.sub(r'^(RAZÓN\s*SOCIAL[:\s]*|NOMBRE[:\s]*)+', '', line_original, flags=re.IGNORECASE).strip()
                            if len(razon) > 5 and 'MEDILASER' not in razon.upper():
                                return razon
        
        return None
    
    def _extract_orden_compra(self, text: str) -> Optional[str]:
        """
        Extrae el número de Orden de Compra del texto del PDF
        Maneja múltiples formatos y casos donde el número está dividido en líneas
        GENÉRICO: No asume ningún prefijo específico (MED, OC, etc.)
        
        Args:
            text: Texto extraído del PDF
        
        Returns:
            Número de orden de compra o None si no se encuentra
        """
        # Patrones ordenados de más específico a más general
        patterns = [
            # Patrón 1: "ORDEN DE COMPRA No. XXX-2026-139" (captura cualquier formato)
            (r'ORDEN\s+DE\s+COMPRA\s+No\.?\s*[:\s]*([A-Z0-9\-/]+)', 1),
            
            # Patrón 2: "Orden de Compra: XXX-2025-6327" (captura alfanumérico con guiones)
            (r'Orden\s+de\s+Compra[:\s]+([A-Z0-9\-/]+)', 2),
            
            # Patrón 3: "O.C: XXX" o "OC: XXX" (captura cualquier alfanumérico)
            (r'\bO\.?\s*C\.?\s*[:\s]+([A-Z0-9\-/]+)', 3),
            
            # Patrón 4: "Purchase Order: XXX" o "P.O: XXX"
            (r'(?:Purchase\s+Order|P\.?\s*O\.?)\s*[:\s]+([A-Z0-9\-/]+)', 4),
            
            # Patrón 5: "Pedido:" o "Pedido No:" (común en algunos proveedores)
            (r'Pedido\s*(?:No\.?|N[°º])?\s*[:\s]+([A-Z0-9\-/]+)', 5),
            
            # Patrón 6: "Ref:" o "Referencia:" seguido de número
            (r'(?:Ref|Referencia)[:\s]+([A-Z0-9\-/]+)', 6),
        ]
        
        # Intentar con patrones regex primero
        for pattern, patron_num in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Si el match es una tupla (grupos múltiples), unirlos
                if isinstance(matches[0], tuple):
                    orden = ''.join(matches[0])
                else:
                    orden = matches[0]
                
                # Limpiar el match (remover espacios extras y normalizar)
                orden = orden.strip()
                orden = re.sub(r'\s+', '', orden)  # Remover espacios
                orden = re.sub(r'-+', '-', orden)  # Normalizar guiones múltiples
                orden = re.sub(r'/+', '/', orden)  # Normalizar slashes múltiples
                
                # Validar que tenga un formato razonable
                if self._is_valid_orden_compra(orden):
                    return orden
        
        # Si no encontramos con patrones, buscar manualmente en el contexto
        # Esto maneja casos donde el número está dividido en múltiples líneas
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'orden de compra' in line.lower() or 'o.c' in line.lower() or 'oc:' in line.lower():
                # Buscar en esta línea y las siguientes 2
                context_lines = lines[i:min(i+3, len(lines))]
                context = ' '.join(context_lines)
                
                # Buscar patrón genérico: LETRAS-NÚMEROS o LETRAS/NÚMEROS
                # Ejemplos: MED-2025-6327, OC-12345, REF/2025/001, etc.
                match = re.search(r'([A-Z]{2,}[\-/\s]*\d{3,}[\-/\s]*\d*)', context, re.IGNORECASE)
                if match:
                    orden = match.group(1)
                    orden = re.sub(r'\s+', '', orden)
                    orden = re.sub(r'-+', '-', orden)
                    orden = re.sub(r'/+', '/', orden)
                    
                    if self._is_valid_orden_compra(orden):
                        return orden
                
                # Caso especial: buscar prefijo en una línea y número en la siguiente
                # Ejemplo: "Orden de Compra: ABC-" + "2025-6327"
                match_prefix = re.search(r'(?:Orden\s+de\s+Compra|O\.?C\.?)[:\s]+([A-Z]{2,}[\-/\s]*)', line, re.IGNORECASE)
                if match_prefix and i + 1 < len(lines):
                    # Buscar número en la siguiente línea
                    next_line = lines[i + 1]
                    match_number = re.search(r'^[\s]*(\d{3,}[\-/\s]*\d*)', next_line)
                    if match_number:
                        prefix = match_prefix.group(1).strip()
                        number = match_number.group(1).strip()
                        orden = prefix + number
                        orden = re.sub(r'\s+', '', orden)
                        orden = re.sub(r'-+', '-', orden)
                        orden = re.sub(r'/+', '/', orden)
                        
                        if self._is_valid_orden_compra(orden):
                            return orden
        
        return None
    
    def _is_valid_orden_compra(self, orden: str) -> bool:
        """
        Valida que una orden de compra tenga un formato razonable
        
        Args:
            orden: Número de orden de compra candidato
        
        Returns:
            True si parece válida, False si no
        """
        if not orden or len(orden) < 3:
            return False
        
        # Debe tener al menos una letra y un número
        has_letter = any(c.isalpha() for c in orden)
        has_digit = any(c.isdigit() for c in orden)
        
        if not (has_letter and has_digit):
            return False
        
        # No debe ser solo números (eso sería un ID genérico)
        if orden.replace('-', '').replace('/', '').isdigit():
            return False
        
        # No debe tener más de 50 caracteres (probablemente no es una orden)
        if len(orden) > 50:
            return False
        
        # Filtrar palabras comunes que no son órdenes de compra
        palabras_invalidas = ['FACTURA', 'TOTAL', 'SUBTOTAL', 'IVA', 'FECHA', 'VENCIMIENTO']
        if any(palabra in orden.upper() for palabra in palabras_invalidas):
            return False
        
        return True
    
    def _limpiar_nit(self, nit: str) -> str:
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
    
    def extract_combined(self, xml_path: str = None, pdf_path: str = None) -> Dict:
        """
        Extrae texto de XML y PDF combinados con pesos inteligentes
        
        Args:
            xml_path: Ruta al XML (opcional)
            pdf_path: Ruta al PDF (opcional)
            
        Returns:
            Dict con texto combinado, metadatos y datos estructurados
        """
        xml_text = ""
        pdf_text = ""
        xml_quality = 0.0
        xml_structured = {'proveedor': {}, 'factura': {}, 'cliente': {}}
        pdf_structured = {'proveedor': {}, 'factura': {}}
        
        # Extraer XML si existe
        if xml_path:
            xml_text, xml_quality, xml_structured = self.extract_from_xml(xml_path)
        
        # Extraer PDF si existe
        if pdf_path:
            pdf_text, pdf_structured = self.extract_from_pdf(pdf_path)
        
        # Calcular pesos dinámicos
        if xml_text and pdf_text:
            if xml_quality >= 0.8:
                xml_weight = 0.70
                pdf_weight = 0.30
            elif xml_quality >= 0.5:
                xml_weight = 0.60
                pdf_weight = 0.40
            else:
                xml_weight = 0.50
                pdf_weight = 0.50
        elif xml_text:
            xml_weight = 1.0
            pdf_weight = 0.0
        elif pdf_text:
            xml_weight = 0.0
            pdf_weight = 1.0
        else:
            xml_weight = 0.0
            pdf_weight = 0.0
        
        # Combinar textos
        combined_text = f"{xml_text} {pdf_text}".strip()
        
        # Combinar datos estructurados (priorizar XML, complementar con PDF)
        proveedor_data = self._merge_proveedor_data(
            xml_structured.get('proveedor', {}),
            pdf_structured.get('proveedor', {})
        )
        
        factura_data = self._merge_factura_data(
            xml_structured.get('factura', {}),
            pdf_structured.get('factura', {})
        )
        
        return {
            'text': combined_text,
            'xml_text': xml_text,
            'pdf_text': pdf_text,
            'xml_quality': xml_quality,
            'xml_weight': xml_weight,
            'pdf_weight': pdf_weight,
            'has_xml': bool(xml_text),
            'has_pdf': bool(pdf_text),
            # Datos estructurados
            'proveedor': proveedor_data,
            'factura': factura_data,
            'cliente': xml_structured.get('cliente', {})
        }
    
    def _merge_proveedor_data(self, xml_data: Dict, pdf_data: Dict) -> Dict:
        """
        Combina datos del proveedor de XML y PDF
        Prioriza XML, complementa con PDF
        """
        merged = {}
        
        # Campos a combinar
        fields = ['nombre', 'razon_social', 'nit', 'nit_original', 'direccion', 'ciudad', 'telefono', 'email']
        
        for field in fields:
            # Priorizar XML
            if xml_data.get(field):
                merged[field] = xml_data[field]
            elif pdf_data.get(field):
                merged[field] = pdf_data[field]
        
        return merged
    
    def _merge_factura_data(self, xml_data: Dict, pdf_data: Dict) -> Dict:
        """
        Combina datos de la factura de XML y PDF
        Prioriza XML, complementa con PDF
        """
        merged = {}
        
        # Campos simples
        fields = ['numero', 'fecha', 'cufe', 'orden_compra']
        
        for field in fields:
            if xml_data.get(field):
                merged[field] = xml_data[field]
            elif pdf_data.get(field):
                merged[field] = pdf_data[field]
        
        # Merging especial para valores (deep merge)
        xml_valores = xml_data.get('valores', {})
        pdf_valores = pdf_data.get('valores', {})
        
        if xml_valores or pdf_valores:
            # Empezar con PDF como base (tiene menos prioridad)
            merged_valores = pdf_valores.copy()
            
            # Actualizar con valores de XML (mayor prioridad)
            # Solo actualizar si el valor no es nulo/vacío
            for k, v in xml_valores.items():
                if v is not None:
                    merged_valores[k] = v
            
            merged['valores'] = self._sanitize_values(merged_valores)
            
        return merged
    
    def _sanitize_values(self, valores: Dict) -> Dict:
        """
        Sanea y valida los valores financieros para eliminar inconsistencias
        """
        if not valores:
            return valores
            
        total = valores.get('total', 0)
        subtotal = valores.get('subtotal', 0)
        iva = valores.get('iva', 0)
        
        # 1. Si total y subtotal son iguales (o casi), IVA debe ser 0
        # Esto corrige casos donde PDF detecta basura como IVA cuando no debería haber
        if total and subtotal and abs(total - subtotal) < 100.0:  # Margen de error de 100 pesos
            if iva > 0:
                valores['iva'] = 0.0
                valores['iva_formatted'] = "$0.00"
                iva = 0.0
            
        # 2. Si IVA es muy pequeño comparado con subtotal (posible porcentaje o basura)
        # O si es muy pequeño en absoluto (< 50 pesos) y subtotal es grande (> 10000)
        if iva > 0 and subtotal > 10000:
            if iva < 50:
                valores['iva'] = 0.0
                valores['iva_formatted'] = "$0.00"
        
        # 3. Recalcular formateados por consistencia
        for key in ['total', 'subtotal', 'iva', 'tax_exclusive', 'tax_inclusive', 'valor_neto']:
            if key in valores and isinstance(valores[key], (int, float)):
                valores[f'{key}_formatted'] = f"${valores[key]:,.2f}"
                
        return valores

    def _extract_text(self, root, xpaths: list) -> str:
        """Extrae texto del primer xpath que encuentre"""
        for xpath in xpaths:
            elem = root.find(xpath, self.NAMESPACES)
            if elem is not None and elem.text:
                return elem.text.strip()
        return ""
    
    def _extract_all_text(self, root, xpaths: list) -> list:
        """Extrae texto de todos los elementos que coincidan"""
        texts = []
        for xpath in xpaths:
            elems = root.findall(xpath, self.NAMESPACES)
            for elem in elems:
                if elem.text:
                    texts.append(elem.text.strip())
        return texts
    
    def _extract_embedded_invoice(self, root):
        """
        Extrae el Invoice embebido en el CDATA del AttachedDocument
        
        Args:
            root: Root del XML AttachedDocument
        
        Returns:
            Root del Invoice embebido o None si no existe
        """
        try:
            # Buscar el CDATA que contiene el Invoice
            description = root.find('.//cac:Attachment//cac:ExternalReference//cbc:Description', self.NAMESPACES)
            
            if description is not None and description.text:
                # El texto del CDATA contiene el XML del Invoice
                invoice_xml = description.text.strip()
                
                # Parsear el XML embebido
                invoice_root = ET.fromstring(invoice_xml)
                
                return invoice_root
        except Exception as e:
            # Si falla, retornar None para usar el root original
            ocr_logger.logger.debug(f"No se pudo extraer invoice embebido: {e}")
            pass
        
        return None
