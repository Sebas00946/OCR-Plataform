"""
Script para listar todas las carpetas del buzón compartido
y contar cuántos correos hay en cada una
"""
import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime

load_dotenv()

# Configuración de Microsoft Graph API
TENANT_ID = os.getenv('AZURE_TENANT_ID')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
SHARED_MAILBOX = os.getenv('SHARED_MAILBOX_EMAIL', 'recepcionfe@medilaser.com.co')

# URLs de Microsoft Graph
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_API_URL = "https://graph.microsoft.com/v1.0"


def get_access_token():
    """Obtiene el token de acceso de Microsoft Graph"""
    data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default'
    }
    
    response = requests.post(TOKEN_URL, data=data)
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"❌ Error al obtener token: {response.status_code}")
        print(response.text)
        return None


def get_folders_recursive(access_token, user_email, parent_folder_id=None, level=0, max_level=10):
    """
    Obtiene todas las carpetas recursivamente
    
    Args:
        access_token: Token de acceso
        user_email: Email del buzón
        parent_folder_id: ID de la carpeta padre (None para raíz)
        level: Nivel de profundidad (para indentación)
        max_level: Nivel máximo de profundidad
    
    Returns:
        Lista de carpetas con su información
    """
    if level > max_level:
        return []
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # URL para obtener carpetas
    if parent_folder_id:
        url = f"{GRAPH_API_URL}/users/{user_email}/mailFolders/{parent_folder_id}/childFolders"
    else:
        url = f"{GRAPH_API_URL}/users/{user_email}/mailFolders"
    
    # Agregar parámetros para obtener más información y aumentar el límite
    url += "?$select=id,displayName,totalItemCount,unreadItemCount,childFolderCount&$top=500"
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            if level == 0:  # Solo mostrar error en nivel raíz
                print(f"❌ Error al obtener carpetas: {response.status_code}")
                print(response.text)
            return []
        
        folders_data = response.json()
        folders = folders_data.get('value', [])
        
        all_folders = []
        
        for folder in folders:
            folder_info = {
                'id': folder['id'],
                'name': folder['displayName'],
                'total_items': folder.get('totalItemCount', 0),
                'unread_items': folder.get('unreadItemCount', 0),
                'child_folder_count': folder.get('childFolderCount', 0),
                'level': level,
                'path': '  ' * level + folder['displayName']
            }
            
            all_folders.append(folder_info)
            
            # Si tiene subcarpetas, obtenerlas recursivamente
            if folder.get('childFolderCount', 0) > 0:
                child_folders = get_folders_recursive(
                    access_token, 
                    user_email, 
                    folder['id'], 
                    level + 1,
                    max_level
                )
                all_folders.extend(child_folders)
        
        # Verificar si hay más páginas (paginación)
        next_link = folders_data.get('@odata.nextLink')
        if next_link:
            try:
                next_response = requests.get(next_link, headers=headers)
                if next_response.status_code == 200:
                    next_folders = next_response.json().get('value', [])
                    for folder in next_folders:
                        folder_info = {
                            'id': folder['id'],
                            'name': folder['displayName'],
                            'total_items': folder.get('totalItemCount', 0),
                            'unread_items': folder.get('unreadItemCount', 0),
                            'child_folder_count': folder.get('childFolderCount', 0),
                            'level': level,
                            'path': '  ' * level + folder['displayName']
                        }
                        all_folders.append(folder_info)
                        
                        if folder.get('childFolderCount', 0) > 0:
                            child_folders = get_folders_recursive(
                                access_token, 
                                user_email, 
                                folder['id'], 
                                level + 1,
                                max_level
                            )
                            all_folders.extend(child_folders)
            except Exception as e:
                pass
        
        return all_folders
        
    except Exception as e:
        if level == 0:
            print(f"❌ Error: {e}")
        return []


