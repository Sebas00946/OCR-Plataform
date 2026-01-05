"""
Extractor de texto de XML y PDF
Extrae datos estructurados de facturas electrónicas colombianas
"""
import xml.etree.ElementTree as ET
import pdfplumber
import re
from typing import Dict, Tuple, Optional


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
            r'(?:FACTURA|FE|FV|FVE|FEPN|No\.?|N[°º])[:\s]*([A-Z]*\s*\d+)',
            r'Nro\.?\s*Doc\.?[:\s]*([A-Z]?\d+)',
            r'(?:FACTURA ELECTR[OÓ]NICA)[^\d]*(\d+)',
            r'No\.\s*FE\s*(\d+)',
            r'No\.\s*FVE\s*(\d+)',
        ],
        # Razón social / Nombre del proveedor (al inicio del documento)
        'razon_social': [
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.]+(?:S\.?A\.?S\.?|LTDA\.?|S\.?A\.?))',
            r'Raz[oó]n\s*social/?Nombre[:\s]*([^\n]+)',
            r'Datos\s+del\s+Emisor[^\n]*\n[^\n]*Raz[oó]n\s*social/?Nombre[:\s]*([^\n]+)',
        ],
    }
    
    def extract_from_xml(self, xml_path: str) -> Tuple[str, float, Dict]:
        """
        Extrae texto del XML y datos estructurados del proveedor
        
        Returns:
            Tuple[str, float, Dict]: (texto_extraido, calidad_0_a_1, datos_estructurados)
        """
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
            
            # Calcular valor neto (total - retenciones)
            if 'total' in valores and 'total_retenciones' in valores:
                valor_neto = valores['total'] - valores['total_retenciones']
                valores['valor_neto'] = valor_neto
                valores['valor_neto_formatted'] = f"${valor_neto:,.2f}"
            
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
            print(f"⚠️  Error al leer XML: {e}")
            return "", 0.0, {'proveedor': {}, 'factura': {}, 'cliente': {}}
    
    def extract_from_pdf(self, pdf_path: str) -> Tuple[str, Dict]:
        """
        Extrae texto del PDF y datos estructurados
        
        Returns:
            Tuple[str, Dict]: (texto_extraido, datos_estructurados)
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
                
                # Extraer datos estructurados del texto
                structured_data = self._extract_pdf_structured_data(text)
                
                return text.upper(), structured_data
        except Exception as e:
            print(f"⚠️  Error al leer PDF: {e}")
            return "", {'proveedor': {}, 'factura': {}}
    
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
        
        return structured_data
    
    def _extract_nit_from_text(self, text: str) -> Optional[str]:
        """
        Extrae el NIT del proveedor del texto
        Busca el primer NIT que aparece (generalmente es del proveedor)
        """
        # Patrones para NIT
        patterns = [
            # NIT: 900.462.203 - 5 o NIT: 900.462.203-5
            r'NIT[:\s]*[:\.]?\s*(\d{3}[\.\s]?\d{3}[\.\s]?\d{3})\s*[-\s]*(\d)?',
            # Nit: 900462203-5
            r'Nit[:\s]*[:\.]?\s*(\d{9,10})\s*[-\s]*(\d)?',
            # N.I.T.: 900462203
            r'N\.?I\.?T\.?[:\s]*(\d{9,10})\s*[-\s]*(\d)?',
            # Solo número con formato 900.123.456
            r'(\d{3}\.\d{3}\.\d{3})\s*[-\s]*(\d)?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                nit_base = match.group(1)
                # Limpiar el NIT
                nit_limpio = self._limpiar_nit(nit_base)
                if len(nit_limpio) >= 9:  # NIT válido tiene al menos 9 dígitos
                    return nit_limpio
        
        return None
    
    def _extract_numero_factura(self, text: str) -> Optional[str]:
        """
        Extrae el número de factura del texto del PDF
        Busca diferentes formatos comunes en facturas colombianas
        """
        patterns = [
            # FEPN 1746 o FEPN1746
            r'FEPN\s*(\d+)',
            # FE 356 o FE356
            r'\bFE\s*(\d+)',
            # FVE 2473 o FVE2473
            r'FVE\s*(\d+)',
            # FV 123 o FV123
            r'\bFV\s*(\d+)',
            # No. FE 356
            r'No\.?\s*(?:FE|FV|FVE|FEPN)\s*(\d+)',
            # N° FVE 2473
            r'N[°º]\s*(?:FVE|FE|FV|FEPN)\s*(\d+)',
            # FACTURA ELECTRÓNICA DE VENTA ... No. 356
            r'FACTURA\s+ELECTR[OÓ]NICA[^\n]*No\.?\s*(\d+)',
            # Nro. Doc.: Z3872
            r'Nro\.?\s*Doc\.?[:\s]*([A-Z]?\d+)',
            # Número Factura: 123
            r'N[uú]mero\s*(?:de\s*)?Factura[:\s]*([A-Z]*\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                numero = match.group(1).strip()
                # Reconstruir con prefijo si es necesario
                if 'FEPN' in pattern:
                    return f"FEPN{numero}"
                elif 'FVE' in pattern:
                    return f"FVE{numero}"
                elif 'FE' in pattern and 'FVE' not in pattern:
                    return f"FE{numero}"
                elif 'FV' in pattern and 'FVE' not in pattern:
                    return f"FV{numero}"
                return numero
        
        return None
    
    def _extract_razon_social(self, text: str) -> Optional[str]:
        """
        Extrae la razón social del proveedor
        Generalmente está al inicio del documento o después de "Razón social"
        """
        lines = text.split('\n')
        
        # Buscar en las primeras líneas (el proveedor suele estar arriba)
        for i, line in enumerate(lines[:15]):
            line = line.strip()
            
            # Buscar patrón "Razón social/Nombre: XXXX"
            match = re.search(r'Raz[oó]n\s*social/?Nombre[:\s]*(.+)', line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            
            # Buscar línea que termine en S.A.S, LTDA, etc.
            if re.search(r'\b(S\.?A\.?S\.?|LTDA\.?|S\.?A\.?)\s*$', line, re.IGNORECASE):
                # Verificar que no sea el cliente (CLINICA MEDILASER)
                if 'MEDILASER' not in line.upper() and 'CLIENTE' not in line.upper():
                    return line
            
            # Buscar nombre de empresa en mayúsculas al inicio
            if i < 5 and len(line) > 10 and line.isupper():
                # Verificar que parece un nombre de empresa
                if not any(x in line for x in ['FACTURA', 'NIT', 'FECHA', 'DIREC', 'CLIENTE', 'SEÑOR']):
                    # Podría ser el nombre del proveedor
                    if re.search(r'[A-Z]{3,}', line):
                        return line
        
        return None
    
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
        
        # Campos a combinar
        fields = ['numero', 'fecha', 'cufe', 'valores']
        
        for field in fields:
            if xml_data.get(field):
                merged[field] = xml_data[field]
            elif pdf_data.get(field):
                merged[field] = pdf_data[field]
        
        return merged
    
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
            pass
        
        return None