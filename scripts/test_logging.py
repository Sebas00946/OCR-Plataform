"""
Script para probar el sistema de logging
"""
import requests
import time
from pathlib import Path

API_URL = "http://localhost:8000"

def test_logging_system():
    """Prueba el sistema de logging completo"""
    
    print("=" * 60)
    print("PRUEBA DEL SISTEMA DE LOGGING")
    print("=" * 60)
    print()
    
    # 1. Probar endpoint raíz
    print("1️⃣  Probando endpoint raíz (GET /)...")
    try:
        response = requests.get(f"{API_URL}/")
        print(f"   ✅ Status: {response.status_code}")
        print(f"   📝 Respuesta: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    time.sleep(0.5)
    
    # 2. Probar health check
    print("2️⃣  Probando health check (GET /api/health)...")
    try:
        response = requests.get(f"{API_URL}/api/health")
        print(f"   ✅ Status: {response.status_code}")
        print(f"   📝 Respuesta: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    time.sleep(0.5)
    
    # 3. Probar estadísticas
    print("3️⃣  Probando estadísticas (GET /api/stats)...")
    try:
        response = requests.get(f"{API_URL}/api/stats")
        print(f"   ✅ Status: {response.status_code}")
        print(f"   📝 Respuesta: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    time.sleep(0.5)
    
    # 4. Probar clasificación con archivos de ejemplo
    print("4️⃣  Probando clasificación (POST /api/classify)...")
    ejemplo_dir = Path("ejemplos/z09012928260082500000039")
    
    if ejemplo_dir.exists():
        xml_file = ejemplo_dir / "ad09012928260082500000039.xml"
        pdf_file = ejemplo_dir / "fv09012928260082500000039.pdf"
        
        if xml_file.exists() and pdf_file.exists():
            try:
                files = {
                    'xml_file': open(xml_file, 'rb'),
                    'pdf_file': open(pdf_file, 'rb')
                }
                data = {'factura_id': 99999}
                
                response = requests.post(
                    f"{API_URL}/api/classify",
                    files=files,
                    data=data
                )
                
                print(f"   ✅ Status: {response.status_code}")
                result = response.json()
                print(f"   📝 Sucursal: {result.get('sucursal', {}).get('nombre', 'No detectada')}")
                print(f"   📝 Unidad: {result.get('unidad_funcional', {}).get('nombre', 'No detectada')}")
                print(f"   📝 Historial ID: {result.get('historial_id')}")
                
                historial_id = result.get('historial_id')
                
                # Cerrar archivos
                for f in files.values():
                    f.close()
                
                # 5. Probar validación
                if historial_id:
                    print()
                    print("5️⃣  Probando validación (POST /api/validate)...")
                    time.sleep(0.5)
                    
                    try:
                        validation_data = {
                            "historial_id": historial_id,
                            "es_correcta": True,
                            "observaciones": "Prueba de logging - clasificación correcta"
                        }
                        
                        response = requests.post(
                            f"{API_URL}/api/validate",
                            json=validation_data
                        )
                        
                        print(f"   ✅ Status: {response.status_code}")
                        print(f"   📝 Respuesta: {response.json()}")
                    except Exception as e:
                        print(f"   ❌ Error: {e}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        else:
            print("   ⚠️  Archivos de ejemplo no encontrados")
    else:
        print("   ⚠️  Directorio de ejemplos no encontrado")
    
    print()
    time.sleep(0.5)
    
    # 6. Probar resumen de logs
    print("6️⃣  Obteniendo resumen de logs (GET /api/logs)...")
    try:
        response = requests.get(f"{API_URL}/api/logs")
        print(f"   ✅ Status: {response.status_code}")
        result = response.json()
        
        print(f"\n   📊 RESUMEN DE LOGS:")
        print(f"   {'='*50}")
        
        print(f"\n   📡 Peticiones por endpoint:")
        for endpoint, count in result.get('peticiones_por_endpoint', {}).items():
            print(f"      • {endpoint}: {count} peticiones")
        
        print(f"\n   📄 Archivos procesados:")
        file_stats = result.get('archivos_procesados', {})
        print(f"      • Total facturas: {file_stats.get('total_facturas', 0)}")
        print(f"      • Con XML: {file_stats.get('con_xml', 0)}")
        print(f"      • Con PDF: {file_stats.get('con_pdf', 0)}")
        print(f"      • Con ambos: {file_stats.get('con_ambos', 0)}")
        print(f"      • Exitosas: {file_stats.get('exitosas', 0)}")
        print(f"      • Fallidas: {file_stats.get('fallidas', 0)}")
        
        print(f"\n   📁 Archivos de log:")
        for log_type, log_path in result.get('archivos_log', {}).items():
            print(f"      • {log_type}: {log_path}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    print("=" * 60)
    print("✅ PRUEBA COMPLETADA")
    print("=" * 60)
    print()
    print("📝 Los logs se han guardado en:")
    print("   • logs/api_requests.log - Todas las peticiones HTTP")
    print("   • logs/processed_files.log - Archivos procesados")
    print("   • logs/statistics.log - Consultas de estadísticas")
    print()


if __name__ == "__main__":
    print("\n⚠️  Asegúrate de que el servidor esté corriendo:")
    print("   python run.py")
    print()
    input("Presiona ENTER para continuar...")
    print()
    
    test_logging_system()
