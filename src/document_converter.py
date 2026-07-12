"""
Módulo de conversión universal de documentos PDF.

Funcionalidad:
- Lee cualquier PDF (nativo o escaneado)
- Extrae texto, tablas, imágenes
- Genera salida en Excel, Word, JSON o imagen

Independiente del módulo de facturas.
"""

import pdfplumber
import re
import os
import io
import tempfile
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Generación de archivos
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

try:
    from docx import Document as DocxDocument
    from docx.shared import Inches, Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import pytesseract
    from PIL import Image
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

try:
    import pypdfium2 as pdfium
    HAS_PDFIUM = True
except ImportError:
    HAS_PDFIUM = False

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from .logger import ocr_logger


class DocumentConverter:
    """
    Convertidor universal de documentos PDF.
    Lee cualquier PDF y genera Excel, Word, JSON o imagen.
    """

    def __init__(self, tesseract_path: str = None, poppler_path: str = None):
        """
        Args:
            tesseract_path: Ruta al ejecutable tesseract (None=auto-detectar)
            poppler_path: Ruta a la carpeta bin de Poppler (None=auto-detectar)
        """
        self.tesseract_path = tesseract_path
        self.poppler_path = poppler_path

        # Auto-detectar Tesseract
        if HAS_TESSERACT:
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            else:
                # Buscar en ubicaciones comunes
                common_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                    os.path.expanduser(r'~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'),
                    '/usr/bin/tesseract',
                    '/usr/local/bin/tesseract',
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        self.tesseract_path = path
                        break

        # Auto-detectar Poppler
        if not poppler_path:
            common_poppler = [
                r'C:\ProgramData\chocolatey\lib\poppler\tools',
                r'C:\poppler\bin',
                r'C:\poppler\Library\bin',
            ]
            for path in common_poppler:
                if os.path.exists(path):
                    self.poppler_path = path
                    break

    # ============================================
    # MÉTODO PRINCIPAL
    # ============================================

    def convert(self, pdf_path: str, output_format: str = 'excel',
                options: Dict = None) -> Dict:
        """
        Convierte un PDF al formato solicitado.

        Args:
            pdf_path: Ruta al archivo PDF
            output_format: 'excel', 'word', 'json', 'image'
            options: Opciones adicionales:
                - pages: lista de páginas a procesar (None=todas)
                - language: idioma para OCR ('spa', 'eng')
                - extract_tables: True/False (default True)
                - extract_images: True/False (default False)
                - table_strategy: 'auto', 'lines', 'text' (default 'auto')
                - password: contraseña del PDF si está protegido

        Returns:
            Dict con:
                - success: bool
                - output_path: ruta al archivo generado (para excel/word/image)
                - data: datos extraídos (para json)
                - metadata: info del procesamiento
                - password_required: True si el PDF necesita contraseña
        """
        if not os.path.exists(pdf_path):
            return {'success': False, 'error': f'Archivo no encontrado: {pdf_path}'}

        options = options or {}
        language = options.get('language', 'spa')
        pages_filter = options.get('pages', None)
        extract_tables = options.get('extract_tables', True)
        password = options.get('password', None)

        try:
            # 0. Verificar si el PDF está protegido con contraseña
            is_encrypted, can_open = self._check_pdf_encryption(pdf_path, password)

            if is_encrypted and not can_open:
                return {
                    'success': False,
                    'password_required': True,
                    'error': 'El PDF está protegido con contraseña. Envíe la contraseña en el campo "password".'
                }

            # 1. Detectar tipo de PDF y extraer contenido
            content = self._extract_content(pdf_path, language, pages_filter, extract_tables, password)

            if not content.get('pages'):
                return {'success': False, 'error': 'No se pudo extraer contenido del PDF'}

            # 2. Detectar si es un extracto bancario (usa parser especializado)
            if output_format == 'excel':
                banco = self._detectar_extracto_bancario(content)
                if banco:
                    output_path = self._generate_excel_extracto_bancario(
                        content, banco, pdf_path, options
                    )
                    return {
                        'success': True,
                        'output_path': output_path,
                        'metadata': {**content.get('metadata', {}), 'tipo_documento': 'extracto_bancario', 'banco': banco},
                        'pages_processed': len(content.get('pages', []))
                    }

            # 3. Generar salida según formato (genérico)
            if output_format == 'excel':
                output_path = self._generate_excel(content, pdf_path, options)
            elif output_format == 'word':
                output_path = self._generate_word(content, pdf_path, options)
            elif output_format == 'image':
                output_path = self._generate_images(pdf_path, pages_filter, options)
            elif output_format == 'json':
                return {
                    'success': True,
                    'data': content,
                    'metadata': content.get('metadata', {})
                }
            else:
                return {'success': False, 'error': f'Formato no soportado: {output_format}'}

            return {
                'success': True,
                'output_path': output_path,
                'metadata': content.get('metadata', {}),
                'pages_processed': len(content.get('pages', []))
            }

        except Exception as e:
            ocr_logger.log_error(
                endpoint="DocumentConverter.convert",
                error_message=str(e),
                error_type=type(e).__name__
            )
            return {'success': False, 'error': str(e)}

    # ============================================
    # EXTRACCIÓN DE CONTENIDO
    # ============================================

    def _extract_content(self, pdf_path: str, language: str,
                         pages_filter: List[int], extract_tables: bool,
                         password: str = None) -> Dict:
        """Extrae todo el contenido del PDF"""

        content = {
            'metadata': {
                'filename': os.path.basename(pdf_path),
                'total_pages': 0,
                'method': 'native',  # 'native' o 'ocr'
                'language': language,
                'encrypted': password is not None,
                'processed_at': datetime.now().isoformat()
            },
            'pages': []
        }

        open_kwargs = {}
        if password:
            open_kwargs['password'] = password

        with pdfplumber.open(pdf_path, **open_kwargs) as pdf:
            content['metadata']['total_pages'] = len(pdf.pages)

            pages_to_process = range(len(pdf.pages))
            if pages_filter:
                pages_to_process = [p - 1 for p in pages_filter if 0 < p <= len(pdf.pages)]

            for page_idx in pages_to_process:
                page = pdf.pages[page_idx]
                page_data = self._extract_page(page, page_idx + 1, extract_tables)

                # Si no se extrajo texto nativo, intentar OCR
                if not page_data['text'].strip() and HAS_TESSERACT and HAS_PDF2IMAGE:
                    page_data = self._extract_page_ocr(pdf_path, page_idx, language)
                    content['metadata']['method'] = 'ocr'

                content['pages'].append(page_data)

        return content

    def _check_pdf_encryption(self, pdf_path: str, password: str = None) -> Tuple[bool, bool]:
        """
        Verifica si un PDF está encriptado y si se puede abrir.

        Returns:
            Tuple[is_encrypted, can_open]:
                - is_encrypted: True si el PDF tiene algún tipo de protección
                - can_open: True si se puede abrir (sin password o con el password correcto)
        """
        # Primero intentar abrir sin password usando pypdfium2 (más claro con errores)
        if HAS_PDFIUM:
            try:
                pdf = pdfium.PdfDocument(pdf_path)
                pdf.close()
                return False, True  # No encriptado
            except Exception as e:
                if 'password' in str(e).lower() or 'Incorrect password' in str(e):
                    # Está encriptado
                    if password:
                        try:
                            pdf = pdfium.PdfDocument(pdf_path, password=password)
                            pdf.close()
                            return True, True  # Password correcto
                        except Exception:
                            return True, False  # Password incorrecto
                    return True, False  # Sin password
                # Otro error
                pass

        # Fallback con pdfplumber
        try:
            with pdfplumber.open(pdf_path) as pdf:
                _ = len(pdf.pages)
                return False, True
        except Exception:
            # Asumimos que está encriptado
            if password:
                try:
                    with pdfplumber.open(pdf_path, password=password) as pdf:
                        _ = len(pdf.pages)
                        return True, True
                except Exception:
                    return True, False
            return True, False

    def _extract_page(self, page, page_num: int, extract_tables: bool) -> Dict:
        """Extrae contenido de una página con pdfplumber (texto nativo)"""

        page_data = {
            'page_number': page_num,
            'text': '',
            'tables': [],
            'lines': []
        }

        # Extraer texto completo
        text = page.extract_text() or ''
        page_data['text'] = text
        page_data['lines'] = [line for line in text.split('\n') if line.strip()]

        # Extraer tablas con múltiples estrategias
        if extract_tables:
            tables = self._extract_tables_smart(page)
            page_data['tables'] = tables

        return page_data

    def _extract_tables_smart(self, page) -> List[Dict]:
        """Extrae tablas con estrategia inteligente: prueba varias configuraciones"""

        best_tables = []

        # Estrategia 1: Default (detección por líneas)
        try:
            raw_tables = page.extract_tables()
            if raw_tables:
                for i, table in enumerate(raw_tables):
                    cleaned = self._clean_table(table)
                    if cleaned:
                        best_tables.append(cleaned)
        except Exception:
            pass

        # Si las tablas tienen muy pocas columnas (mal detectadas), probar otra estrategia
        if best_tables and all(t['cols'] <= 2 for t in best_tables):
            try:
                alt_tables = page.extract_tables({
                    'vertical_strategy': 'lines_strict',
                    'horizontal_strategy': 'lines_strict'
                })
                if alt_tables:
                    alt_cleaned = []
                    for table in alt_tables:
                        cleaned = self._clean_table(table)
                        if cleaned and cleaned['cols'] > 2:
                            alt_cleaned.append(cleaned)
                    if alt_cleaned:
                        best_tables = alt_cleaned
            except Exception:
                pass

        return best_tables

    def _clean_table(self, table) -> Optional[Dict]:
        """Limpia una tabla: quita filas vacías, normaliza columnas"""
        if not table:
            return None

        cleaned = []
        for row in table:
            if not row:
                continue
            # Limpiar celdas
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append('')
                else:
                    # Limpiar saltos de línea y espacios extra
                    cleaned_row.append(str(cell).replace('\n', ' ').strip())

            # Solo incluir si tiene al menos un valor
            if any(c for c in cleaned_row):
                cleaned.append(cleaned_row)

        if not cleaned:
            return None

        # Calcular columnas máximas
        max_cols = max(len(r) for r in cleaned)

        # Normalizar: todas las filas con el mismo número de columnas
        for i in range(len(cleaned)):
            while len(cleaned[i]) < max_cols:
                cleaned[i].append('')

        return {
            'index': 0,
            'rows': len(cleaned),
            'cols': max_cols,
            'data': cleaned
        }

    def _extract_page_ocr(self, pdf_path: str, page_idx: int, language: str) -> Dict:
        """Extrae contenido usando OCR (para PDFs escaneados)"""

        page_data = {
            'page_number': page_idx + 1,
            'text': '',
            'tables': [],
            'lines': [],
            'method': 'ocr'
        }

        try:
            img = None

            # Opción 1: pypdfium2 (no necesita Poppler)
            if HAS_PDFIUM:
                pdf_doc = pdfium.PdfDocument(pdf_path)
                page = pdf_doc[page_idx]
                bitmap = page.render(scale=3)
                img = bitmap.to_pil()
                pdf_doc.close()

            # Opción 2: pdf2image + Poppler
            elif HAS_PDF2IMAGE:
                kwargs = {'first_page': page_idx + 1, 'last_page': page_idx + 1, 'dpi': 300}
                if self.poppler_path:
                    kwargs['poppler_path'] = self.poppler_path
                images = convert_from_path(pdf_path, **kwargs)
                if images:
                    img = images[0]

            if not img:
                page_data['error'] = 'No se pudo convertir la página a imagen'
                return page_data

            # Pre-procesamiento con OpenCV
            if HAS_OPENCV:
                img_array = np.array(img.convert('RGB'))
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                img = Image.fromarray(enhanced)

            # OCR con Tesseract
            text = pytesseract.image_to_string(img, lang=language)
            page_data['text'] = text
            page_data['lines'] = [line for line in text.split('\n') if line.strip()]

            # Detectar tablas en el texto OCR
            page_data['tables'] = self._detect_tables_from_text(text)

        except Exception as e:
            page_data['error'] = str(e)

        return page_data

    def _detect_tables_from_text(self, text: str) -> List[Dict]:
        """Detecta tablas en texto OCR usando heurísticas de alineación"""
        tables = []
        lines = text.split('\n')

        # Buscar bloques de líneas con separadores consistentes (espacios múltiples o tabs)
        current_table = []
        for line in lines:
            # Una línea es parte de una tabla si tiene 2+ campos separados por 2+ espacios
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) >= 2 and line.strip():
                current_table.append(parts)
            else:
                if len(current_table) >= 3:  # Mínimo 3 filas para ser tabla
                    tables.append({
                        'index': len(tables),
                        'rows': len(current_table),
                        'cols': max(len(r) for r in current_table),
                        'data': current_table
                    })
                current_table = []

        # Última tabla pendiente
        if len(current_table) >= 3:
            tables.append({
                'index': len(tables),
                'rows': len(current_table),
                'cols': max(len(r) for r in current_table),
                'data': current_table
            })

        return tables

    # ============================================
    # GENERACIÓN DE EXCEL
    # ============================================

    def _generate_excel(self, content: Dict, pdf_path: str, options: Dict) -> str:
        """Genera un archivo Excel con todo el contenido en UNA SOLA hoja"""

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Documento"

        # Estilos
        header_font = Font(name='Calibri', bold=True, size=11, color='FFFFFF')
        header_fill = PatternFill(start_color='2F5496', end_color='2F5496', fill_type='solid')
        title_font = Font(name='Calibri', bold=True, size=13, color='2F5496')
        section_font = Font(name='Calibri', bold=True, size=11, color='333333')
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )

        row = 1

        # Título del documento
        ws.cell(row=row, column=1, value=content['metadata']['filename']).font = title_font
        row += 2

        # Recorrer cada página
        for page in content['pages']:
            page_num = page['page_number']
            total_pages = content['metadata']['total_pages']

            # Separador de página si hay más de una
            if total_pages > 1:
                ws.cell(row=row, column=1, value=f"── Página {page_num} de {total_pages} ──")
                ws.cell(row=row, column=1).font = section_font
                row += 1

            # Si la página tiene tablas, volcarlas en la hoja
            if page.get('tables'):
                for table in page['tables']:
                    if not table.get('data'):
                        continue

                    data = table['data']
                    num_cols = max(len(r) for r in data) if data else 0

                    for r_idx, row_data in enumerate(data):
                        for c_idx in range(num_cols):
                            cell_value = row_data[c_idx] if c_idx < len(row_data) else ''
                            cell = ws.cell(row=row, column=c_idx + 1, value=cell_value)
                            cell.border = thin_border

                            # Primera fila de cada tabla como header
                            if r_idx == 0:
                                cell.font = header_font
                                cell.fill = header_fill
                                cell.alignment = Alignment(horizontal='center', wrap_text=True)

                        row += 1

                    # Espacio entre tablas
                    row += 1

            # Si no hay tablas, poner el texto línea por línea
            elif page.get('lines'):
                for line in page['lines']:
                    ws.cell(row=row, column=1, value=line)
                    row += 1
                row += 1

        # Auto-ajustar ancho de columnas
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_length + 3, 65)

        # Filtro en la primera tabla si existe
        has_tables = any(p.get('tables') for p in content['pages'])
        if has_tables:
            # Encontrar rango de la primera tabla para filtros
            first_table_start = 3 if content['metadata']['total_pages'] > 1 else 2
            for page in content['pages']:
                if page.get('tables') and page['tables'][0].get('data'):
                    first_table = page['tables'][0]
                    num_cols = max(len(r) for r in first_table['data'])
                    num_rows = len(first_table['data'])
                    end_col = openpyxl.utils.get_column_letter(num_cols)
                    ws.auto_filter.ref = f"A{first_table_start}:{end_col}{first_table_start + num_rows - 1}"
                    break

        # Guardar
        output_dir = options.get('output_dir', tempfile.gettempdir())
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.xlsx")
        wb.save(output_path)

        return output_path

    # ============================================
    # GENERACIÓN DE WORD
    # ============================================

    def _generate_word(self, content: Dict, pdf_path: str, options: Dict) -> str:
        """Genera un archivo Word con el contenido extraído"""

        if not HAS_DOCX:
            raise ImportError("python-docx no está instalado. Instalar: pip install python-docx")

        doc = DocxDocument()

        # Título
        doc.add_heading(content['metadata']['filename'], level=1)

        # Metadata
        p = doc.add_paragraph()
        p.add_run(f"Páginas: {content['metadata']['total_pages']} | "
                  f"Método: {content['metadata']['method']} | "
                  f"Procesado: {content['metadata']['processed_at']}")
        p.paragraph_format.space_after = Pt(12)

        for page in content['pages']:
            # Encabezado de página
            if content['metadata']['total_pages'] > 1:
                doc.add_heading(f"Página {page['page_number']}", level=2)

            # Tablas
            tables_written = False
            for table in page.get('tables', []):
                if not table.get('data'):
                    continue

                data = table['data']
                if not data:
                    continue

                # Calcular número máximo de columnas
                num_cols = max(len(r) for r in data)
                if num_cols == 0:
                    continue

                try:
                    t = doc.add_table(rows=len(data), cols=num_cols)
                    t.style = 'Table Grid'

                    for r_idx, row_data in enumerate(data):
                        for c_idx in range(num_cols):
                            cell_value = ''
                            if c_idx < len(row_data) and row_data[c_idx]:
                                cell_value = str(row_data[c_idx])
                            t.cell(r_idx, c_idx).text = cell_value

                    doc.add_paragraph()  # Espacio después de tabla
                    tables_written = True
                except Exception:
                    # Si falla la tabla, escribir como texto
                    for row_data in data:
                        line = '  |  '.join(str(c) if c else '' for c in row_data)
                        doc.add_paragraph(line)

            # Texto (solo si no se escribieron tablas, para evitar duplicados)
            if not tables_written and page.get('lines'):
                for line in page['lines']:
                    if line.strip():
                        doc.add_paragraph(line)

            # Salto de página entre páginas (excepto la última)
            if page['page_number'] < content['metadata']['total_pages']:
                doc.add_page_break()

        # Guardar
        output_dir = options.get('output_dir', tempfile.gettempdir())
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.docx")
        doc.save(output_path)

        return output_path

    # ============================================
    # GENERACIÓN DE IMÁGENES
    # ============================================

    def _generate_images(self, pdf_path: str, pages_filter: List[int],
                         options: Dict) -> str:
        """Genera imágenes PNG de las páginas del PDF"""

        if not HAS_PDF2IMAGE:
            raise ImportError("pdf2image no está instalado. Instalar: pip install pdf2image")

        dpi = options.get('dpi', 200)
        output_dir = options.get('output_dir', tempfile.gettempdir())
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]

        kwargs = {'dpi': dpi}
        if self.poppler_path:
            kwargs['poppler_path'] = self.poppler_path
        if pages_filter:
            kwargs['first_page'] = min(pages_filter)
            kwargs['last_page'] = max(pages_filter)

        images = convert_from_path(pdf_path, **kwargs)

        output_paths = []
        for i, img in enumerate(images, 1):
            img_path = os.path.join(output_dir, f"{base_name}_page_{i}.png")
            img.save(img_path, 'PNG')
            output_paths.append(img_path)

        # Si solo una página, retornar esa ruta; si varias, retornar directorio
        if len(output_paths) == 1:
            return output_paths[0]
        return output_dir

    # ============================================
    # EXTRACTO BANCARIO (parser especializado)
    # ============================================

    def _detectar_extracto_bancario(self, content: Dict) -> Optional[str]:
        """Detecta si el PDF es un extracto bancario. Retorna el nombre del banco o None."""
        # Unir texto de las primeras 2 páginas
        text = ''
        for page in content['pages'][:2]:
            text += page.get('text', '') + '\n'

        text_upper = text.upper()

        if 'BBVA' in text_upper or 'BBVACASH' in text_upper:
            return 'BBVA'
        elif 'OCCIDENTE' in text_upper and ('CUENTA CORRIENTE' in text_upper or 'EXTRACTO' in text_upper):
            return 'OCCIDENTE'
        elif ('ITAU' in text_upper or 'ITAÚ' in text_upper or 'úatI' in text) and 'CUENTA' in text_upper:
            return 'ITAU'
        elif 'BANCOLOMBIA' in text_upper and ('EXTRACTO' in text_upper or 'CUENTA' in text_upper):
            return 'BANCOLOMBIA'
        elif 'DAVIVIENDA' in text_upper and ('EXTRACTO' in text_upper or 'CUENTA' in text_upper):
            return 'DAVIVIENDA'

        return None

    def _generate_excel_extracto_bancario(self, content: Dict, banco: str,
                                           pdf_path: str, options: Dict) -> str:
        """Genera un Excel organizado para extractos bancarios con columnas separadas."""

        # Unir todo el texto
        all_text = '\n'.join(p.get('text', '') for p in content['pages'])

        # Extraer info del encabezado
        info = self._parse_encabezado_extracto(all_text, banco)

        # Extraer movimientos
        movimientos = self._parse_movimientos_extracto(all_text, banco)

        # Generar Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Movimientos"

        # Estilos
        header_font = Font(name='Calibri', bold=True, size=11, color='FFFFFF')
        header_fill = PatternFill(start_color='2F5496', end_color='2F5496', fill_type='solid')
        title_font = Font(name='Calibri', bold=True, size=13, color='2F5496')
        money_fmt = '#,##0.00'
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )
        cargo_fill = PatternFill(start_color='FFE6E6', end_color='FFE6E6', fill_type='solid')
        abono_fill = PatternFill(start_color='E6FFE6', end_color='E6FFE6', fill_type='solid')

        # Encabezado
        ws.cell(row=1, column=1, value=f"Extracto Bancario — {banco}").font = title_font
        ws.cell(row=2, column=1, value=f"Cuenta: {info.get('cuenta', '')}")
        ws.cell(row=2, column=3, value=f"Período: {info.get('periodo', '')}")
        ws.cell(row=3, column=1, value=f"Titular: {info.get('titular', '')}")
        ws.cell(row=3, column=3, value=f"Saldo Anterior: ${info.get('saldo_anterior', 0):,.2f}")
        ws.cell(row=3, column=5, value=f"Saldo Final: ${info.get('saldo_final', 0):,.2f}")

        # Headers de la tabla
        row = 5
        headers = ['Fecha', 'Descripción', 'Débito', 'Crédito', 'Saldo']
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border

        # Movimientos
        for mov in movimientos:
            row += 1
            ws.cell(row=row, column=1, value=mov['fecha']).border = thin_border
            ws.cell(row=row, column=2, value=mov['descripcion']).border = thin_border

            if mov['tipo'] == 'CARGO':
                c = ws.cell(row=row, column=3, value=mov['monto'])
                c.number_format = money_fmt
                c.border = thin_border
                ws.cell(row=row, column=4, value='').border = thin_border
                for col in range(1, 6):
                    ws.cell(row=row, column=col).fill = cargo_fill
            else:
                ws.cell(row=row, column=3, value='').border = thin_border
                c = ws.cell(row=row, column=4, value=mov['monto'])
                c.number_format = money_fmt
                c.border = thin_border
                for col in range(1, 6):
                    ws.cell(row=row, column=col).fill = abono_fill

            c = ws.cell(row=row, column=5, value=mov['saldo'])
            c.number_format = money_fmt
            c.border = thin_border

        # Totales
        row += 1
        ws.cell(row=row, column=2, value='TOTALES').font = Font(bold=True)
        total_deb = sum(m['monto'] for m in movimientos if m['tipo'] == 'CARGO')
        total_cre = sum(m['monto'] for m in movimientos if m['tipo'] == 'ABONO')
        ws.cell(row=row, column=3, value=total_deb).number_format = money_fmt
        ws.cell(row=row, column=3).font = Font(bold=True)
        ws.cell(row=row, column=4, value=total_cre).number_format = money_fmt
        ws.cell(row=row, column=4).font = Font(bold=True)

        # Anchos
        ws.column_dimensions['A'].width = 14
        ws.column_dimensions['B'].width = 55
        ws.column_dimensions['C'].width = 18
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 20

        # Filtros
        ws.auto_filter.ref = f"A5:E{row - 1}"

        # Guardar
        output_dir = options.get('output_dir', tempfile.gettempdir())
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.xlsx")
        wb.save(output_path)

        return output_path

    def _parse_encabezado_extracto(self, text: str, banco: str) -> Dict:
        """Extrae información del encabezado del extracto bancario."""
        info = {'banco': banco, 'titular': '', 'cuenta': '', 'periodo': '',
                'saldo_anterior': 0, 'saldo_final': 0}

        m = re.search(r'(CLINICA MEDILASER\s*\S*)', text)
        if m:
            info['titular'] = m.group(1).strip()

        if banco == 'BBVA':
            m = re.search(r'INSTITUCIONAL\s+\S+\s+(\d+)', text)
            if m:
                info['cuenta'] = m.group(1)
            m = re.search(r'PERÍODO DESDE:\s*([\d-]+)\s*HASTA:\s*([\d-]+)', text)
            if m:
                info['periodo'] = f"{m.group(1)} a {m.group(2)}"
            m = re.search(r'SALDO CIERRE MES ANTERIOR\s*([\d,.]+)', text)
            if m:
                info['saldo_anterior'] = float(m.group(1).replace(',', ''))
            m = re.search(r'SALDO FINAL\s*([\d,.]+)', text)
            if m:
                info['saldo_final'] = float(m.group(1).replace(',', ''))

        elif banco == 'ITAU':
            m = re.search(r'(\d{3}-\d{5}-\d)', text)
            if m:
                info['cuenta'] = m.group(1)
            m = re.search(r'(\d{2}/\d{2}/\d{4})\s*AL\s*(\d{2}/\d{2}/\d{4})', text)
            if m:
                info['periodo'] = f"{m.group(1)} a {m.group(2)}"
            m = re.search(r'Saldo al \d{2}/\d{2}/\d{4}\s*[.\s]*([\d,]+\.\d{2})', text)
            if m:
                info['saldo_anterior'] = float(m.group(1).replace(',', ''))
            m = re.search(r'Saldo Final\s*[.\s]*([\d,]+\.\d{2})', text)
            if m:
                info['saldo_final'] = float(m.group(1).replace(',', ''))

        elif banco == 'OCCIDENTE':
            m = re.search(r'CUENTA No\.\s*([\d-]+)', text)
            if m:
                info['cuenta'] = m.group(1)
            m = re.search(r'FECHA DE CORTE:\s*(\S+)', text)
            if m:
                info['periodo'] = f"Corte: {m.group(1)}"
            m = re.search(r'SALDO ANTERIOR\s*([\d,.]+)', text)
            if m:
                info['saldo_anterior'] = float(m.group(1).replace(',', ''))
            m = re.search(r'SALDO ACTUAL\s*([\d,.]+)', text)
            if m:
                info['saldo_final'] = float(m.group(1).replace(',', ''))

        return info

    def _parse_movimientos_extracto(self, text: str, banco: str) -> List[Dict]:
        """Parsea los movimientos del extracto según el banco."""
        movimientos = []

        if banco == 'BBVA':
            pattern = re.compile(
                r'(\d{5})\s+(\d{2}-\d{2}-\d{4})\s+(\d{2}-\d{2}-\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
            )
            for m in pattern.finditer(text):
                desc = m.group(4).strip()
                monto = float(m.group(5).replace(',', ''))
                saldo = float(m.group(6).replace(',', ''))
                tipo = "CARGO" if "CARGO" in desc.upper() or "REVERSO" in desc.upper() else "ABONO"
                movimientos.append({
                    'fecha': m.group(2), 'descripcion': desc,
                    'tipo': tipo, 'monto': monto, 'saldo': saldo
                })

        elif banco == 'ITAU':
            pattern = re.compile(
                r'^(\d{2})\s+\d+\s+(NC|ND|Impuesto|Intereses)\s*(.+?)\s+([\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})',
                re.MULTILINE
            )
            for m in pattern.finditer(text):
                dia = m.group(1)
                tipo_code = m.group(2).strip()
                desc = f"{tipo_code} {m.group(3).strip()}"
                monto = float(m.group(4).replace(',', ''))
                saldo = float(m.group(5).replace(',', ''))
                tipo = 'ABONO' if tipo_code == 'NC' else 'CARGO'
                movimientos.append({
                    'fecha': f"Día {dia}", 'descripcion': desc,
                    'tipo': tipo, 'monto': monto, 'saldo': saldo
                })

        elif banco == 'OCCIDENTE':
            pattern = re.compile(
                r'^(\d{2})\s+(.+?)\s+([A-Z]\d{5,7})\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)',
                re.MULTILINE
            )
            for m in pattern.finditer(text):
                dia = m.group(1)
                desc = f"{m.group(2).strip()} {m.group(3)}"
                debito = float(m.group(4).replace(',', ''))
                credito = float(m.group(5).replace(',', ''))
                saldo = float(m.group(6).replace(',', ''))
                tipo = 'CARGO' if debito > 0 else 'ABONO'
                monto = debito if debito > 0 else credito
                movimientos.append({
                    'fecha': f"Día {dia}", 'descripcion': desc,
                    'tipo': tipo, 'monto': monto, 'saldo': saldo
                })

        return movimientos

    # ============================================
    # INFO DE CAPACIDADES
    # ============================================

    def get_capabilities(self) -> Dict:
        """Retorna las capacidades disponibles del convertidor"""
        return {
            'native_pdf': True,  # Siempre disponible (pdfplumber)
            'scanned_pdf_ocr': HAS_TESSERACT and HAS_PDF2IMAGE,
            'output_excel': True,  # Siempre disponible (openpyxl)
            'output_word': HAS_DOCX,
            'output_json': True,
            'output_image': HAS_PDF2IMAGE,
            'image_preprocessing': HAS_OPENCV,
            'libraries': {
                'pdfplumber': True,
                'pytesseract': HAS_TESSERACT,
                'pdf2image': HAS_PDF2IMAGE,
                'opencv': HAS_OPENCV,
                'python-docx': HAS_DOCX,
                'openpyxl': True
            }
        }
