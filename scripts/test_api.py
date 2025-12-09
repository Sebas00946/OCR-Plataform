"""
Script para probar la API localmente
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_db_config
from src.classifier import PDFClassifier
from src.extractor import InvoiceExtractor


def test_classification():
    """Prueba la clasificación con la factura de ejemplo"""
    print("=" * 80)
    print("PRUEBA DE CLASIFICACIÓN XML + PDF")
    print("=" * 80)
    
    # Factura de ejemplo
    xml_path = "ejemplos/z09012928260082500000039/ad09012928260082500000039.xml"
    pdf_path = "ejemplos/z09012928260082500000039/fv09012928260082500000039.pdf"
    
    print(f"\n📋 XML: {xml_path}")
    print(f"📄 PDF: {pdf_path}\n")
    
    # Extraer
    extractor = InvoiceExtractor()
    data = extractor.extract_combined(xml_path, pdf_path)
    
    print("📊 EXTRACCIÓN:")
    print(f"   ✅ XML: {len(data['xml_text'])} caracteres (calidad: {data['xml_quality']:.0%})")
    print(f"   ⚖️  Peso XML: {data['xml_weight']:.0%}")
    print(f"   ✅ PDF: {len(data['pdf_text'])} caracteres")
    print(f"   ⚖️  Peso PDF: {data['pdf_weight']:.0%}")
    print(f"   📝 Texto combinado: {len(data['text'])} caracteres\n")
    
    # Clasificar
    classifier = PDFClassifier(get_db_config())
    sucursal, unidad = classifier.classify(
        data['text'],
        xml_weight=data['xml_weight'],
        pdf_weight=data['pdf_weight']
    )
    
    # Resultados
    print("🏢 SUCURSAL:")
    if sucursal['success']:
        print(f"   ✅ {sucursal['nombre']}")
        print(f"   📊 Score: {sucursal['score']}")
        print(f"   🔑 Keywords: {', '.join(sucursal['keywords'][:5])}")
    else:
        print(f"   ❌ No detectada")
    
    print(f"\n📦 UNIDAD FUNCIONAL:")
    if unidad['success']:
        print(f"   ✅ {unidad['nombre']}")
        print(f"   📊 Score: {unidad['score']}")
        print(f"   🔑 Keywords: {', '.join(unidad['keywords'][:5])}")
    else:
        print(f"   ❌ No detectada")
    
    print(f"\n{'='*80}")
    print("RESULTADO")
    print(f"{'='*80}")
    
    if sucursal['success'] and unidad['success']:
        print(f"✅ CLASIFICACIÓN EXITOSA")
        print(f"   Sucursal: {sucursal['nombre']}")
        print(f"   Unidad: {unidad['nombre']}")
        print(f"   Fuentes: XML ({data['xml_weight']:.0%}) + PDF ({data['pdf_weight']:.0%})")
    else:
        print(f"⚠️  CLASIFICACIÓN INCOMPLETA")
    
    print()


if __name__ == "__main__":
    test_classification()
