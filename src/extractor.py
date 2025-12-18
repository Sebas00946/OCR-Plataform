"""
Extractor de texto de XML y PDF
"""
import xml.etree.ElementTree as ET
import pdfplumber
from typing import Dict, Tuple


class InvoiceExtractor:
    """Extrae texto de facturas XML y PDF"""
    
    # Namespaces comunes en facturas electrónicas
    NAMESPACES = {
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
        'sts': 'dian:gov:co:facturaelectronica:Structures-2-1'
    }
    
    def extract_from_xml(self, xml_path: str) -> Tuple[str, float, Dict]:
        """
        Extrae texto del XML y calcula su calidad
        
        Returns:
            Tuple[str, float, Dict]: (texto_extraido, calidad_0_a_1, datos_estructurados)
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            parts = []
            quality_score = 0
            max_quality = 6  # Número de campos importantes
            
            # Diccionario para datos estructurados
            structured_data = {
                'proveedor': {}
            }
            
            # 1. Proveedor (peso: 1)
            supplier = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:PartyName//cbc:Name',
                './/cac:AccountingSupplierParty//cac:Party//cac:PartyLegalEntity//cbc:RegistrationName',
                './/cac:SenderParty//cbc:RegistrationName',
                './/cac:AccountingSupplierParty//cbc:RegistrationName'
            ])
            if supplier:
                parts.append(supplier)
                quality_score += 1
                structured_data['proveedor']['nombre'] = supplier
            
            # Extraer NIT del proveedor
            supplier_nit = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:PartyTaxScheme//cbc:CompanyID',
                './/cac:AccountingSupplierParty//cac:Party//cac:PartyIdentification//cbc:ID'
            ])
            if supplier_nit:
                # Limpiar NIT (remover guiones, espacios, etc.)
                supplier_nit_clean = supplier_nit.replace('-', '').replace('.', '').replace(' ', '').strip()
                structured_data['proveedor']['nit'] = supplier_nit_clean
                structured_data['proveedor']['nit_original'] = supplier_nit
            
            # Extraer dirección del proveedor
            supplier_address = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:PhysicalLocation//cac:Address//cbc:Line',
                './/cac:AccountingSupplierParty//cac:Party//cac:PostalAddress//cbc:Line'
            ])
            if supplier_address:
                structured_data['proveedor']['direccion'] = supplier_address
            
            # Extraer ciudad del proveedor
            supplier_city = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:PhysicalLocation//cac:Address//cbc:CityName',
                './/cac:AccountingSupplierParty//cac:Party//cac:PostalAddress//cbc:CityName'
            ])
            if supplier_city:
                structured_data['proveedor']['ciudad'] = supplier_city
            
            # Extraer teléfono del proveedor
            supplier_phone = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:Contact//cbc:Telephone'
            ])
            if supplier_phone:
                structured_data['proveedor']['telefono'] = supplier_phone
            
            # Extraer email del proveedor
            supplier_email = self._extract_text(root, [
                './/cac:AccountingSupplierParty//cac:Party//cac:Contact//cbc:ElectronicMail'
            ])
            if supplier_email:
                structured_data['proveedor']['email'] = supplier_email
            
            # 2. Cliente (peso: 1)
            customer = self._extract_text(root, [
                './/cac:ReceiverParty//cbc:RegistrationName',
                './/cac:AccountingCustomerParty//cbc:RegistrationName',
                './/cac:AccountingCustomerParty//cac:Party//cac:PartyName//cbc:Name'
            ])
            if customer:
                parts.append(customer)
                quality_score += 1
            
            # 3. Dirección de entrega (PESO ALTO - 3x para priorizar)
            # Esta es la información más importante para determinar la sucursal
            address = self._extract_text(root, [
                './/cac:Delivery//cac:DeliveryLocation//cac:Address//cbc:Line',
                './/cac:Delivery//cac:DeliveryAddress//cbc:Line',
                './/cac:AccountingCustomerParty//cac:Address//cbc:Line',
                './/cac:ReceiverParty//cac:Address//cbc:Line'
            ])
            if address:
                # Repetir 3 veces para dar más peso
                parts.append(address)
                parts.append(address)
                parts.append(address)
                quality_score += 1
            
            # 4. Ciudad de entrega (PESO ALTO - 3x para priorizar)
            city = self._extract_text(root, [
                './/cac:Delivery//cac:DeliveryLocation//cac:Address//cbc:CityName',
                './/cac:Delivery//cac:DeliveryAddress//cbc:CityName',
                './/cac:AccountingCustomerParty//cac:Address//cbc:CityName',
                './/cac:ReceiverParty//cac:Address//cbc:CityName'
            ])
            if city:
                # Repetir 3 veces para dar más peso
                parts.append(city)
                parts.append(city)
                parts.append(city)
                quality_score += 1
            
            # 5. Observaciones/Notas (peso: 1)
            notes = self._extract_all_text(root, ['.//cbc:Note', './/cbc:Description'])
            if notes:
                parts.extend(notes)
                quality_score += 1
            
            # 6. Items/Productos (peso: 1)
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
            return "", 0.0, {}
    
    def extract_from_pdf(self, pdf_path: str) -> str:
        """
        Extrae texto del PDF
        
        Returns:
            str: texto_extraido
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                return text.upper()
        except Exception as e:
            print(f"⚠️  Error al leer PDF: {e}")
            return ""
    
    def extract_combined(self, xml_path: str = None, pdf_path: str = None) -> Dict:
        """
        Extrae texto de XML y PDF combinados con pesos inteligentes
        
        Args:
            xml_path: Ruta al XML (opcional)
            pdf_path: Ruta al PDF (opcional)
            
        Returns:
            Dict con texto combinado y metadatos
        """
        xml_text = ""
        pdf_text = ""
        xml_quality = 0.0
        structured_data = {}
        
        # Extraer XML si existe
        if xml_path:
            xml_text, xml_quality, structured_data = self.extract_from_xml(xml_path)
        
        # Extraer PDF si existe
        if pdf_path:
            pdf_text = self.extract_from_pdf(pdf_path)
        
        # Calcular pesos dinámicos
        if xml_text and pdf_text:
            # Ambos disponibles: peso según calidad del XML
            if xml_quality >= 0.8:  # XML muy completo
                xml_weight = 0.70
                pdf_weight = 0.30
            elif xml_quality >= 0.5:  # XML moderado
                xml_weight = 0.60
                pdf_weight = 0.40
            else:  # XML pobre
                xml_weight = 0.50
                pdf_weight = 0.50
        elif xml_text:
            # Solo XML
            xml_weight = 1.0
            pdf_weight = 0.0
        elif pdf_text:
            # Solo PDF
            xml_weight = 0.0
            pdf_weight = 1.0
        else:
            # Ninguno (error)
            xml_weight = 0.0
            pdf_weight = 0.0
        
        # Combinar textos
        combined_text = f"{xml_text} {pdf_text}".strip()
        
        return {
            'text': combined_text,
            'xml_text': xml_text,
            'pdf_text': pdf_text,
            'xml_quality': xml_quality,
            'xml_weight': xml_weight,
            'pdf_weight': pdf_weight,
            'has_xml': bool(xml_text),
            'has_pdf': bool(pdf_text),
            'proveedor': structured_data  # Datos estructurados del proveedor
        }
    
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