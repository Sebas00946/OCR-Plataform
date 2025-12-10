"""
Script de prueba para extraer información de facturas XML y PDF
"""
import json
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extractor import InvoiceExtractor
from src.classifier import PDFClassifier
from src.config import get_db_config


def test_extraction():
    """Prueba la extracción de datos de los archivos de ejemplo"""
    
    # Rutas a los archivos de ejemplo
    xml_path = "ejemplos/z08002503820122500006DF7/ad08002503820122500006DF7.xml"
    pdf_path = "ejemplos/z08002503820122500006DF7/ad08002503820122500006DF7.pdf"
    
    print("=" * 80)
    print("PRUEBA DE EXTRACCIÓN DE FACTURAS")
    print("=" * 80)
    print()
    
    # Crear extractor y clasificador
    extractor = InvoiceExtractor()
    classifier = PDFClassifier(get_db_config())
    
    # Procesar factura
    print("Procesando factura...")
    print(f"  XML: {xml_path}")
    print(f"  PDF: {pdf_path}")
    print()
    
    try:
        # Extraer datos
        print("1. Extrayendo texto de XML y PDF...")
        data = extractor.extract_combined(xml_path, pdf_path)
        
        print(f"   ✅ XML: {len(data['xml_text'])} caracteres (calidad: {data['xml_quality']:.0%})")
        print(f"   ✅ PDF: {len(data['pdf_text'])} caracteres")
        print(f"   ⚖️  Peso XML: {data['xml_weight']:.0%}")
        print(f"   ⚖️  Peso PDF: {data['pdf_weight']:.0%}")
        print()
        
        # Clasificar
        print("2. Clasificando factura...")
        sucursal, unidad = classifier.classify(
            data['text'],
            xml_weight=data['xml_weight'],
            pdf_weight=data['pdf_weight']
        )
        
        result = {
            'clasificacion': {
                'sucursal': sucursal,
                'unidad_funcional': unidad
            },
            'metadata': {
                'xml_quality': data['xml_quality'],
                'xml_weight': data['xml_weight'],
                'pdf_weight': data['pdf_weight'],
                'has_xml': data['has_xml'],
                'has_pdf': data['has_pdf']
            },
            'texto_extraido': {
                'xml': data['xml_text'][:500] + '...' if len(data['xml_text']) > 500 else data['xml_text'],
                'pdf': data['pdf_text'][:500] + '...' if len(data['pdf_text']) > 500 else data['pdf_text']
            }
        }
        
        # Mostrar resultados
        print("=" * 80)
        print("RESULTADOS DE LA EXTRACCIÓN Y CLASIFICACIÓN")
        print("=" * 80)
        print()
        
        # Sucursal
        print("🏢 SUCURSAL:")
        if sucursal['success']:
            print(f"   ✅ DETECTADA: {sucursal['nombre']}")
            print(f"   📊 Score: {sucursal['score']}")
            print(f"   🔑 Keywords: {', '.join(sucursal['keywords'][:5])}")
        else:
            print("   ❌ No detectada")
        print()
        
        # Unidad Funcional
        print("📦 UNIDAD FUNCIONAL:")
        if unidad['success']:
            print(f"   ✅ DETECTADA: {unidad['nombre']}")
            print(f"   📊 Score: {unidad['score']}")
            print(f"   🔑 Keywords: {', '.join(unidad['keywords'][:5])}")
        else:
            print("   ❌ No detectada")
        print()
        
        # Metadata
        print("📊 METADATA:")
        print(f"   XML Quality: {data['xml_quality']:.0%}")
        print(f"   XML Weight: {data['xml_weight']:.0%}")
        print(f"   PDF Weight: {data['pdf_weight']:.0%}")
        print(f"   Has XML: {'✅' if data['has_xml'] else '❌'}")
        print(f"   Has PDF: {'✅' if data['has_pdf'] else '❌'}")
        print()
        
        # Muestra de texto extraído
        print("� MUEASTRA DE TEXTO EXTRAÍDO (primeros 300 caracteres):")
        print("   XML:")
        print(f"   {data['xml_text'][:300]}...")
        print()
        print("   PDF:")
        print(f"   {data['pdf_text'][:300]}...")
        print()
        
        # Resumen para API
        print("=" * 80)
        print("RESUMEN JSON")
        print("=" * 80)
        summary = {
            'success': sucursal['success'] and unidad['success'],
            'sucursal': sucursal if sucursal['success'] else None,
            'unidad_funcional': unidad if unidad['success'] else None,
            'metadata': result['metadata']
        }
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
