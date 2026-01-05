"""
Script para extraer valores de cualquier factura
Uso: python scripts/extraer_valores.py <ruta_xml> [ruta_pdf]
"""
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from extractor import InvoiceExtractor

def extraer_valores(xml_path, pdf_path=None):
    """
    Extrae y muestra los valores de una factura
    """
    extractor = InvoiceExtractor()
    result = extractor.extract_combined(xml_path=xml_path, pdf_path=pdf_path)
    
    proveedor = result.get('proveedor', {})
    factura = result.get('factura', {})
    valores = factura.get('valores', {})
    
    print("\n" + "=" * 80)
    print("EXTRACCIÓN DE VALORES MONETARIOS")
    print("=" * 80)
    
    # Información básica
    print(f"\n📄 FACTURA: {factura.get('numero', 'N/A')}")
    print(f"📅 FECHA: {factura.get('fecha', 'N/A')}")
    print(f"🏢 PROVEEDOR: {proveedor.get('nombre', 'N/A')}")
    print(f"🆔 NIT: {proveedor.get('nit', 'N/A')}")
    
    # Valores
    if valores:
        print("\n" + "-" * 80)
        print("💰 VALORES MONETARIOS")
        print("-" * 80)
        
        # Valor bruto
        if 'subtotal' in valores:
            print(f"\nValor Bruto (Subtotal):     {valores['subtotal_formatted']}")
        
        # IVA
        if 'iva' in valores:
            iva_valor = valores.get('iva', 0)
            if iva_valor > 0:
                print(f"IVA:                        {valores['iva_formatted']}")
            else:
                print(f"IVA:                        $0.00 (No aplica)")
        
        # Total
        if 'total' in valores:
            print(f"Total Factura:              {valores['total_formatted']}")
        
        # Retenciones
        if 'retenciones' in valores and valores['retenciones']:
            print(f"\n{'Retenciones:':<28}")
            for ret in valores['retenciones']:
                nombre = ret['nombre']
                porcentaje = ret['porcentaje']
                valor = ret['valor_formatted']
                print(f"  • {nombre} ({porcentaje}%):".ljust(28) + valor)
            
            print(f"\nTotal Retenciones:          {valores['total_retenciones_formatted']}")
        else:
            print(f"\nRetenciones:                $0.00 (No aplica)")
        
        # Valor neto (destacado)
        if 'valor_neto' in valores:
            print("\n" + "=" * 80)
            print(f"VALOR NETO A PAGAR:         {valores['valor_neto_formatted']}")
            print("=" * 80)
        elif 'total' in valores:
            print("\n" + "=" * 80)
            print(f"VALOR NETO A PAGAR:         {valores['total_formatted']}")
            print("=" * 80)
    else:
        print("\n⚠️  No se pudieron extraer valores monetarios de esta factura")
    
    print()
    
    return valores

def main():
    """
    Punto de entrada del script
    """
    if len(sys.argv) < 2:
        print("\n❌ Error: Debes proporcionar la ruta del archivo XML")
        print("\nUso:")
        print("  python scripts/extraer_valores.py <ruta_xml>")
        print("  python scripts/extraer_valores.py <ruta_xml> <ruta_pdf>")
        print("\nEjemplo:")
        print("  python scripts/extraer_valores.py ejemplos/FQE142584/ad09004334370002500036584.xml")
        print("  python scripts/extraer_valores.py ejemplos/FQE142584/ad09004334370002500036584.xml ejemplos/FQE142584/FQE142584.pdf")
        sys.exit(1)
    
    xml_path = sys.argv[1]
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Verificar que el archivo XML existe
    if not Path(xml_path).exists():
        print(f"\n❌ Error: El archivo XML no existe: {xml_path}")
        sys.exit(1)
    
    # Verificar que el archivo PDF existe (si se proporcionó)
    if pdf_path and not Path(pdf_path).exists():
        print(f"\n⚠️  Advertencia: El archivo PDF no existe: {pdf_path}")
        print("Continuando solo con XML...\n")
        pdf_path = None
    
    # Extraer valores
    try:
        valores = extraer_valores(xml_path, pdf_path)
        
        if valores:
            print("✅ Extracción completada exitosamente")
        else:
            print("⚠️  No se pudieron extraer valores")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error al procesar la factura: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
