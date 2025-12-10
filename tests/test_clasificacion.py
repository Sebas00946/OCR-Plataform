"""
Script de prueba para clasificar la factura de ejemplo
"""
import requests
import json
from pathlib import Path

# Configuración
API_URL = "http://localhost:8000"
XML_PATH = "ejemplos/z08002503820122500006DF7/ad08002503820122500006DF7.xml"
PDF_PATH = "ejemplos/z08002503820122500006DF7/ad08002503820122500006DF7.pdf"

def test_health():
    """Verificar que la API esté funcionando"""
    print("=" * 80)
    print("1. VERIFICANDO ESTADO DE LA API")
    print("=" * 80)
    
    response = requests.get(f"{API_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Respuesta: {json.dumps(response.json(), indent=2)}")
    print()
    
    return response.status_code == 200

def test_classify():
    """Clasificar la factura de ejemplo"""
    print("=" * 80)
    print("2. CLASIFICANDO FACTURA DE EJEMPLO")
    print("=" * 80)
    print(f"XML: {XML_PATH}")
    print(f"PDF: {PDF_PATH}")
    print()
    
    # Preparar archivos
    files = {}
    
    if Path(XML_PATH).exists():
        files['xml_file'] = open(XML_PATH, 'rb')
        print("✅ Archivo XML encontrado")
    else:
        print("❌ Archivo XML no encontrado")
    
    if Path(PDF_PATH).exists():
        files['pdf_file'] = open(PDF_PATH, 'rb')
        print("✅ Archivo PDF encontrado")
    else:
        print("❌ Archivo PDF no encontrado")
    
    print()
    
    # Enviar request
    print("Enviando request a /api/classify...")
    try:
        response = requests.post(
            f"{API_URL}/api/classify",
            files=files,
            data={'factura_id': 999}
        )
        
        # Cerrar archivos
        for f in files.values():
            f.close()
        
        print(f"Status: {response.status_code}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            
            print("=" * 80)
            print("RESULTADO DE LA CLASIFICACIÓN")
            print("=" * 80)
            print()
            
            # Sucursal
            print("🏢 SUCURSAL:")
            if result.get('sucursal'):
                sucursal = result['sucursal']
                print(f"   ✅ DETECTADA: {sucursal.get('nombre', 'N/A')}")
                print(f"   📊 Score: {sucursal.get('score', 0)}")
                print(f"   🔑 Keywords: {', '.join(sucursal.get('keywords', [])[:5])}")
            else:
                print("   ❌ No detectada")
            
            print()
            
            # Unidad Funcional
            print("📦 UNIDAD FUNCIONAL:")
            if result.get('unidad_funcional'):
                unidad = result['unidad_funcional']
                print(f"   ✅ DETECTADA: {unidad.get('nombre', 'N/A')}")
                print(f"   📊 Score: {unidad.get('score', 0)}")
                print(f"   🔑 Keywords: {', '.join(unidad.get('keywords', [])[:5])}")
            else:
                print("   ❌ No detectada")
            
            print()
            
            # Metadata
            print("📊 METADATA:")
            metadata = result.get('metadata', {})
            print(f"   XML Quality: {metadata.get('xml_quality', 0):.0%}")
            print(f"   XML Weight: {metadata.get('xml_weight', 0):.0%}")
            print(f"   PDF Weight: {metadata.get('pdf_weight', 0):.0%}")
            print(f"   Has XML: {'✅' if metadata.get('has_xml') else '❌'}")
            print(f"   Has PDF: {'✅' if metadata.get('has_pdf') else '❌'}")
            
            print()
            
            # Historial ID
            if result.get('historial_id'):
                print(f"💾 Historial ID: {result['historial_id']}")
                print()
            
            # JSON completo
            print("=" * 80)
            print("JSON COMPLETO")
            print("=" * 80)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            return result
        else:
            print("❌ ERROR:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return None
            
    except Exception as e:
        print(f"❌ Error al hacer request: {e}")
        return None

def test_stats():
    """Obtener estadísticas del sistema"""
    print()
    print("=" * 80)
    print("3. ESTADÍSTICAS DEL SISTEMA")
    print("=" * 80)
    
    try:
        response = requests.get(f"{API_URL}/api/stats")
        
        if response.status_code == 200:
            stats = response.json()
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "PRUEBA DE CLASIFICACIÓN OCR" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # 1. Verificar salud
    if not test_health():
        print("❌ La API no está disponible. Asegúrate de que esté corriendo.")
        exit(1)
    
    # 2. Clasificar
    result = test_classify()
    
    # 3. Estadísticas
    if result:
        test_stats()
    
    print()
    print("=" * 80)
    print("PRUEBA COMPLETADA")
    print("=" * 80)
    print()