def count_emails_in_date_range(access_token, user_email, folder_id, start_date, end_date):
    """
    Cuenta correos en un rango de fechas específico
    
    Args:
        access_token: Token de acceso
        user_email: Email del buzón
        folder_id: ID de la carpeta
        start_date: Fecha inicio (YYYY-MM-DD)
        end_date: Fecha fin (YYYY-MM-DD)
    
    Returns:
        Número de correos en el rango
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Filtro para el rango de fechas
    filter_query = f"receivedDateTime ge {start_date}T00:00:00Z and receivedDateTime le {end_date}T23:59:59Z"
    
    url = f"{GRAPH_API_URL}/users/{user_email}/mailFolders/{folder_id}/messages"
    url += f"?$filter={filter_query}&$count=true&$top=1"
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('@odata.count', 0)
        else:
            return 0
            
    except Exception as e:
        print(f"⚠️  Error al contar correos: {e}")
        return 0


def main():
    """Función principal"""
    print("=" * 80)
    print("ANÁLISIS DE CARPETAS DEL BUZÓN COMPARTIDO")
    print("=" * 80)
    print()
    
    # Verificar configuración
    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        print("❌ ERROR: Faltan credenciales de Microsoft 365")
        print()
        print("Agrega estas variables al archivo .env:")
        print("  MS_TENANT_ID=tu_tenant_id")
        print("  MS_CLIENT_ID=tu_client_id")
        print("  MS_CLIENT_SECRET=tu_client_secret")
        print("  SHARED_MAILBOX_EMAIL=facturacionelectronica@indigo.tech")
        return
    
    print(f"📧 Buzón: {SHARED_MAILBOX}")
    print()
    
    # Obtener token de acceso
    print("🔑 Obteniendo token de acceso...")
    access_token = get_access_token()
    
    if not access_token:
        print("❌ No se pudo obtener el token de acceso")
        return
    
    print("✅ Token obtenido correctamente")
    print()
    
    # Obtener todas las carpetas
    print("📁 Listando carpetas...")
    print()
    
    folders = get_folders_recursive(access_token, SHARED_MAILBOX)
    
    if not folders:
        print("❌ No se encontraron carpetas")
        return
    
    # Mostrar carpetas
    print("=" * 80)
    print("CARPETAS ENCONTRADAS")
    print("=" * 80)
    print()
    
    total_emails = 0
    
    for i, folder in enumerate(folders, 1):
        indent = '  ' * folder['level']
        print(f"{i:3d}. {indent}{folder['name']}")
        print(f"      {indent}├─ Total correos: {folder['total_items']}")
        print(f"      {indent}├─ No leídos: {folder['unread_items']}")
        print(f"      {indent}└─ Subcarpetas: {folder['child_folder_count']}")
        print()
        
        total_emails += folder['total_items']
    
    # Resumen
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Total de carpetas: {len(folders)}")
    print(f"Total de correos: {total_emails:,}")
    print()
    
    # Guardar en JSON
    output_file = "carpetas_buzon.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'fecha_analisis': datetime.now().isoformat(),
            'buzon': SHARED_MAILBOX,
            'total_carpetas': len(folders),
            'total_correos': total_emails,
            'carpetas': folders
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Información guardada en: {output_file}")
    print()
    
    # Preguntar si quiere contar correos del 2025
    print("=" * 80)
    print("¿Deseas contar correos solo del 2025? (s/n): ", end="")
    respuesta = input().strip().lower()
    
    if respuesta == 's':
        print()
        print("📊 Contando correos del 2025...")
        print()
        
        start_date = "2025-01-01"
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        total_2025 = 0
        
        for folder in folders:
            count = count_emails_in_date_range(
                access_token,
                SHARED_MAILBOX,
                folder['id'],
                start_date,
                end_date
            )
            
            if count > 0:
                print(f"  {folder['path']}: {count} correos")
                total_2025 += count
        
        print()
        print(f"Total correos del 2025: {total_2025:,}")
        print()


if __name__ == "__main__":
    main()
