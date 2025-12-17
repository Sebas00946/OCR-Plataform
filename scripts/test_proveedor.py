"""
Script para probar la extracción de datos del proveedor
"""
import requests
import json
from pathlib import Path

API_URL = "http://localhost:8000"

def test_proveedor_extraction():
    """Prueba la extracción de datos del proveedor"""
    
    print("=" * 70)
    print("PRUEBA DE EXTRACCIÓN DE DATOS DEL PROVEEDOR")
    print("=" * 70)
    print()
    
    # Buscar archivos de ejemplo
    ejemplo_dir = Path("ejemplos/z09012928260082500000039")
    
    if not ejemplo_dir.exists():
        print("❌ No se encontró el directorio de ejemplos")
        return
    
    xml_file = ejemplo_dir / "ad09012928260082500000039.xml"
    pdf_file = ejemplo_dir / "fv09012928260082500000039.pdf"
    
    if not xml_file.exists() or not pdf_file.exists():
        print("❌ No se encontraron los archivos de ejemplo")
        return
    
    print("📄 Archivos a procesar:")
    print(f"   • XML: {xml_file.name}")
    print(f"   • PDF: {pdf_file.name}")
    print()
    
    # Clasificar factura
    print("🔄 Clasificando factura...")
    print()
    
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
        
        # Cerrar archivos
        for f in files.values():
            f.close()
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return
        
        result = response.json()
        
        # Mostrar resultados
        print("=" * 70)
        print("✅ CLASIFICACIÓN EXITOSA")
        print("=" * 70)
        print()
        
        # Datos del proveedor
        proveedor = result.get('proveedor', {})
        
        if proveedor:
            print("📦 DATOS DEL PROVEEDOR:")
            print("-" * 70)
            
            if 'proveedor_nombre' in proveedor:
                print(f"   Nombre:     {proveedor['proveedor_nombre']}")
            
            if 'proveedor_nit' in proveedor:
                print(f"   NIT:        {proveedor['proveedor_nit']}")
            
            if 'proveedor_direccion' in proveedor:
                print(f"   Dirección:  {proveedor['proveedor_direccion']}")
            
            if 'proveedor_ciudad' in proveedor:
                print(f"   Ciudad:     {proveedor['proveedor_ciudad']}")
            
            if 'proveedor_telefono' in proveedor:
                print(f"   Teléfono:   {proveedor['proveedor_telefono']}")
            
            if 'proveedor_email' in proveedor:
                print(f"   Email:      {proveedor['proveedor_email']}")
            
            if not proveedor:
                print("   ⚠️  No se encontraron datos del proveedor en el XML")
        else:
            print("📦 DATOS DEL PROVEEDOR:")
            print("-" * 70)
            print("   ⚠️  No se extrajeron datos del proveedor")
        
        print()
        
        # Sucursal detectada
        sucursal = result.get('sucursal')
        if sucursal:
            print("🏢 SUCURSAL DETECTADA:")
            print("-" * 70)
            print(f"   Nombre:     {sucursal['nombre']}")
            print(f"   Código:     {sucursal['codigo']}")
            print(f"   Score:      {sucursal['score']}")
            print(f"   Keywords:   {', '.join(sucursal['keywords'])}")
        else:
            print("🏢 SUCURSAL: No detectada")
        
        print()
        
        # Unidad funcional detectada
        unidad = result.get('unidad_funcional')
        if unidad:
            print("📋 UNIDAD FUNCIONAL DETECTADA:")
            print("-" * 70)
            print(f"   Nombre:     {unidad['nombre']}")
            print(f"   Código:     {unidad['codigo']}")
            print(f"   Score:      {unidad['score']}")
            print(f"   Keywords:   {', '.join(unidad['keywords'])}")
        else:
            print("📋 UNIDAD FUNCIONAL: No detectada")
        
        print()
        
        # Metadata
        metadata = result.get('metadata', {})
        print("📊 METADATA:")
        print("-" * 70)
        print(f"   Calidad XML:    {metadata.get('xml_quality', 0):.2f}")
        print(f"   Peso XML:       {metadata.get('xml_weight', 0):.2f}")
        print(f"   Peso PDF:       {metadata.get('pdf_weight', 0):.2f}")
        print(f"   Tiene XML:      {'Sí' if metadata.get('has_xml') else 'No'}")
        print(f"   Tiene PDF:      {'Sí' if metadata.get('has_pdf') else 'No'}")
        
        print()
        print("=" * 70)
        print("📝 JSON COMPLETO:")
        print("=" * 70)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar al servidor")
        print("   Asegúrate de que el servidor esté corriendo:")
        print("   python run.py")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print()
    print("⚠️  Asegúrate de que el servidor esté corriendo:")
    print("   python run.py")
    print()
    input("Presiona ENTER para continuar...")
    print()
    
    test_proveedor_extraction()
