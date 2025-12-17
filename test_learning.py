"""
Prueba del sistema de auto-aprendizaje
"""
import requests
import json

API_URL = "http://localhost:8000"

print("=" * 100)
print("PRUEBA DE SISTEMA DE AUTO-APRENDIZAJE")
print("=" * 100)
print()

# Test 1: Verificar que la API está funcionando
print("1. Verificando API...")
try:
    response = requests.get(f"{API_URL}/api/health")
    if response.status_code == 200:
        print("   ✅ API funcionando correctamente")
    else:
        print("   ❌ API no responde correctamente")
        exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    print("   Asegúrate de que la API esté corriendo: py run.py")
    exit(1)

print()

# Test 2: Simular una reclasificación
print("2. Simulando reclasificación de factura...")
print("   Factura mal clasificada como NEIVA, debería ser TUNJA")
print()

validation_data = {
    "historial_id": 7,  # Usar un ID existente
    "es_correcta": False,
    "sucursal_correcta_id": 5,  # Tunja
    "unidad_correcta_id": 9,    # Almacén - TJA
    "observaciones": "Prueba de auto-aprendizaje: Factura de TUNJA"
}

try:
    response = requests.post(
        f"{API_URL}/api/validate",
        json=validation_data
    )
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        
        print()
        print("=" * 100)
        print("RESULTADO DEL AUTO-APRENDIZAJE")
        print("=" * 100)
        print()
        print(f"✅ {result.get('message', 'Procesado correctamente')}")
        print()
        
        learning = result.get('learning', {})
        
        # Keywords agregadas
        if learning.get('keywords_added'):
            print("🎓 KEYWORDS AGREGADAS AUTOMÁTICAMENTE:")
            for kw in learning['keywords_added']:
                keyword = kw.get('keyword', '')
                tipo = kw.get('tipo', '')
                peso = kw.get('peso_sugerido', 0)
                razon = kw.get('razon', '')
                accion = kw.get('accion', 'agregada')
                
                emoji = "➕" if accion == 'agregada' else "🔄"
                print(f"   {emoji} [{tipo.upper()}] '{keyword}' (peso: {peso})")
                print(f"      Razón: {razon}")
            print()
        
        # Keywords reforzadas
        if learning.get('keywords_reforzadas', 0) > 0:
            print(f"⬆️  KEYWORDS REFORZADAS: {learning['keywords_reforzadas']}")
            print()
        
        # Keywords sugeridas
        if learning.get('keywords_suggested'):
            print("💡 KEYWORDS SUGERIDAS:")
            for kw in learning['keywords_suggested']:
                print(f"   - {kw.get('keyword', '')} (peso: {kw.get('peso_sugerido', 0)})")
            print()
        
        print("=" * 100)
        print("JSON COMPLETO")
        print("=" * 100)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        print("=" * 100)
        print("✅ PRUEBA EXITOSA")
        print("=" * 100)
        print()
        print("El sistema de auto-aprendizaje está funcionando correctamente!")
        print("Cada vez que reclasifiques una factura, el sistema aprenderá automáticamente.")
        
    else:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   Respuesta: {response.text}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
