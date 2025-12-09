"""
Script para clasificar facturas usando XML + PDF
"""
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_db_config
from src.classifier import PDFClassifier
from src.extractor import InvoiceExtractor


def classify_invoice(xml_path: str = None, pdf_path: str = None):
    """Clasifica una factura usando XML y/o PDF"""
    print(f"\n{'='*80}")
    print(f"📄 CLASIFICANDO FACTURA")
    print(f"{'='*80}")
    
    if xml_path:
        print(f"📋 XML: {xml_path}")
    if pdf_path:
        print(f"📄 PDF: {pdf_path}")
    print()
    
    # Extraer texto de ambos archivos
    extractor = InvoiceExtractor()
    data = extractor.extract_combined(xml_path, pdf_path)
    
    if not data['text']:
        print("❌ No se pudo extraer texto de ningún archivo")
        return
    
    # Mostrar información de extracción
    print("📊 EXTRACCIÓN:")
    if data['has_xml']:
        print(f"   ✅ XML: {len(data['xml_text'])} caracteres (calidad: {data['xml_quality']:.0%})")
        print(f"   ⚖️  Peso XML: {data['xml_weight']:.0%}")
    else:
        print(f"   ⚠️  XML: No disponible")
    
    if data['has_pdf']:
        print(f"   ✅ PDF: {len(data['pdf_text'])} caracteres")
        print(f"   ⚖️  Peso PDF: {data['pdf_weight']:.0%}")
    else:
        print(f"   ⚠️  PDF: No disponible")
    
    print()
    
    # Clasificar
    classifier = PDFClassifier(get_db_config())
    sucursal, unidad = classifier.classify(
        data['text'],
        xml_weight=data['xml_weight'],
        pdf_weight=data['pdf_weight']
    )
    
    # Mostrar resultados
    print("🏢 SUCURSAL:")
    if sucursal['success']:
        print(f"   ✅ DETECTADA: {sucursal['nombre']}")
        print(f"   📊 Score: {sucursal['score']}")
        print(f"   🔑 Keywords: {', '.join(sucursal['keywords'][:5])}")
    else:
        print(f"   ❌ No detectada")
    
    print(f"\n📦 UNIDAD FUNCIONAL:")
    if unidad['success']:
        print(f"   ✅ DETECTADA: {unidad['nombre']}")
        print(f"   📊 Score: {unidad['score']}")
        print(f"   🔑 Keywords: {', '.join(unidad['keywords'][:5])}")
    else:
        print(f"   ❌ No detectada")
    
    # Resumen
    print(f"\n{'='*80}")
    print("RESUMEN")
    print(f"{'='*80}")
    if sucursal['success'] and unidad['success']:
        print(f"✅ CLASIFICACIÓN EXITOSA")
        print(f"   Sucursal: {sucursal['nombre']}")
        print(f"   Unidad: {unidad['nombre']}")
        print(f"   Fuentes: ", end="")
        sources = []
        if data['has_xml']:
            sources.append(f"XML ({data['xml_weight']:.0%})")
        if data['has_pdf']:
            sources.append(f"PDF ({data['pdf_weight']:.0%})")
        print(" + ".join(sources))
    else:
        print(f"⚠️  CLASIFICACIÓN INCOMPLETA")


def main():
    """Procesa facturas desde línea de comandos"""
    if len(sys.argv) < 2:
        print("❌ Uso: python scripts/classify.py <carpeta_factura>")
        print("   Ejemplo: python scripts/classify.py ejemplos/FQE138095")
        return
    
    # Detectar si es carpeta o archivo
    path = Path(sys.argv[1])
    
    if path.is_dir():
        # Buscar XML y PDF en la carpeta
        xml_files = list(path.glob("*.xml"))
        pdf_files = list(path.glob("*.pdf"))
        
        xml_path = str(xml_files[0]) if xml_files else None
        pdf_path = str(pdf_files[0]) if pdf_files else None
        
        if not xml_path and not pdf_path:
            print(f"❌ No se encontraron archivos XML o PDF en {path}")
            return
        
        classify_invoice(xml_path, pdf_path)
    
    elif path.suffix.lower() == '.pdf':
        # Solo PDF
        xml_path = path.with_suffix('.xml')
        if not xml_path.exists():
            # Buscar XML con nombre similar
            xml_candidates = list(path.parent.glob("*.xml"))
            xml_path = str(xml_candidates[0]) if xml_candidates else None
        else:
            xml_path = str(xml_path)
        
        classify_invoice(xml_path, str(path))
    
    elif path.suffix.lower() == '.xml':
        # Solo XML
        pdf_path = path.with_suffix('.pdf')
        if not pdf_path.exists():
            # Buscar PDF con nombre similar
            pdf_candidates = list(path.parent.glob("*.pdf"))
            pdf_path = str(pdf_candidates[0]) if pdf_candidates else None
        else:
            pdf_path = str(pdf_path)
        
        classify_invoice(str(path), pdf_path)
    
    else:
        print(f"❌ Formato no soportado: {path.suffix}")


if __name__ == "__main__":
    main()
