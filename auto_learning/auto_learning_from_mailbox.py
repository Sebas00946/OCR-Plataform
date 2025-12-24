"""
Script de auto-aprendizaje masivo desde buzón compartido
Procesa correos del 2025 carpeta por carpeta para entrenar el OCR
"""
import os
import sys
import json
import requests
import tempfile
import base64
import zipfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from extractor import InvoiceExtractor
from classifier import PDFClassifier
from learning import LearningSystem

load_dotenv()

# Configuración
TENANT_ID = os.getenv('AZURE_TENANT_ID')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
SHARED_MAILBOX = os.getenv('SHARED_MAILBOX_EMAIL', 'recepcionfe@medilaser.com.co')

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

# Configuración de procesamiento
BATCH_SIZE = 100  # Procesar de 100 en 100 (aumentado de 50)
MAX_WORKERS = 10  # Número de threads paralelos
PROGRESS_FILE = "auto_learning_progress.json"
RESULTS_FILE = "auto_learning_results.json"
LOG_FILE = "auto_learning.log"

# Mapeo de carpetas a clasificación correcta
# IMPORTANTE: IDs validados contra las tablas sucursales y unidades_funcionales
# Nombres verificados contra el buzón real
FOLDER_MAPPING = {
    # NEIVA (Sucursal ID 4)
    "1. NEIVA/1.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 4, "unidad_id": 11},  # Neiva - Administración
    "1. NEIVA/1.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 4, "unidad_id": 5},   # Neiva - Almacén
    "1. NEIVA/1.3. GASTOS": {"sucursal_id": 4, "unidad_id": 11},                    # Neiva - Administración
    
    # TUNJA (Sucursal ID 5)
    "2. TUNJA/2.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 5, "unidad_id": 13}, # Tunja - Administración
    "2. TUNJA/2.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 5, "unidad_id": 9},   # Tunja - Almacén
    "2. TUNJA/2.3. GASTOS": {"sucursal_id": 5, "unidad_id": 13},                    # Tunja - Administración
    
    # FLORENCIA (Sucursal ID 3) - NOTA: Sin espacio después del número
    "3.FLORENCIA/3.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 3, "unidad_id": 12}, # Florencia - Administración
    "3.FLORENCIA/3.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 3, "unidad_id": 8},   # Florencia - Almacén
    "3.FLORENCIA/3.3. GASTOS": {"sucursal_id": 3, "unidad_id": 12},                    # Florencia - Administración
    
    # PITALITO (Sucursal ID 7) - Solo tiene Almacén
    "4. PITALITO/4.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 7, "unidad_id": 15}, # Pitalito - Almacén
    "4. PITALITO/4.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 7, "unidad_id": 15},  # Pitalito - Almacén
    "4. PITALITO/4.3. GASTOS": {"sucursal_id": 7, "unidad_id": 15},                    # Pitalito - Almacén
    
    # BOGOTA (Sucursal ID 2 - Facatativa)
    "5. BOGOTA/5.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 2, "unidad_id": 14}, # Facatativa - Administración
    "5. BOGOTA/5.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 2, "unidad_id": 2},   # Facatativa - Almacén
    "5. BOGOTA/5.3. GASTOS": {"sucursal_id": 2, "unidad_id": 14},                    # Facatativa - Administración
    
    # FACATATIVA (Sucursal ID 2) - Carpeta adicional encontrada
    "6. FACATATIVA/6.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 2, "unidad_id": 14}, # Facatativa - Administración
    "6. FACATATIVA/6.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 2, "unidad_id": 2},   # Facatativa - Almacén
    "6. FACATATIVA/6.3 GASTOS": {"sucursal_id": 2, "unidad_id": 14},                     # Facatativa - Administración (sin punto)
    
    # DUITAMA (Sucursal ID 1 - Nacional, o crear nueva?) - Carpeta adicional encontrada
    # NOTA: Duitama no tiene sucursal propia, usando Nacional temporalmente
    "7. DUITAMA/7.1. PROVEEDORES MÉDICOS E IPS": {"sucursal_id": 1, "unidad_id": 11},  # Nacional - Administración (temporal)
    "7. DUITAMA/7.3. GASTOS": {"sucursal_id": 1, "unidad_id": 11},                     # Nacional - Administración (temporal)
}


