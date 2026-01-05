"""
Demo completo del sistema OCR con extracción de valores
Muestra todas las capacidades del sistema
"""
import sys
from pathlib import Path
import json

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from extractor import InvoiceExtractor
from classifier import PDFClassifier
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de BD
db_config = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

def print_header(title):
    """Imprime un encabezado bonito"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_section(title):
    """Imprime una sección"""
    print(f"\n{title}")
    print("-" * 80)

def demo_completo():
    """
    Demostración completa del sistema
    """
    print_header("🎯 DEMO COMPLETO - SISTEMA OCR MEDILASER")
    print("\nEste demo muestra todas las capacidades del sistema:")
    print("  1. Extracción de datos del proveedor")
    print("  2. Extracción de valores monetarios")
    print("  3. Clasificación automática (sucursal y unidad funcional)")
    print("  4. Generación de JSON estructurado")
    
    # Factura de ejemplo
    XML_PATH = "ejemplos/8130019520025/XML_580831408695.xml"
    PDF_PATH = "ejemplos/8130019520025/RepGrafica_580831408695.pdf"
    
    print(f"\n📁 Procesando factura de ejemplo:")
    print(f"   XML: {XML_PATH}")
    print(f"   PDF: {PDF_PATH}")
    
    # ========================================
    # 1. EXTRACCIÓN
    # ========================================
    print_header("1️⃣ EXTRACCIÓN DE DATOS")
    
    extractor = InvoiceExtractor()
    result = extractor.extract_combined(xml_path=XML_PATH, pdf_path=PDF_PATH)
    
    # Proveedor
    print_section("🏢 DATOS DEL PROVEEDOR")
    proveedor = result.get('proveedor', {})
    print(f"  Nombre:     {proveedor.get('nombre', 'N/A')}")
    print(f"  NIT:        {proveedor.get('nit', 'N/A')}")
    print(f"  Ciudad:     {proveedor.get('ciudad', 'N/A')}")
    print(f"  Dirección:  {proveedor.get('direccion', 'N/A')}")
    print(f"  Teléfono:   {proveedor.get('telefono', 'N/A')}")
    print(f"  Email:      {proveedor.get('email', 'N/A')}")
    
    # Factura
    print_section("📋 DATOS DE LA FACTURA")
    factura = result.get('factura', {})
    print(f"  Número:     {factura.get('numero', 'N/A')}")
    print(f"  Fecha:      {factura.get('fecha', 'N/A')}")
    cufe = factura.get('cufe', 'N/A')
    if cufe != 'N/A':
        print(f"  CUFE:       {cufe[:50]}...")
    else:
        print(f"  CUFE:       N/A")
    
    # Cliente
    print_section("👤 DATOS DEL CLIENTE")
    cliente = result.get('cliente', {})
    print(f"  Nombre:     {cliente.get('nombre', 'N/A')}")
    print(f"  NIT:        {cliente.get('nit', 'N/A')}")
    print(f"  Ciudad:     {cliente.get('ciudad', 'N/A')}")
    print(f"  Dirección:  {cliente.get('direccion', 'N/A')}")
    
    # Valores
    print_section("💰 VALORES MONETARIOS")
    valores = factura.get('valores', {})
    
    if valores:
        print(f"\n  Valor Bruto (Subtotal):     {valores.get('subtotal_formatted', 'N/A')}")
        
        iva = valores.get('iva', 0)
        if iva > 0:
            print(f"  IVA:                        {valores.get('iva_formatted', '$0.00')}")
        else:
            print(f"  IVA:                        $0.00 (No aplica)")
        
        print(f"  Total Factura:              {valores.get('total_formatted', 'N/A')}")
        
        # Retenciones
        retenciones = valores.get('retenciones', [])
        if retenciones:
            print(f"\n  Retenciones:")
            for ret in retenciones:
                print(f"    • {ret['nombre']} ({ret['porcentaje']}%):".ljust(35) + ret['valor_formatted'])
            print(f"\n  Total Retenciones:          {valores.get('total_retenciones_formatted', 'N/A')}")
        else:
            print(f"\n  Retenciones:                $0.00 (No aplica)")
        
        # Valor neto (destacado)
        print(f"\n  {'═' * 76}")
        print(f"  VALOR NETO A PAGAR:         {valores.get('valor_neto_formatted', valores.get('total_formatted', 'N/A'))}")
        print(f"  {'═' * 76}")
    else:
        print("  ⚠️  No se pudieron extraer valores monetarios")
    
    # Calidad de extracción
    print_section("📊 CALIDAD DE EXTRACCIÓN")
    print(f"  Calidad XML:    {result.get('xml_quality', 0) * 100:.1f}%")
    print(f"  Peso XML:       {result.get('xml_weight', 0) * 100:.1f}%")
    print(f"  Peso PDF:       {result.get('pdf_weight', 0) * 100:.1f}%")
    print(f"  Tiene XML:      {'✅ Sí' if result.get('has_xml') else '❌ No'}")
    print(f"  Tiene PDF:      {'✅ Sí' if result.get('has_pdf') else '❌ No'}")
    
    # ========================================
    # 2. CLASIFICACIÓN
    # ========================================
    print_header("2️⃣ CLASIFICACIÓN AUTOMÁTICA")
    
    try:
        classifier = PDFClassifier(db_config)
        texto = result.get('text', '')
        sucursal_result, unidad_result = classifier.classify(texto)
        
        # Sucursal
        print_section("📍 SUCURSAL CLASIFICADA")
        if sucursal_result.get('success'):
            print(f"  Nombre:     {sucursal_result['nombre']}")
            print(f"  Código:     {sucursal_result['codigo']}")
            print(f"  ID:         {sucursal_result['id']}")
            print(f"  Score:      {sucursal_result['score']}")
            print(f"  Keywords:   {', '.join(sucursal_result['keywords'][:5])}")
            if len(sucursal_result['keywords']) > 5:
                print(f"              ... y {len(sucursal_result['keywords']) - 5} más")
        else:
            print("  ⚠️  No se pudo clasificar la sucursal")
        
        # Unidad Funcional
        print_section("🏢 UNIDAD FUNCIONAL CLASIFICADA")
        if unidad_result.get('success'):
            print(f"  Nombre:     {unidad_result['nombre']}")
            print(f"  Código:     {unidad_result['codigo']}")
            print(f"  ID:         {unidad_result['id']}")
            print(f"  Score:      {unidad_result['score']}")
            print(f"  Keywords:   {', '.join(unidad_result['keywords'][:5])}")
            if len(unidad_result['keywords']) > 5:
                print(f"              ... y {len(unidad_result['keywords']) - 5} más")
        else:
            print("  ⚠️  No se pudo clasificar la unidad funcional")
        
    except Exception as e:
        print(f"\n⚠️  Error en clasificación: {e}")
        sucursal_result = None
        unidad_result = None
    
    # ========================================
    # 3. JSON ESTRUCTURADO
    # ========================================
    print_header("3️⃣ RESPUESTA JSON (Como la API)")
    
    # Crear objeto de respuesta
    response = {
        'proveedor': {
            'nombre': proveedor.get('nombre'),
            'nit': proveedor.get('nit'),
            'ciudad': proveedor.get('ciudad'),
            'direccion': proveedor.get('direccion'),
            'telefono': proveedor.get('telefono'),
            'email': proveedor.get('email')
        },
        'factura': {
            'numero': factura.get('numero'),
            'fecha': factura.get('fecha'),
            'cufe': factura.get('cufe'),
            'valores': {
                'subtotal': valores.get('subtotal'),
                'subtotal_formatted': valores.get('subtotal_formatted'),
                'iva': valores.get('iva', 0),
                'iva_formatted': valores.get('iva_formatted', '$0.00'),
                'total': valores.get('total'),
                'total_formatted': valores.get('total_formatted'),
                'retenciones': valores.get('retenciones', []),
                'total_retenciones': valores.get('total_retenciones', 0),
                'total_retenciones_formatted': valores.get('total_retenciones_formatted', '$0.00'),
                'valor_neto': valores.get('valor_neto'),
                'valor_neto_formatted': valores.get('valor_neto_formatted')
            } if valores else None
        },
        'cliente': {
            'nombre': cliente.get('nombre'),
            'nit': cliente.get('nit'),
            'ciudad': cliente.get('ciudad'),
            'direccion': cliente.get('direccion')
        },
        'clasificacion': {
            'sucursal': {
                'id': sucursal_result['id'],
                'nombre': sucursal_result['nombre'],
                'codigo': sucursal_result['codigo'],
                'score': sucursal_result['score']
            } if sucursal_result and sucursal_result.get('success') else None,
            'unidad_funcional': {
                'id': unidad_result['id'],
                'nombre': unidad_result['nombre'],
                'codigo': unidad_result['codigo'],
                'score': unidad_result['score']
            } if unidad_result and unidad_result.get('success') else None
        },
        'metadata': {
            'xml_quality': result.get('xml_quality'),
            'xml_weight': result.get('xml_weight'),
            'pdf_weight': result.get('pdf_weight'),
            'has_xml': result.get('has_xml'),
            'has_pdf': result.get('has_pdf')
        }
    }
    
    print("\n" + json.dumps(response, indent=2, ensure_ascii=False))
    
    # ========================================
    # 4. RESUMEN
    # ========================================
    print_header("4️⃣ RESUMEN DE CAPACIDADES")
    
    print("\n✅ Extracción de Datos:")
    print("   • Proveedor (nombre, NIT, ciudad, dirección, teléfono, email)")
    print("   • Factura (número, fecha, CUFE)")
    print("   • Cliente (nombre, NIT, ciudad, dirección)")
    
    print("\n✅ Extracción de Valores Monetarios:")
    print("   • Valor Bruto / Subtotal")
    print("   • IVA (Impuesto al Valor Agregado)")
    print("   • Retenciones (Retefuente, ReteICA, ReteIVA)")
    print("   • Total Retenciones (suma automática)")
    print("   • Valor Neto (valor final a pagar)")
    
    print("\n✅ Clasificación Automática:")
    print("   • Sucursal (con score y keywords)")
    print("   • Unidad Funcional (con score y keywords)")
    
    print("\n✅ Formatos Soportados:")
    print("   • XML (Factura Electrónica DIAN)")
    print("   • PDF (complementario)")
    print("   • AttachedDocument con Invoice embebido")
    print("   • Invoice directo")
    
    print("\n✅ Integración:")
    print("   • API REST lista para usar")
    print("   • JSON estructurado")
    print("   • Compatible con Node.js")
    
    print_header("✅ DEMO COMPLETADO")
    print("\n🎉 El sistema está funcionando correctamente")
    print("\n📚 Ver documentación completa en:")
    print("   • EXTRACCION_VALORES_MONETARIOS.md")
    print("   • RESUMEN_EXTRACCION_VALORES.md")
    print("   • README.md")
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    demo_completo()
