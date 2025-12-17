from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import json
import pandas as pd
from typing import List, Dict

class ZendeskSeleniumScraper:
    def __init__(self, email: str, password: str, headless: bool = False):
        """
        Inicializa el scraper con Selenium
        
        Args:
            email: Email de usuario
            password: Contraseña
            headless: Ejecutar sin interfaz gráfica
        """
        self.email = email
        self.password = password
        self.base_url = "https://soporte.indigo.ms"
        
        # Configurar Chrome
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User agent real
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
        
        print("✓ Navegador Chrome iniciado")
    
    def login(self) -> bool:
        """
        Realiza el login usando Selenium
        """
        try:
            print("\n=== Iniciando Login con Selenium ===\n")
            
            # Ir a la página de login
            login_url = "https://indigocolombia.zendesk.com/auth/v2/login/signin"
            params = "?return_to=https://soporte.indigo.ms/hc/es&theme=hc&locale=es&brand_id=2525076&auth_origin=2525076,true,true"
            
            print(f"Navegando a: {login_url}{params}")
            self.driver.get(login_url + params)
            
            # Esperar a que cargue el formulario
            print("Esperando formulario de login...")
            email_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, "user[email]"))
            )
            
            # Ingresar email
            print(f"Ingresando email: {self.email}")
            email_input.clear()
            email_input.send_keys(self.email)
            time.sleep(0.5)
            
            # Ingresar password
            password_input = self.driver.find_element(By.NAME, "user[password]")
            print("Ingresando password...")
            password_input.clear()
            password_input.send_keys(self.password)
            time.sleep(0.5)
            
            # Hacer clic en el botón de login
            print("Haciendo clic en 'Iniciar sesión'...")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            submit_button.click()
            
            # Esperar a que se complete el login
            print("Esperando redirección...")
            time.sleep(3)
            
            # Verificar si el login fue exitoso
            current_url = self.driver.current_url
            print(f"URL actual: {current_url}")
            
            # Obtener cookies
            cookies = self.driver.get_cookies()
            cookie_names = [c['name'] for c in cookies]
            
            print(f"Cookies obtenidas: {cookie_names}")
            
            # Verificar si hay cookie de autenticación
            auth_cookie = None
            for cookie in cookies:
                if cookie['name'] == '_zendesk_authenticated':
                    auth_cookie = cookie
                    break
            
            if auth_cookie or "soporte.indigo.ms" in current_url:
                print("\n✅ LOGIN EXITOSO\n")
                return True
            else:
                print("\n❌ Login falló - no se encontró cookie de autenticación")
                return False
                
        except Exception as e:
            print(f"\n❌ Error durante login: {e}")
            return False
    
    def get_api_cookies(self) -> Dict[str, str]:
        """
        Obtiene las cookies del navegador para usar en requests
        """
        cookies = {}
        for cookie in self.driver.get_cookies():
            cookies[cookie['name']] = cookie['value']
        return cookies
    
    def get_requests_with_api(self, year: int = 2025) -> List[Dict]:
        """
        Una vez autenticado, obtiene las solicitudes usando la API
        """
        import requests
        
        print(f"\n=== Extrayendo solicitudes del {year} vía API ===\n")
        
        # Obtener cookies del navegador
        cookies = self.get_api_cookies()
        
        # Crear sesión de requests con las cookies
        session = requests.Session()
        session.cookies.update(cookies)
        session.verify = False
        
        all_requests = []
        page = 1
        
        while True:
            try:
                url = f"{self.base_url}/api/v2/requests.json"
                params = {'page': page, 'per_page': 100}
                
                response = session.get(url, params=params, timeout=30)
                
                if response.status_code != 200:
                    print(f"❌ Error en página {page}. Status: {response.status_code}")
                    break
                
                data = response.json()
                requests_data = data.get('requests', [])
                
                if not requests_data:
                    print(f"✓ No hay más datos. Total páginas: {page - 1}")
                    break
                
                # Filtrar por año
                requests_year = [r for r in requests_data if r.get('created_at', '').startswith(str(year))]
                all_requests.extend(requests_year)
                
                print(f"Página {page}: {len(requests_data)} solicitudes, {len(requests_year)} del {year} | Total: {len(all_requests)}")
                
                if not data.get('next_page'):
                    break
                
                page += 1
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Error: {e}")
                break
        
        print(f"\n✓ TOTAL SOLICITUDES {year}: {len(all_requests)}")
        return all_requests
    
    def export_to_csv(self, requests_data: List[Dict], filename: str = 'solicitudes_2025.csv'):
        """Exporta a CSV"""
        if not requests_data:
            print("⚠ No hay datos para exportar")
            return
        
        rows = []
        for req in requests_data:
            row = {
                'id': req.get('id'),
                'status': req.get('status'),
                'priority': req.get('priority'),
                'type': req.get('type'),
                'subject': req.get('subject'),
                'description': req.get('description'),
                'organization_id': req.get('organization_id'),
                'requester_id': req.get('requester_id'),
                'created_at': req.get('created_at'),
                'updated_at': req.get('updated_at'),
                'url': req.get('url')
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✓ Datos exportados a: {filename}")
    
    def export_to_json(self, requests_data: List[Dict], filename: str = 'solicitudes_2025.json'):
        """Exporta a JSON"""
        if not requests_data:
            print("⚠ No hay datos para exportar")
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(requests_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Datos exportados a: {filename}")
    
    def close(self):
        """Cierra el navegador"""
        if self.driver:
            self.driver.quit()
            print("\n✓ Navegador cerrado")


# Ejemplo de uso
if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    EMAIL = "acruzt@medilaser.com.co"
    PASSWORD = "1234567"
    
    print("╔════════════════════════════════════════╗")
    print("║  ZENDESK SCRAPER CON SELENIUM         ║")
    print("╚════════════════════════════════════════╝\n")
    
    scraper = None
    
    try:
        # Crear scraper (headless=False para ver el navegador)
        scraper = ZendeskSeleniumScraper(EMAIL, PASSWORD, headless=False)
        
        # Login
        if scraper.login():
            # Obtener solicitudes
            requests_2025 = scraper.get_requests_with_api(year=2025)
            
            if requests_2025:
                # Exportar
                scraper.export_to_csv(requests_2025)
                scraper.export_to_json(requests_2025)
                
                print("\n=== EJEMPLO DE SOLICITUD ===")
                print(json.dumps(requests_2025[0], indent=2, ensure_ascii=False)[:500] + "...")
            else:
                print("\n⚠ No se encontraron solicitudes del 2025")
        else:
            print("\n❌ No se pudo iniciar sesión")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    finally:
        if scraper:
            input("\nPresiona Enter para cerrar el navegador...")
            scraper.close()
    
    print("\n" + "="*50)
    print("Proceso finalizado")
    print("="*50)