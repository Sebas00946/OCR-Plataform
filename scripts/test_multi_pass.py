"""
Script para probar el sistema de clasificación multi-pasada
"""
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from extractor import InvoiceExtractor
from multi_pass_classifier import MultiPassClassifier

load_dotenv()

# Configuración de BD
db_config = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

def test_factura(xml_path, pdf_path=None, nombre_factura=""):
    """
    Prueba el sistema multi-pasada con una factura
    """
    print("\n" + "=" * 80)
    print(f"PRUEBA: {nombre_factura}")
    print("=" * 80)
    
    # 1. Extraer datos
    print("\n1️⃣ EXTRACCIÓN DE DATOS")
    print("-" * 80)
    
    extractor = InvoiceExtractor()
    result = extractor.extract_combined(xml_path=xml_path, pdf_path=pdf_path)
    
    proveedor = result.get('proveedor', {})
    factura = result.get('factura', {})
    cliente = result.get('cliente', {})
    
    print(f"Proveedor: {proveedor.get('nombre', 'N/A')}")
    print(f"Factura: {factura.get('numero', 'N/A')}")
    print(f"Cliente: {cliente.get('nombre', 'N/A')}")
    print(f"Dirección: {cliente.get('direccion', 'N/A')}")
    
    # 2. Clasificar con sistema multi-pasada
    print("\n2️⃣ CLASIFICACIÓN MULTI-PASADA")
    print("-" * 80)
    
    classifier = MultiPassClassifier(db_config)
    
    # Preparar datos para el clasificador
    xml_data = {
        'proveedor': proveedor,
        'factura': factura,
        'cliente': cliente
    }
    pdf_text = result.get('text', '')
    
    sucursal_result, unidad_result = classifier.classify(xml_data, pdf_text)
    
    # 3. Mostrar resultados
    print("\n📍 SUCURSAL:")
    if sucursal_result['success']:
        print(f"   ✅ {sucursal_result['nombre']}")
        print(f"   Confianza: {sucursal_result['confidence']*100:.1f}%")
        print(f"   Score: {sucursal_result['score']}")
        print(f"   Contexto: {sucursal_result.get('context', {}).get('ciudad', 'N/A')}")
        if sucursal_result.get('requires_validation'):
            print(f"   ⚠️  REQUIERE VALIDACIÓN")
    else:
        print(f"   ❌ No clasificado")
    
    print("\n🏢 UNIDAD FUNCIONAL:")
    if unidad_result['success']:
        print(f"   ✅ {unidad_result['nombre']}")
        print(f"   Confianza: {unidad_result['confidence']*100:.1f}%")
        print(f"   Score: {unidad_result['score']}")
        print(f"   Keywords: {', '.join(unidad_result['keywords'][:5])}")
        if unidad_result.get('semantic_matches'):
            print(f"   Patrones: {', '.join(unidad_result['semantic_matches'][:3])}")
        if unidad_result.get('requires_validation'):
            print(f"   ⚠️  REQUIERE VALIDACIÓN")
        
        # Mostrar alternativas si existen
        if unidad_result.get('alternatives'):
            print(f"\n   Alternativas:")
            for alt in unidad_result['alternatives']:
                print(f"      • {alt['nombre']} (confianza: {alt['confidence']*100:.1f}%, score: {alt['score']})")
    else:
        print(f"   ❌ No clasificado")
        print(f"   Razón: {unidad_result.get('reason', 'Desconocida')}")
    
    # 4. Comparación con sistema anterior
    print("\n3️⃣ COMPARACIÓN CON SISTEMA ANTERIOR")
    print("-" * 80)
    
    from classifier import PDFClassifier
    old_classifier = PDFClassifier(db_config)
    old_sucursal, old_unidad = old_classifier.classify(pdf_text)
    
    print(f"Sistema Anterior:")
    print(f"   Sucursal: {old_sucursal.get('nombre', 'N/A')} (score: {old_sucursal.get('score', 0)})")
    print(f"   Unidad: {old_unidad.get('nombre', 'N/A')} (score: {old_unidad.get('score', 0)})")
    
    print(f"\nSistema Multi-Pasada:")
    print(f"   Sucursal: {sucursal_result.get('nombre', 'N/A')} (confianza: {sucursal_result.get('confidence', 0)*100:.1f}%)")
    print(f"   Unidad: {unidad_result.get('nombre', 'N/A')} (confianza: {unidad_result.get('confidence', 0)*100:.1f}%)")
    
    # Verificar si cambió
    if old_sucursal.get('nombre') != sucursal_result.get('nombre'):
        print(f"\n   🔄 CAMBIO EN SUCURSAL:")
        print(f"      Antes: {old_sucursal.get('nombre', 'N/A')}")
        print(f"      Ahora: {sucursal_result.get('nombre', 'N/A')}")
    
    if old_unidad.get('nombre') != unidad_result.get('nombre'):
        print(f"\n   🔄 CAMBIO EN UNIDAD:")
        print(f"      Antes: {old_unidad.get('nombre', 'N/A')}")
        print(f"      Ahora: {unidad_result.get('nombre', 'N/A')}")
    
    return sucursal_result, unidad_result

def main():
    """
    Prueba el sistema con las facturas de ejemplo
    """
    print("=" * 80)
    print("PRUEBA DEL SISTEMA DE CLASIFICACIÓN MULTI-PASADA")
    print("=" * 80)
    
    # Factura 1: FQE142584 (FARMAQUIRURGICOS - Neiva)
    test_factura(
        xml_path="ejemplos/FQE142584/ad09004334370002500036584.xml",
        pdf_path="ejemplos/FQE142584/FQE142584.pdf",
        nombre_factura="FQE142584 - FARMAQUIRURGICOS JM SAS"
    )
    
    # Factura 2: FEV306 (CENTRO SURCOLOMBIANO - Neiva)
    test_factura(
        xml_path="ejemplos/z09014892770082600000002/ad09014892770082600000002.xml",
        pdf_path="ejemplos/z09014892770082600000002/fv09014892770082600000002.pdf",
        nombre_factura="FEV306 - CENTRO SURCOLOMBIANO"
    )
    
    # Factura 3: 580831408695 (MOVISTAR - Neiva) - La que fallaba
    test_factura(
        xml_path="ejemplos/8130019520025/XML_580831408695.xml",
        pdf_path="ejemplos/8130019520025/RepGrafica_580831408695.pdf",
        nombre_factura="580831408695 - MOVISTAR (Caso problemático)"
    )
    
    print("\n" + "=" * 80)
    print("✅ PRUEBAS COMPLETADAS")
    print("=" * 80)

if __name__ == "__main__":
    main()
