"""
Script para probar el API de clasificación de facturas
"""
import requests
import json
from pathlib import Path


def test_api_local():
    """Prueba el API localmente"""
    
    # URL del API (asumiendo que está corriendo en localhost:8000)
    base_url = "http://localhost:8000"
    
    # Archivos de prueba
    xml_file = "ejemplos/ad09004334370002500033071.xml"
    pdf_file = "ejemplos/FQE139169.pdf"
    
    print("=" * 80)
    print("PRUEBA DEL API DE CLASIFICACIÓN DE FACTURAS")
    print("=" * 80)
    print()
    
    # Verificar que los archivos existen
    if not Path(xml_file).exists():
        print(f"❌ Error: No se encuentra el archivo {xml_file}")
        return
    
    if not Path(pdf_file).exists():
        print(f"❌ Error: No se encuentra el archivo {pdf_file}")
        return
    
    print("📁 Archivos de prueba:")
    print(f"  XML: {xml_file}")
    print(f"  PDF: {pdf_file}")
    print()
    
    # Test 1: Endpoint /classify (solo clasificación)
    print("=" * 80)
    print("TEST 1: Clasificación simple (/api/invoices/classify)")
    print("=" * 80)
    
    try:
        with open(xml_file, 'rb') as xml_f, open(pdf_file, 'rb') as pdf_f:
            files = {
                'xml_file': ('factura.xml', xml_f, 'application/xml'),
                'pdf_file': ('factura.pdf', pdf_f, 'application/pdf')
            }
            
            response = requests.post(f"{base_url}/api/invoices/classify", files=files)
            
            if response.status_code == 200:
                print("✅ Respuesta exitosa")
                print()
                print("Resultado:")
                print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
    
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar al servidor")
        print("   Asegúrate de que el servidor esté corriendo:")
        print("   python -m uvicorn src.main:app --reload")
        return
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return
    
    print()
    
    # Test 2: Endpoint /process (información completa)
    print("=" * 80)
    print("TEST 2: Procesamiento completo (/api/invoices/process)")
    print("=" * 80)
    
    try:
        with open(xml_file, 'rb') as xml_f, open(pdf_file, 'rb') as pdf_f:
            files = {
                'xml_file': ('factura.xml', xml_f, 'application/xml'),
                'pdf_file': ('factura.pdf', pdf_f, 'application/pdf')
            }
            
            response = requests.post(f"{base_url}/api/invoices/process", files=files)
            
            if response.status_code == 200:
                print("✅ Respuesta exitosa")
                print()
                print("Resultado:")
                print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return
    
    print()
    print("=" * 80)
    print("PRUEBAS COMPLETADAS")
    print("=" * 80)


def generate_curl_examples():
    """Genera ejemplos de comandos curl para probar el API"""
    
    print()
    print("=" * 80)
    print("EJEMPLOS DE COMANDOS CURL")
    print("=" * 80)
    print()
    
    print("# Clasificación simple (solo XML):")
    print('curl -X POST "http://localhost:8000/api/invoices/classify" \\')
    print('  -F "xml_file=@ejemplos/ad09004334370002500033071.xml"')
    print()
    
    print("# Clasificación simple (XML + PDF):")
    print('curl -X POST "http://localhost:8000/api/invoices/classify" \\')
    print('  -F "xml_file=@ejemplos/ad09004334370002500033071.xml" \\')
    print('  -F "pdf_file=@ejemplos/FQE139169.pdf"')
    print()
    
    print("# Procesamiento completo:")
    print('curl -X POST "http://localhost:8000/api/invoices/process" \\')
    print('  -F "xml_file=@ejemplos/ad09004334370002500033071.xml" \\')
    print('  -F "pdf_file=@ejemplos/FQE139169.pdf"')
    print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "curl":
        generate_curl_examples()
    else:
        test_api_local()
        generate_curl_examples()
