"""
Script para verificar que los nombres de carpetas en FOLDER_MAPPING
coincidan exactamente con las carpetas reales del buzón
"""
import os
import requests
from dotenv import load_dotenv

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
    
    "3. FLORENCIA/3.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 3, "unidad_id": 12},
    "3. FLORENCIA/3.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 3, "unidad_id": 8},
    "3. FLORENCIA/3.3. GASTOS": {"sucursal_id": 3, "unidad_id": 12},
    
    "4. PITALITO/4.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 7, "unidad_id": 15},
    "4. PITALITO/4.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 7, "unidad_id": 15},
    "4. PITALITO/4.3. GASTOS": {"sucursal_id": 7, "unidad_id": 15},
    
    "5. BOGOTA/5.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 2, "unidad_id": 14},
    "5. BOGOTA/5.2. PROVEEDORES MEDICAMENTOS": {"sucursal_id": 2, "unidad_id": 2},
    "5. BOGOTA/5.3. GASTOS": {"sucursal_id": 2, "unidad_id": 14},
}

print("=" * 80)
print("VERIFICACIÓN DE NOMBRES DE CARPETAS")
print("=" * 80)
print()
print(f"Buzón: {SHARED_MAILBOX}")
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

headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

# Obtener carpeta SUCURSALES
print("📂 Buscando carpeta SUCURSALES...")
url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders?$top=500"
response = requests.get(url, headers=headers)
folders = response.json().get('value', [])

sucursales_id = None
for folder in folders:
    if 'SUCURSALES' in folder['displayName'].upper():
        sucursales_id = folder['id']
        print(f"✅ Carpeta SUCURSALES encontrada: '{folder['displayName']}'")
        break

if not sucursales_id:
    print("❌ No se encontró carpeta SUCURSALES")
    exit(1)

print()

# Obtener carpetas de ciudades
print("📍 Obteniendo carpetas de ciudades...")
url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders/{sucursales_id}/childFolders?$top=500"
response = requests.get(url, headers=headers)
ciudades = response.json().get('value', [])

print(f"✅ Encontradas {len(ciudades)} carpetas de ciudades")
print()

# Crear estructura de carpetas reales
carpetas_reales = {}

for ciudad in ciudades:
    ciudad_nombre = ciudad['displayName']
    print(f"📁 {ciudad_nombre}")
    
    # Obtener subcarpetas (tipos)
    url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders/{ciudad['id']}/childFolders?$top=500"
    response = requests.get(url, headers=headers)
    tipos = response.json().get('value', [])
    
    for tipo in tipos:
        tipo_nombre = tipo['displayName']
        ruta_completa = f"{ciudad_nombre}/{tipo_nombre}"
        carpetas_reales[ruta_completa] = {
            'ciudad_id': ciudad['id'],
            'tipo_id': tipo['id'],
            'correos': tipo.get('totalItemCount', 0)
        }
        print(f"   └─ {tipo_nombre} ({tipo.get('totalItemCount', 0)} correos)")
    
    print()

print("=" * 80)
print("COMPARACIÓN CON FOLDER_MAPPING")
print("=" * 80)
print()

encontradas = 0
no_encontradas = 0
sugerencias = []

for folder_path, mapping in FOLDER_MAPPING.items():
    print(f"📋 Verificando: {folder_path}")
    
    # Buscar coincidencia exacta
    if folder_path in carpetas_reales:
        print(f"   ✅ ENCONTRADA (coincidencia exacta)")
        print(f"      Correos: {carpetas_reales[folder_path]['correos']}")
        encontradas += 1
    else:
        print(f"   ❌ NO ENCONTRADA")
        no_encontradas += 1
        
        # Buscar coincidencias similares
        ciudad_parte = folder_path.split('/')[0]
        tipo_parte = folder_path.split('/')[1] if '/' in folder_path else ''
        
        similares = []
        for ruta_real in carpetas_reales.keys():
            # Comparar ignorando mayúsculas y espacios extras
            if ciudad_parte.upper().replace(' ', '') in ruta_real.upper().replace(' ', ''):
                if tipo_parte.upper().replace(' ', '') in ruta_real.upper().replace(' ', ''):
                    similares.append(ruta_real)
        
        if similares:
            print(f"   💡 Carpetas similares encontradas:")
            for similar in similares:
                print(f"      • '{similar}' ({carpetas_reales[similar]['correos']} correos)")
                sugerencias.append({
                    'buscada': folder_path,
                    'sugerida': similar,
                    'mapping': mapping
                })
        else:
            print(f"   ⚠️  No se encontraron carpetas similares")
    
    print()

print("=" * 80)
print("RESUMEN")
print("=" * 80)
print()
print(f"✅ Carpetas encontradas: {encontradas}/{len(FOLDER_MAPPING)}")
print(f"❌ Carpetas no encontradas: {no_encontradas}/{len(FOLDER_MAPPING)}")
print()

if no_encontradas > 0:
    print("=" * 80)
    print("SUGERENCIAS DE CORRECCIÓN")
    print("=" * 80)
    print()
    print("Reemplaza en FOLDER_MAPPING:")
    print()
    
    for sug in sugerencias:
        print(f"# Cambiar:")
        print(f'# "{sug["buscada"]}": {sug["mapping"]},')
        print(f"# Por:")
        print(f'"{sug["sugerida"]}": {sug["mapping"]},')
        print()

print("=" * 80)
print("TODAS LAS CARPETAS DISPONIBLES EN EL BUZÓN")
print("=" * 80)
print()

for ruta, info in sorted(carpetas_reales.items()):
    print(f"📁 {ruta} ({info['correos']} correos)")

print()
print("✅ Verificación completada")
