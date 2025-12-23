"""
Script simple para listar carpetas del buzón
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

# Obtener token
data = {
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'scope': 'https://graph.microsoft.com/.default'
}

response = requests.post(TOKEN_URL, data=data)
access_token = response.json()['access_token']

headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

# Obtener carpetas raíz
url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders?$top=500"
response = requests.get(url, headers=headers)
folders = response.json().get('value', [])

# Buscar SUCURSALES
sucursales_id = None
for folder in folders:
    if 'SUCURSALES' in folder['displayName'].upper():
        sucursales_id = folder['id']
        print(f"✅ Carpeta SUCURSALES encontrada: {folder['displayName']}")
        break

if not sucursales_id:
    print("❌ No se encontró carpeta SUCURSALES")
    exit(1)

# Listar subcarpetas de SUCURSALES (ciudades)
url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders/{sucursales_id}/childFolders?$top=500"
response = requests.get(url, headers=headers)
ciudades = response.json().get('value', [])

print(f"\n{'='*80}")
print(f"CARPETAS DE CIUDADES EN SUCURSALES:")
print(f"{'='*80}\n")

for ciudad in ciudades:
    print(f"📁 {ciudad['displayName']}")
    
    # Listar subcarpetas de cada ciudad
    url = f"{GRAPH_API_URL}/users/{SHARED_MAILBOX}/mailFolders/{ciudad['id']}/childFolders?$top=500"
    response = requests.get(url, headers=headers)
    tipos = response.json().get('value', [])
    
    for tipo in tipos:
        print(f"   └─ {tipo['displayName']} ({tipo.get('totalItemCount', 0)} correos)")
    
    print()
