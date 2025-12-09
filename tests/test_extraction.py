"""
Script de prueba para extraer información de facturas XML y PDF
"""
import json
import sys
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from domain.invoice_processor import InvoiceProcessor


def test_extraction():
    """Prueba la extracción de datos de los archivos de ejemplo"""
    
    # Rutas a los archivos de ejemplo
    xml_path = "ejemplos/ad09004334370002500033071.xml"
    pdf_path = "ejemplos/FQE139169.pdf"
    
    print("=" * 80)
    print("PRUEBA DE EXTRACCIÓN DE FACTURAS")
    print("=" * 80)
    print()
    
    # Crear procesador
    processor = InvoiceProcessor()
    
    # Procesar factura
    print("Procesando factura...")
    print(f"  XML: {xml_path}")
    print(f"  PDF: {pdf_path}")
    print()
    
    try:
        result = processor.process_invoice(xml_path=xml_path, pdf_path=pdf_path)
        
        # Mostrar resultados
        print("=" * 80)
        print("RESULTADOS DE LA EXTRACCIÓN")
        print("=" * 80)
        print()
        
        # Clasificación
        print("📍 CLASIFICACIÓN:")
        print(f"  Sucursal detectada: {result['clasificacion']['sucursal']}")
        print(f"  Área responsable: {result['clasificacion']['area']}")
        print(f"  Confianza: {result['clasificacion']['confianza']}")
        print(f"  Fuente: {result['clasificacion']['fuente']}")
        print()
        
        # Proveedor
        print("🏢 PROVEEDOR:")
        if result['proveedor']:
            for key, value in result['proveedor'].items():
                print(f"  {key.capitalize()}: {value}")
        print()
        
        # Cliente
        print("👤 CLIENTE:")
        if result['cliente']:
            for key, value in result['cliente'].items():
                print(f"  {key.capitalize()}: {value}")
        print()
        
        # Factura
        print("📄 FACTURA:")
        if result['factura']:
            for key, value in result['factura'].items():
                print(f"  {key.capitalize()}: {value}")
        print()
        
        # Totales
        print("💰 TOTALES:")
        if result['totales']:
            for key, value in result['totales'].items():
                print(f"  {key.capitalize()}: {value}")
        print()
        
        # Items (primeros 5)
        print("📦 ITEMS (primeros 5):")
        if result['items']:
            for i, item in enumerate(result['items'][:5], 1):
                print(f"  {i}. {item.get('descripcion', 'N/A')}")
                print(f"     Cantidad: {item.get('cantidad', 'N/A')} | Precio: {item.get('precio', 'N/A')}")
        print()
        
        # Resumen para API
        print("=" * 80)
        print("RESUMEN PARA API (JSON)")
        print("=" * 80)
        summary = processor.get_classification_summary(result)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        print()
        
        # Guardar resultado completo
        output_file = "test_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Resultado completo guardado en: {output_file}")
        
    except Exception as e:
        print(f"❌ Error durante el procesamiento: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_extraction()
