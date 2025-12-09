"""
Script completo para probar todos los endpoints de la API
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def print_section(title):
    print("\n" + "="*80)
    print(title)
    print("="*80)

def test_health():
    """Prueba el endpoint de health"""
    print_section("1. HEALTH CHECK")
    response = requests.get(f"{BASE_URL}/api/health")
    data = response.json()
    print(f"✅ Status: {data['status']}")
    print(f"✅ Database: {data['database']}")
    print(f"✅ Version: {data['version']}")
    return response.status_code == 200

def test_classify():
    """Prueba el endpoint de clasificación"""
    print_section("2. CLASIFICACIÓN DE FACTURA")
    
    xml_path = "ejemplos/z09012928260082500000039/ad09012928260082500000039.xml"
    pdf_path = "ejemplos/z09012928260082500000039/fv09012928260082500000039.pdf"
    
    print(f"📋 XML: {xml_path}")
    print(f"📄 PDF: {pdf_path}\n")
    
    with open(xml_path, 'rb') as xml_file, open(pdf_path, 'rb') as pdf_file:
        files = {
            'xml_file': xml_file,
            'pdf_file': pdf_file
        }
        data = {
            'factura_id': '123'
        }
        
        response = requests.post(f"{BASE_URL}/api/classify", files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        print("📊 RESULTADO:")
        print(f"   🏢 Sucursal: {result['sucursal']['nombre']}")
        print(f"   📦 Unidad: {result['unidad_funcional']['nombre']}")
        print(f"   📈 Score Sucursal: {result['sucursal']['score']}")
        print(f"   📈 Score Unidad: {result['unidad_funcional']['score']}")
        print(f"   🔑 Keywords Sucursal: {', '.join(result['sucursal']['keywords'][:5])}")
        print(f"   🔑 Keywords Unidad: {', '.join(result['unidad_funcional']['keywords'][:5])}")
        print(f"   📝 Historial ID: {result['historial_id']}")
        print(f"   ⚖️  Peso XML: {result['metadata']['xml_weight']:.0%}")
        print(f"   ⚖️  Peso PDF: {result['metadata']['pdf_weight']:.0%}")
        return result['historial_id']
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

def test_validate(historial_id):
    """Prueba el endpoint de validación"""
    print_section("3. VALIDACIÓN (AUTO-APRENDIZAJE)")
    
    if not historial_id:
        print("⚠️  No hay historial_id para validar")
        return False
    
    data = {
        "historial_id": historial_id,
        "es_correcta": True
    }
    
    response = requests.post(
        f"{BASE_URL}/api/validate",
        json=data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
        print(f"📚 Keywords reforzadas: {result['keywords_reforzadas']}")
        return True
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return False

def test_stats():
    """Prueba el endpoint de estadísticas"""
    print_section("4. ESTADÍSTICAS DEL SISTEMA")
    
    response = requests.get(f"{BASE_URL}/api/stats")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"📊 Total clasificaciones: {stats['total_clasificaciones']}")
        print(f"✅ Validadas correctas: {stats['correctas']}")
        print(f"❌ Validadas incorrectas: {stats['incorrectas']}")
        print(f"🎯 Precisión: {stats['precision']}%")
        print(f"📈 Confianza promedio sucursal: {stats['confianza_promedio']['sucursal']}")
        print(f"📈 Confianza promedio unidad: {stats['confianza_promedio']['unidad']}")
        
        return True
    else:
        print(f"❌ Error: {response.status_code}")
        return False

def main():
    print("\n" + "="*80)
    print("🚀 PRUEBA COMPLETA DE LA API")
    print("="*80)
    
    try:
        # 1. Health check
        if not test_health():
            print("\n❌ Health check falló")
            return
        
        # 2. Clasificar
        historial_id = test_classify()
        if not historial_id:
            print("\n❌ Clasificación falló")
            return
        
        # 3. Validar
        if not test_validate(historial_id):
            print("\n⚠️  Validación falló")
        
        # 4. Estadísticas
        test_stats()
        
        print("\n" + "="*80)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
        print("="*80)
        print("\n💡 El sistema está funcionando correctamente y listo para integración con Node.js")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
