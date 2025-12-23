"""
Script para probar que TODAS las carpetas del FOLDER_MAPPING
se pueden encontrar correctamente navegando por subcarpetas
"""
import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

load_dotenv()

TENANT_ID = os.getenv('AZURE_TENANT_ID')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
SHARED_MAILBOX = os.getenv('SHARED_MAILBOX_EMAIL', 'recepcionfe@medilaser.com.co')

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

# FOLDER_MAPPING actual
FOLDER_MAPPING = {
    "1. NEIVA/1.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 4, "unidad_id": 11},
    "1. NEIVA/1.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 4, "unidad_id": 5},
    "1. NEIVA/1.3. GASTOS": {"sucursal_id": 4, "unidad_id": 11},
    
    "2. TUNJA/2.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 5, "unidad_id": 13},
    "2. TUNJA/2.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 5, "unidad_id": 9},
    "2. TUNJA/2.3. GASTOS": {"sucursal_id": 5, "unidad_id": 13},
    
    "3.FLORENCIA/3.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 3, "unidad_id": 12},
    "3.FLORENCIA/3.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 3, "unidad_id": 8},
    "3.FLORENCIA/3.3. GASTOS": {"sucursal_id": 3, "unidad_id": 12},
    
    "4. PITALITO/4.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 7, "unidad_id": 15},
    "4. PITALITO/4.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 7, "unidad_id": 15},
    "4. PITALITO/4.3. GASTOS": {"sucursal_id": 7, "unidad_id": 15},
    
    "5. BOGOTA/5.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 2, "unidad_id": 14},
    "5. BOGOTA/5.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 2, "unidad_id": 2},
    "5. BOGOTA/5.3. GASTOS": {"sucursal_id": 2, "unidad_id": 14},
    
    "6. FACATATIVA/6.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 2, "unidad_id": 14},
    "6. FACATATIVA/6.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 2, "unidad_id": 2},
    "6. FACATATIVA/6.3 GASTOS": {"sucursal_id": 2, "unidad_id": 14},
    
    "7. DUITAMA/7.1. PROVEEDORES MÉDICOS E IPS": {"sucursal_id": 1, "unidad_id": 11},
    "7. DUITAMA/7.3. GASTOS": {"sucursal_id": 1, "unidad_id": 11},
}

def get_folder_id(access_token, folder_path):
    """
    Obtiene ID de carpeta por su ruta (desde SUCURSALES)
    Simula el método del script principal
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Primero obtener carpeta SUCURSALES
    url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders?$top=500"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return None, f"Error obteniendo carpetas raíz: {response.status_code}"
    
    folders = response.json().get('value', [])
    sucursales_folder = None
    
    for folder in folders:
        if 'SUCURSALES' in folder['displayName'].upper():
            sucursales_folder = folder['id']
            break
    
    if not sucursales_folder:
        return None, "No se encontró carpeta SUCURSALES"
    
    # Navegar por la ruta desde SUCURSALES
    parts = folder_path.split('/')
    current_id = sucursales_folder
    
    for i, part in enumerate(parts):
        url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders/{current_id}/childFolders?$top=500"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return None, f"Error obteniendo subcarpetas en nivel {i+1}: {response.status_code}"
        
        folders = response.json().get('value', [])
        found = False
        
        # Buscar la carpeta (comparación flexible)
        for folder in folders:
            folder_name = folder['displayName']
            # Comparar ignorando espacios extras y mayúsculas/minúsculas
            if folder_name.strip().upper() == part.strip().upper():
                current_id = folder['id']
                found = True
                break
        
        if not found:
            available = [f['displayName'] for f in folders[:10]]
            return None, f"No encontrada '{part}' en nivel {i+1}. Disponibles: {available}"
    
    return current_id, "OK"

print("=" * 80)
print("PRUEBA DE NAVEGACIÓN DE TODAS LAS CARPETAS")
print("=" * 80)
print()
print(f"Buzón: {SHARED_MAILBOX}")
print(f"Total carpetas a probar: {len(FOLDER_MAPPING)}")
print()

# Obtener token
print("🔑 Obteniendo token de acceso...")
data = {
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'scope': 'https://graph.microsoft.com/.default'
}

response = requests.post(TOKEN_URL, data=data)
if response.status_code != 200:
    print(f"❌ Error obteniendo token: {response.status_code}")
    exit(1)

access_token = response.json()['access_token']
print("✅ Token obtenido")
print()

print("=" * 80)
print("PROBANDO CADA CARPETA")
print("=" * 80)
print()

exitosas = 0
fallidas = 0
errores = []

for idx, (folder_path, mapping) in enumerate(FOLDER_MAPPING.items(), 1):
    print(f"[{idx}/{len(FOLDER_MAPPING)}] Probando: {folder_path}")
    
    folder_id, mensaje = get_folder_id(access_token, folder_path)
    
    if folder_id:
        print(f"   ✅ ENCONTRADA")
        print(f"      ID: {folder_id[:30]}...")
        print(f"      Sucursal: {mapping['sucursal_id']}, Unidad: {mapping['unidad_id']}")
        exitosas += 1
    else:
        print(f"   ❌ ERROR: {mensaje}")
        fallidas += 1
        errores.append({
            'carpeta': folder_path,
            'error': mensaje,
            'mapping': mapping
        })
    
    print()

print("=" * 80)
print("RESUMEN FINAL")
print("=" * 80)
print()
print(f"✅ Carpetas encontradas: {exitosas}/{len(FOLDER_MAPPING)}")
print(f"❌ Carpetas con error: {fallidas}/{len(FOLDER_MAPPING)}")
print()

if fallidas > 0:
    print("=" * 80)
    print("CARPETAS CON ERRORES")
    print("=" * 80)
    print()
    
    for error in errores:
        print(f"❌ {error['carpeta']}")
        print(f"   Error: {error['error']}")
        print(f"   Mapping: {error['mapping']}")
        print()
    
    print("⚠️  ACCIÓN REQUERIDA:")
    print("   Corrige los nombres en FOLDER_MAPPING antes de ejecutar el procesamiento")
    print()
else:
    print("🎉 ¡TODAS LAS CARPETAS SE PUEDEN ENCONTRAR CORRECTAMENTE!")
    print()
    print("✅ El sistema está listo para iniciar el auto-aprendizaje")
    print()
    print("Para iniciar:")
    print("   python auto_learning/auto_learning_from_mailbox.py")
    print()