class AutoLearningProcessor:
    """Procesador de auto-aprendizaje desde buzón"""
    
    def __init__(self):
        self.access_token = None
        self.extractor = InvoiceExtractor()
        
        # Configuración de BD para el clasificador
        db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        self.classifier = PDFClassifier(db_config)
        self.learning = LearningSystem(db_config)
        self.progress = self.load_progress()
        self.results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'by_folder': {},
            'start_time': datetime.now().isoformat(),
            'errors': []
        }
        
        # Locks para thread-safety
        self.results_lock = threading.Lock()
        self.log_lock = threading.Lock()
        
        # Inicializar archivo de log
        self.log_file = open(LOG_FILE, 'a', encoding='utf-8')
        self.log(f"\n{'='*80}")
        self.log(f"INICIO DE SESIÓN: {datetime.now().isoformat()}")
        self.log(f"Configuración: {MAX_WORKERS} workers paralelos, lotes de {BATCH_SIZE}")
        self.log(f"{'='*80}")
    
    def log(self, message):
        """Escribe en el archivo de log (thread-safe)"""
        try:
            with self.log_lock:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log_file.write(f"[{timestamp}] {message}\n")
                self.log_file.flush()
        except:
            pass
    
    def __del__(self):
        """Cierra el archivo de log al terminar"""
        try:
            if hasattr(self, 'log_file'):
                self.log("FIN DE SESIÓN")
                self.log_file.close()
        except:
            pass
    
    def get_access_token(self):
        """Obtiene token de acceso"""
        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'scope': 'https://graph.microsoft.com/.default'
            }
            
            response = requests.post(TOKEN_URL, data=data)
            if response.status_code == 200:
                self.access_token = response.json()['access_token']
                self.token_time = datetime.now()
                self.log("Token de acceso obtenido exitosamente")
                return True
            else:
                self.log(f"Error obteniendo token: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log(f"Excepción obteniendo token: {e}")
            return False
    
    def ensure_valid_token(self):
        """Asegura que el token sea válido, renovándolo si es necesario"""
        # Los tokens de Azure expiran en 1 hora, renovar cada 50 minutos
        if not hasattr(self, 'token_time') or not self.access_token:
            return self.get_access_token()
        
        elapsed = (datetime.now() - self.token_time).total_seconds() / 60
        if elapsed > 50:
            self.log("Token próximo a expirar, renovando...")
            return self.get_access_token()
        
        return True
    
    def load_progress(self):
        """Carga progreso guardado"""
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        return {'processed_folders': {}, 'last_folder': None}
    
    def save_progress(self):
        """Guarda progreso"""
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def save_results(self):
        """Guarda resultados"""
        self.results['end_time'] = datetime.now().isoformat()
        with open(RESULTS_FILE, 'w') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
    
    def get_folder_id(self, folder_path):
        """Obtiene ID de carpeta por su ruta (desde SUCURSALES)"""
        # Asegurar token válido
        if not self.ensure_valid_token():
            self.log("ERROR: No se pudo obtener token válido")
            return None
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Primero obtener carpeta SUCURSALES
            url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders?$top=500"
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                self.log(f"Error obteniendo carpetas raíz: {response.status_code} - {response.text}")
                return None
            
            folders = response.json().get('value', [])
            sucursales_folder = None
            
            for folder in folders:
                if 'SUCURSALES' in folder['displayName'].upper():
                    sucursales_folder = folder['id']
                    self.log(f"Carpeta SUCURSALES encontrada: {folder['displayName']}")
                    break
            
            if not sucursales_folder:
                self.log("ERROR: No se encontró carpeta SUCURSALES")
                return None
            
            # Navegar por la ruta desde SUCURSALES
            parts = folder_path.split('/')
            current_id = sucursales_folder
            
            for i, part in enumerate(parts):
                self.log(f"Buscando subcarpeta nivel {i+1}: {part}")
                url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders/{current_id}/childFolders?$top=500"
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code != 200:
                    self.log(f"Error obteniendo subcarpetas nivel {i+1}: {response.status_code} - {response.text}")
                    return None
                
                folders = response.json().get('value', [])
                found = False
                
                # Buscar la carpeta (comparación flexible)
                for folder in folders:
                    folder_name = folder['displayName']
                    # Comparar ignorando espacios extras y mayúsculas/minúsculas
                    if folder_name.strip().upper() == part.strip().upper():
                        current_id = folder['id']
                        found = True
                        self.log(f"  ✓ Encontrada: {folder_name}")
                        break
                
                if not found:
                    self.log(f"  ✗ No encontrada: {part}")
                    self.log(f"  Carpetas disponibles: {[f['displayName'] for f in folders[:10]]}")
                    return None
            
            self.log(f"✅ Carpeta completa encontrada: {folder_path}")
            return current_id
            
        except requests.exceptions.Timeout:
            self.log(f"ERROR: Timeout buscando carpeta {folder_path}")
            return None
        except Exception as e:
            self.log(f"ERROR: Excepción buscando carpeta {folder_path}: {e}")
            return None
    
    def get_emails_from_folder(self, folder_id, start_date="2025-01-01"):
        """Obtiene correos de una carpeta desde una fecha"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        filter_query = f"receivedDateTime ge {start_date}T00:00:00Z and receivedDateTime le {end_date}T23:59:59Z and hasAttachments eq true"
        
        url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders/{folder_id}/messages"
        url += f"?$filter={filter_query}&$select=id,subject,receivedDateTime,hasAttachments&$top=999"
        
        all_emails = []
        
        try:
            while url:
                response = requests.get(url, headers=headers)
                
                if response.status_code != 200:
                    break
                
                data = response.json()
                all_emails.extend(data.get('value', []))
                url = data.get('@odata.nextLink')
        except Exception as e:
            print(f"   ⚠️  Error obteniendo correos: {e}")
        
        return all_emails
    
    def get_all_subfolders_recursive(self, parent_folder_id, max_depth=10, current_depth=0):
        """Obtiene todas las subcarpetas recursivamente"""
        if current_depth >= max_depth:
            return []
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders/{parent_folder_id}/childFolders"
        url += "?$select=id,displayName,totalItemCount,childFolderCount&$top=500"
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                return []
            
            folders = response.json().get('value', [])
            all_folders = []
            
            for folder in folders:
                folder_info = {
                    'id': folder['id'],
                    'name': folder['displayName'],
                    'total_items': folder.get('totalItemCount', 0),
                    'child_count': folder.get('childFolderCount', 0)
                }
                
                all_folders.append(folder_info)
                
                # Si tiene subcarpetas, obtenerlas recursivamente
                if folder.get('childFolderCount', 0) > 0:
                    subfolders = self.get_all_subfolders_recursive(
                        folder['id'],
                        max_depth,
                        current_depth + 1
                    )
                    all_folders.extend(subfolders)
            
            return all_folders
            
        except Exception as e:
            print(f"⚠️  Error obteniendo subcarpetas: {e}")
            return []
    
    def get_emails_from_folder_and_subfolders(self, folder_id, start_date="2025-01-01"):
        """Obtiene correos de una carpeta Y todas sus subcarpetas"""
        all_emails = []
        emails_by_subfolder = {}  # Para tracking
        
        # Obtener correos de la carpeta actual
        try:
            emails = self.get_emails_from_folder(folder_id, start_date)
            if emails:
                all_emails.extend(emails)
                emails_by_subfolder['[Carpeta Principal]'] = len(emails)
                print(f"   📧 Carpeta principal: {len(emails)} correos")
        except Exception as e:
            print(f"⚠️  Error obteniendo correos de carpeta principal: {e}")
        
        # Obtener todas las subcarpetas
        try:
            subfolders = self.get_all_subfolders_recursive(folder_id)
            
            if subfolders:
                print(f"   📂 Encontradas {len(subfolders)} subcarpetas (proveedores)")
                print(f"   🔍 Obteniendo correos de cada proveedor...")
                
                for idx, subfolder in enumerate(subfolders, 1):
                    try:
                        subfolder_name = subfolder['name']
                        print(f"      [{idx}/{len(subfolders)}] 📁 {subfolder_name}...", end=" ")
                        
                        subfolder_emails = self.get_emails_from_folder(subfolder['id'], start_date)
                        email_count = len(subfolder_emails) if subfolder_emails else 0
                        
                        if subfolder_emails:
                            all_emails.extend(subfolder_emails)
                            emails_by_subfolder[subfolder_name] = email_count
                            print(f"✅ {email_count} correos")
                        else:
                            print(f"⏭️  0 correos")
                            
                    except Exception as e:
                        print(f"❌ Error: {e}")
                        continue
                
                # Resumen de subcarpetas con más correos
                if emails_by_subfolder:
                    print(f"\n   📊 Top 5 proveedores con más correos:")
                    sorted_folders = sorted(emails_by_subfolder.items(), key=lambda x: x[1], reverse=True)
                    for folder_name, count in sorted_folders[:5]:
                        print(f"      • {folder_name}: {count} correos")
                    print()
                    
        except Exception as e:
            print(f"⚠️  Error obteniendo subcarpetas: {e}")
        
        return all_emails
    
    def get_attachments(self, message_id):
        """Obtiene adjuntos de un correo"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/messages/{message_id}/attachments"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return []
        
        return response.json().get('value', [])
    
    def check_if_processed(self, cufe):
        """Verifica si una factura ya fue procesada (por CUFE)"""
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            )
            
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM historial_clasificaciones WHERE cufe = %s LIMIT 1",
                    (cufe,)
                )
                result = cur.fetchone()
            
            conn.close()
            return result is not None
            
        except Exception as e:
            # Si hay error en BD, asumir que no está procesado
            return False
    
    def process_email(self, email, correct_classification, folder_name):
        """Procesa un correo individual con manejo robusto de errores"""
        xml_path = None
        pdf_path = None
        temp_files = []  # Lista para limpiar todos los archivos temporales
        email_subject = email.get('subject', 'Sin asunto')
        
        try:
            # Obtener adjuntos
            try:
                attachments = self.get_attachments(email['id'])
            except Exception as e:
                error_msg = f'Error obteniendo adjuntos: {str(e)}'
                self.log(f"ERROR en '{email_subject}': {error_msg}")
                return {'status': 'error', 'error': error_msg}
            
            xml_content = None
            pdf_content = None
            
            # Buscar ZIP, XML y PDF
            try:
                for att in attachments:
                    name = att.get('name', '').lower()
                    content_bytes = att.get('contentBytes')
                    
                    if not content_bytes:
                        continue
                    
                    # Si es un ZIP, extraer su contenido
                    if name.endswith('.zip'):
                        try:
                            import zipfile
                            import io
                            
                            self.log(f"Extrayendo ZIP: {name}")
                            zip_data = base64.b64decode(content_bytes)
                            zip_file = zipfile.ZipFile(io.BytesIO(zip_data))
                            
                            # Buscar XML y PDF dentro del ZIP
                            for zip_info in zip_file.namelist():
                                zip_name = zip_info.lower()
                                
                                if zip_name.endswith('.xml') and not xml_content:
                                    xml_content = zip_file.read(zip_info)
                                    self.log(f"  ✓ XML encontrado: {zip_info}")
                                elif zip_name.endswith('.pdf') and not pdf_content:
                                    pdf_content = zip_file.read(zip_info)
                                    self.log(f"  ✓ PDF encontrado: {zip_info}")
                            
                            zip_file.close()
                        except Exception as e:
                            self.log(f"Error extrayendo ZIP '{name}': {e}")
                            continue
                    
                    # Si es XML directo
                    elif name.endswith('.xml') and not xml_content:
                        xml_content = base64.b64decode(content_bytes)
                    
                    # Si es PDF directo
                    elif name.endswith('.pdf') and not pdf_content:
                        pdf_content = base64.b64decode(content_bytes)
                    
                    # Si ya tenemos ambos, no seguir buscando
                    if xml_content and pdf_content:
                        break
                        
            except Exception as e:
                return {'status': 'error', 'error': f'Error procesando adjuntos: {str(e)}'}
            
            # Si no hay XML o PDF, saltar
            if not xml_content and not pdf_content:
                self.log(f"SKIP en '{email_subject}': No tiene XML ni PDF")
                return {'status': 'skipped', 'reason': 'no_xml_pdf'}
            
            # Guardar temporalmente
            try:
                if xml_content:
                    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as xml_file:
                        xml_file.write(xml_content)
                        xml_path = xml_file.name
                        temp_files.append(xml_path)
                
                if pdf_content:
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
                        pdf_file.write(pdf_content)
                        pdf_path = pdf_file.name
                        temp_files.append(pdf_path)
            except Exception as e:
                return {'status': 'error', 'error': f'Error guardando archivos temporales: {str(e)}'}
            
            # Extraer datos primero para obtener CUFE
            try:
                if xml_path:
                    _, _, xml_data = self.extractor.extract_from_xml(xml_path)
                    cufe = xml_data.get('factura', {}).get('cufe')
                    
                    # Verificar si ya fue procesado
                    if cufe and self.check_if_processed(cufe):
                        return {'status': 'skipped', 'reason': 'already_processed', 'cufe': cufe}
            except Exception as e:
                # Si falla la extracción de CUFE, continuar de todos modos
                self.log(f"Error extrayendo CUFE: {e}")
                pass
            
            # Extraer texto combinado
            try:
                result = self.extractor.extract_combined(
                    xml_path=xml_path,
                    pdf_path=pdf_path
                )
                extracted_text = result['text']
            except Exception as e:
                error_msg = f'Error extrayendo texto: {str(e)}'
                self.log(f"ERROR en '{email_subject}': {error_msg}")
                return {'status': 'error', 'error': error_msg}
            
            # Clasificar
            try:
                sucursal_result, unidad_result = self.classifier.classify(extracted_text)
                
                classification = {
                    'sucursal': sucursal_result,
                    'unidad_funcional': unidad_result
                }
            except Exception as e:
                error_msg = f'Error clasificando: {str(e)}'
                self.log(f"ERROR en '{email_subject}': {error_msg}")
                return {'status': 'error', 'error': error_msg}
            
            # Verificar si la clasificación es correcta
            sucursal_correct = classification['sucursal']['id'] == correct_classification['sucursal_id']
            unidad_correct = classification['unidad_funcional']['id'] == correct_classification['unidad_id']
            
            # Aplicar auto-aprendizaje
            try:
                if sucursal_correct and unidad_correct:
                    # Reforzar keywords correctas
                    self.learning.reinforce_correct_classification(
                        extracted_text,
                        correct_classification['sucursal_id'],
                        correct_classification['unidad_id']
                    )
                    result_status = 'correct'
                else:
                    # IMPORTANTE: Aprender de la clasificación incorrecta
                    # Agregar keywords del texto a la clasificación correcta
                    self.learning.reinforce_correct_classification(
                        extracted_text,
                        correct_classification['sucursal_id'],
                        correct_classification['unidad_id']
                    )
                    result_status = 'incorrect'
                    
                    # Log para debug
                    self.log(f"Aprendiendo de error - Clasificó: S{classification['sucursal']['id']}/U{classification['unidad_funcional']['id']}, Correcto: S{correct_classification['sucursal_id']}/U{correct_classification['unidad_id']}")
            except Exception as e:
                # Si falla el aprendizaje, al menos registrar el resultado
                result_status = 'correct' if (sucursal_correct and unidad_correct) else 'incorrect'
                self.log(f"Error en aprendizaje: {e}")
            
            return {
                'status': result_status,
                'classified_sucursal': classification['sucursal']['id'],
                'classified_unidad': classification['unidad_funcional']['id'],
                'correct_sucursal': correct_classification['sucursal_id'],
                'correct_unidad': correct_classification['unidad_id']
            }
            
        except Exception as e:
            # Capturar cualquier error no manejado
            error_msg = f'Error general: {str(e)}'
            self.log(f"ERROR CRÍTICO en '{email_subject}': {error_msg}")
            return {'status': 'error', 'error': error_msg}
        
        finally:
            # SIEMPRE limpiar TODOS los archivos temporales
            for temp_file in temp_files:
                try:
                    if temp_file and os.path.exists(temp_file):
                        os.unlink(temp_file)
                except:
                    pass
    
    def process_folder(self, folder_path, correct_classification):
        """Procesa una carpeta completa"""
        print(f"\n{'='*80}")
        print(f"📁 PROCESANDO: {folder_path}")
        print(f"{'='*80}")
        self.log(f"\n{'='*80}")
        self.log(f"PROCESANDO CARPETA: {folder_path}")
        self.log(f"Clasificación correcta: Sucursal={correct_classification['sucursal_id']}, Unidad={correct_classification['unidad_id']}")
        self.log(f"{'='*80}")
        
        # Verificar si ya se procesó
        if folder_path in self.progress['processed_folders']:
            processed_count = self.progress['processed_folders'][folder_path]
            print(f"⚠️  Carpeta ya procesada anteriormente ({processed_count} correos)")
            print(f"   Saltando carpeta...")
            self.log(f"Carpeta ya procesada: {processed_count} correos - SALTANDO")
            return
        
        # Obtener ID de carpeta
        print(f"🔍 Buscando carpeta...")
        self.log("Buscando ID de carpeta...")
        
        try:
            folder_id = self.get_folder_id(folder_path)
        except Exception as e:
            print(f"❌ Error buscando carpeta: {e}")
            self.log(f"ERROR buscando carpeta: {e}")
            return
        
        if not folder_id:
            print(f"❌ No se pudo encontrar la carpeta")
            self.log("ERROR: Carpeta no encontrada")
            return
        
        print(f"✅ Carpeta encontrada (ID: {folder_id[:20]}...)")
        self.log(f"Carpeta encontrada: {folder_id}")
        
        # Obtener correos (incluyendo subcarpetas de proveedores)
        print(f"📧 Obteniendo correos del 2025 (incluyendo subcarpetas)...")
        self.log("Obteniendo correos...")
        
        try:
            emails = self.get_emails_from_folder_and_subfolders(folder_id)
            total_emails = len(emails)
        except Exception as e:
            print(f"❌ Error obteniendo correos: {e}")
            self.log(f"ERROR obteniendo correos: {e}")
            return
        
        print(f"✅ {total_emails:,} correos encontrados")
        self.log(f"Total correos encontrados: {total_emails}")
        
        if total_emails == 0:
            self.log("No hay correos para procesar")
            # Marcar como procesada aunque esté vacía
            self.progress['processed_folders'][folder_path] = 0
            self.save_progress()
            return
        
        # Inicializar estadísticas de carpeta
        folder_stats = {
            'total': total_emails,
            'processed': 0,
            'correct': 0,
            'incorrect': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Procesar por lotes con paralelización
        for i in range(0, total_emails, BATCH_SIZE):
            batch = emails[i:i+BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (total_emails + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"\n📦 Lote {batch_num}/{total_batches} ({len(batch)} correos) - Procesando con {MAX_WORKERS} workers...")
            self.log(f"Procesando lote {batch_num}/{total_batches} con {MAX_WORKERS} workers")
            
            # Procesar correos en paralelo usando ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Enviar todos los correos del lote al pool
                future_to_email = {
                    executor.submit(self.process_email, email, correct_classification, folder_path): email 
                    for email in batch
                }
                
                # Procesar resultados a medida que se completan
                completed = 0
                for future in as_completed(future_to_email):
                    email = future_to_email[future]
                    email_id = email.get('id', 'unknown')
                    
                    try:
                        result = future.result()
                        
                        # Actualizar estadísticas (thread-safe)
                        with self.results_lock:
                            folder_stats['processed'] += 1
                            self.results['total_processed'] += 1
                            
                            if result['status'] == 'correct':
                                folder_stats['correct'] += 1
                                self.results['successful'] += 1
                                status_icon = '✅'
                            elif result['status'] == 'incorrect':
                                folder_stats['incorrect'] += 1
                                self.results['failed'] += 1
                                status_icon = '❌'
                            elif result['status'] == 'skipped':
                                folder_stats['skipped'] += 1
                                self.results['skipped'] += 1
                                status_icon = '⏭️'
                                
                                # Si fue saltado por duplicado, no contar como error
                                if result.get('reason') == 'already_processed':
                                    status_icon = '🔄'
                            else:
                                folder_stats['errors'] += 1
                                self.results['failed'] += 1
                                status_icon = '⚠️'
                                
                                # Guardar error para análisis
                                error_info = {
                                    'folder': folder_path,
                                    'email_id': email_id,
                                    'subject': email.get('subject', 'N/A'),
                                    'error': result.get('error', 'Unknown'),
                                    'timestamp': datetime.now().isoformat()
                                }
                                self.results['errors'].append(error_info)
                        
                        completed += 1
                        
                        # Mostrar progreso cada 10 correos
                        if completed % 10 == 0 or completed == len(batch):
                            progress_pct = (folder_stats['processed'] / total_emails) * 100
                            elapsed_time = (datetime.now() - datetime.fromisoformat(self.results['start_time'])).total_seconds() / 60
                            emails_per_min = folder_stats['processed'] / max(elapsed_time, 0.1)
                            remaining_emails = total_emails - folder_stats['processed']
                            eta_minutes = remaining_emails / max(emails_per_min, 0.1)
                            
                            print(f"   {status_icon} {folder_stats['processed']}/{total_emails} ({progress_pct:.1f}%) - "
                                  f"✅ {folder_stats['correct']} | ❌ {folder_stats['incorrect']} | "
                                  f"⏭️ {folder_stats['skipped']} | ⚠️ {folder_stats['errors']} | "
                                  f"⏱️ ETA: {eta_minutes:.0f}min")
                    
                    except KeyboardInterrupt:
                        # Permitir cancelación manual
                        print("\n⚠️  Cancelado por usuario")
                        print("💾 Guardando progreso...")
                        executor.shutdown(wait=False, cancel_futures=True)
                        self.progress['processed_folders'][folder_path] = folder_stats['processed']
                        self.progress['last_folder'] = folder_path
                        self.save_progress()
                        self.save_results()
                        raise
                    
                    except Exception as e:
                        # Capturar CUALQUIER error para que no se caiga
                        print(f"   ⚠️  Error crítico procesando correo {email_id}: {e}")
                        
                        with self.results_lock:
                            folder_stats['errors'] += 1
                            self.results['failed'] += 1
                            
                            # Guardar error
                            error_info = {
                                'folder': folder_path,
                                'email_id': email_id,
                                'subject': email.get('subject', 'N/A'),
                                'error': f'Error crítico: {str(e)}',
                                'timestamp': datetime.now().isoformat()
                            }
                            self.results['errors'].append(error_info)
                        
                        # Continuar con el siguiente correo
                        continue
            
            # Guardar progreso cada lote
            self.progress['processed_folders'][folder_path] = folder_stats['processed']
            self.progress['last_folder'] = folder_path
            self.save_progress()
            self.save_results()
            
            print(f"   💾 Progreso guardado")
        
        # Resumen de carpeta
        print(f"\n{'='*80}")
        print(f"📊 RESUMEN DE CARPETA: {folder_path}")
        print(f"{'='*80}")
        print(f"Total procesados: {folder_stats['processed']:,}")
        print(f"✅ Correctos: {folder_stats['correct']:,} ({(folder_stats['correct']/folder_stats['processed']*100):.1f}%)")
        print(f"❌ Incorrectos: {folder_stats['incorrect']:,} ({(folder_stats['incorrect']/folder_stats['processed']*100):.1f}%)")
        print(f"⏭️  Saltados: {folder_stats['skipped']:,}")
        print(f"⚠️  Errores: {folder_stats['errors']:,}")
        print()
        print(f"💡 AUTO-APRENDIZAJE:")
        print(f"   • {folder_stats['correct']:,} correos reforzaron keywords existentes")
        print(f"   • {folder_stats['incorrect']:,} correos crearon/actualizaron keywords nuevas")
        print(f"   • Total de aprendizajes: {folder_stats['correct'] + folder_stats['incorrect']:,}")
        print()
        print(f"📚 Verifica keywords en BD:")
        print(f"   SELECT COUNT(*) FROM ocr_sucursal_keywords WHERE sucursal_id = {correct_classification['sucursal_id']};")
        print(f"   SELECT COUNT(*) FROM ocr_unidad_keywords WHERE unidad_funcional_id = {correct_classification['unidad_id']};")
        
        # Guardar estadísticas de carpeta
        self.results['by_folder'][folder_path] = folder_stats
        self.save_results()
    
    def run(self):
        """Ejecuta el procesamiento completo"""
        print("=" * 80)
        print("AUTO-APRENDIZAJE MASIVO DESDE BUZÓN COMPARTIDO")
        print("=" * 80)
        print()
        print(f"📧 Buzón: {SHARED_MAILBOX}")
        print(f"📅 Período: 2025-01-01 hasta hoy")
        print(f"📦 Tamaño de lote: {BATCH_SIZE} correos")
        print(f"⚙️  Workers paralelos: {MAX_WORKERS}")
        print()
        print("💡 IMPORTANTE:")
        print("   ✅ = Clasificación correcta (refuerza keywords existentes)")
        print("   ❌ = Clasificación incorrecta (APRENDE y crea nuevas keywords)")
        print("   ⏭️  = Saltado (duplicado por CUFE)")
        print("   ⚠️  = Error técnico (problema al procesar)")
        print()
        print("   Los ❌ son NORMALES al inicio. El sistema aprende de ellos.")
        print("   Cada ❌ agrega keywords a la BD para mejorar futuras clasificaciones.")
        print()
        
        # Obtener token
        print("🔑 Obteniendo token de acceso...")
        if not self.get_access_token():
            print("❌ Error al obtener token")
            return
        
        print("✅ Token obtenido")
        print()
        
        # Procesar cada carpeta
        for folder_path, classification in FOLDER_MAPPING.items():
            self.process_folder(folder_path, classification)
        
        # Resumen final
        print("\n" + "=" * 80)
        print("📊 RESUMEN FINAL")
        print("=" * 80)
        print(f"Total procesados: {self.results['total_processed']:,}")
        print(f"✅ Exitosos: {self.results['successful']:,} ({(self.results['successful']/max(self.results['total_processed'],1)*100):.1f}%)")
        print(f"❌ Fallidos: {self.results['failed']:,}")
        print(f"⏭️  Saltados: {self.results['skipped']:,}")
        print()
        
        # Calcular tiempo
        start = datetime.fromisoformat(self.results['start_time'])
        end = datetime.now()
        duration = end - start
        hours = duration.total_seconds() / 3600
        
        print(f"⏱️  Tiempo total: {hours:.2f} horas")
        print(f"⚡ Velocidad: {self.results['total_processed']/max(hours,0.01):.0f} correos/hora")
        print()
        
        print(f"✅ Resultados guardados en: {RESULTS_FILE}")
        print(f"💾 Progreso guardado en: {PROGRESS_FILE}")


if __name__ == "__main__":
    processor = AutoLearningProcessor()
    processor.run()