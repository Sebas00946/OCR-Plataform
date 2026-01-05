"""
Script para analizar keywords duplicadas entre unidades funcionales
Identifica keywords que están causando conflictos en la clasificación
"""
import sys
from pathlib import Path
import psycopg2
import psycopg2.extras
from collections import defaultdict
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

def analizar_keywords_duplicadas():
    """
    Analiza keywords que están en múltiples unidades funcionales
    """
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print("=" * 80)
    print("ANÁLISIS DE KEYWORDS DUPLICADAS")
    print("=" * 80)
    
    # 1. Keywords duplicadas entre unidades
    print("\n📊 KEYWORDS COMPARTIDAS ENTRE UNIDADES FUNCIONALES:")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            uk.keyword,
            COUNT(DISTINCT uk.unidad_funcional_id) as num_unidades,
            STRING_AGG(DISTINCT uf.nombre, ', ' ORDER BY uf.nombre) as unidades,
            AVG(uk.peso) as peso_promedio
        FROM ocr_unidad_keywords uk
        JOIN unidades_funcionales uf ON uf.id = uk.unidad_funcional_id
        WHERE uk.activo = TRUE
        GROUP BY uk.keyword
        HAVING COUNT(DISTINCT uk.unidad_funcional_id) > 1
        ORDER BY num_unidades DESC, peso_promedio DESC
        LIMIT 50
    """)
    
    duplicadas = cursor.fetchall()
    
    if duplicadas:
        print(f"\n⚠️  Encontradas {len(duplicadas)} keywords duplicadas (mostrando top 50):\n")
        for row in duplicadas:
            print(f"Keyword: '{row['keyword']}'")
            print(f"  Unidades: {row['num_unidades']}")
            print(f"  Peso promedio: {row['peso_promedio']:.1f}")
            print(f"  En: {row['unidades']}")
            print()
    else:
        print("✅ No hay keywords duplicadas")
    
    # 2. Keywords genéricas (muy comunes)
    print("\n" + "=" * 80)
    print("🔍 KEYWORDS GENÉRICAS (Posiblemente problemáticas):")
    print("-" * 80)
    
    keywords_genericas = [
        'CLIENTE', 'PRODUCTO', 'SERVICIOS', 'VENCIMIENTO', 'FIRMA',
        'ELECTRÓNICA', 'FACTURA', 'TOTAL', 'FECHA', 'CANTIDAD',
        'PRECIO', 'DESCRIPCIÓN', 'CÓDIGO', 'NOMBRE', 'DIRECCIÓN',
        'TELÉFONO', 'EMAIL', 'NIT', 'VALOR', 'IVA'
    ]
    
    cursor.execute("""
        SELECT 
            uk.keyword,
            COUNT(DISTINCT uk.unidad_funcional_id) as num_unidades,
            STRING_AGG(DISTINCT uf.nombre, ', ' ORDER BY uf.nombre) as unidades,
            MAX(uk.peso) as peso_maximo
        FROM ocr_unidad_keywords uk
        JOIN unidades_funcionales uf ON uf.id = uk.unidad_funcional_id
        WHERE uk.activo = TRUE
        AND UPPER(uk.keyword) IN %s
        GROUP BY uk.keyword
        ORDER BY num_unidades DESC, peso_maximo DESC
    """, (tuple(keywords_genericas),))
    
    genericas = cursor.fetchall()
    
    if genericas:
        print(f"\n⚠️  Encontradas {len(genericas)} keywords genéricas en uso:\n")
        for row in genericas:
            print(f"❌ '{row['keyword']}' está en {row['num_unidades']} unidades (peso máx: {row['peso_maximo']})")
            print(f"   {row['unidades']}")
            print()
    
    # 3. Keywords específicas por unidad
    print("\n" + "=" * 80)
    print("✅ KEYWORDS ESPECÍFICAS (Únicas por unidad):")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            uf.nombre as unidad,
            COUNT(*) as total_keywords,
            COUNT(*) FILTER (WHERE uk.keyword IN (
                SELECT keyword 
                FROM ocr_unidad_keywords 
                WHERE activo = TRUE
                GROUP BY keyword 
                HAVING COUNT(DISTINCT unidad_funcional_id) = 1
            )) as keywords_unicas,
            ROUND(100.0 * COUNT(*) FILTER (WHERE uk.keyword IN (
                SELECT keyword 
                FROM ocr_unidad_keywords 
                WHERE activo = TRUE
                GROUP BY keyword 
                HAVING COUNT(DISTINCT unidad_funcional_id) = 1
            )) / COUNT(*), 1) as porcentaje_unicas
        FROM ocr_unidad_keywords uk
        JOIN unidades_funcionales uf ON uf.id = uk.unidad_funcional_id
        WHERE uk.activo = TRUE
        GROUP BY uf.nombre
        ORDER BY porcentaje_unicas DESC
    """)
    
    especificas = cursor.fetchall()
    
    print()
    for row in especificas:
        porcentaje = row['porcentaje_unicas']
        emoji = "✅" if porcentaje >= 80 else "⚠️" if porcentaje >= 50 else "❌"
        print(f"{emoji} {row['unidad']}")
        print(f"   Total: {row['total_keywords']} | Únicas: {row['keywords_unicas']} ({porcentaje}%)")
    
    # 4. Recomendaciones
    print("\n" + "=" * 80)
    print("💡 RECOMENDACIONES:")
    print("-" * 80)
    
    num_duplicadas = len(duplicadas)
    num_genericas = len(genericas)
    
    if num_duplicadas > 20 or num_genericas > 5:
        print("\n❌ PROBLEMA CRÍTICO:")
        print(f"   • {num_duplicadas} keywords duplicadas")
        print(f"   • {num_genericas} keywords genéricas")
        print("\n   Acciones recomendadas:")
        print("   1. Eliminar keywords genéricas (CLIENTE, PRODUCTO, etc.)")
        print("   2. Usar keywords específicas del contexto de cada unidad")
        print("   3. Aumentar peso de keywords específicas de ciudad/sucursal")
        print("   4. Implementar sistema de contexto (grafo de relaciones)")
    elif num_duplicadas > 10:
        print("\n⚠️  PROBLEMA MODERADO:")
        print(f"   • {num_duplicadas} keywords duplicadas")
        print("\n   Acciones recomendadas:")
        print("   1. Revisar keywords duplicadas y eliminar las menos relevantes")
        print("   2. Priorizar keywords específicas sobre genéricas")
    else:
        print("\n✅ ESTADO ACEPTABLE:")
        print(f"   • Solo {num_duplicadas} keywords duplicadas")
        print("\n   Mantener monitoreo y optimizar cuando sea necesario")
    
    cursor.close()
    conn.close()

def analizar_clasificacion_factura(xml_path):
    """
    Analiza qué keywords están afectando la clasificación de una factura específica
    """
    sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
    from extractor import InvoiceExtractor
    from classifier import PDFClassifier
    
    print("\n" + "=" * 80)
    print("🔍 ANÁLISIS DE CLASIFICACIÓN DE FACTURA")
    print("=" * 80)
    
    # Extraer texto
    extractor = InvoiceExtractor()
    result = extractor.extract_combined(xml_path=xml_path)
    texto = result.get('text', '')
    
    print(f"\n📄 Factura: {result['factura'].get('numero', 'N/A')}")
    print(f"🏢 Proveedor: {result['proveedor'].get('nombre', 'N/A')}")
    print(f"📍 Ciudad cliente: {result['cliente'].get('ciudad', 'N/A')}")
    
    # Clasificar
    classifier = PDFClassifier(db_config)
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Obtener todas las keywords de unidades y ver cuáles coinciden
    cursor.execute("""
        SELECT 
            uk.unidad_funcional_id,
            uf.nombre as unidad_nombre,
            uk.keyword,
            uk.peso
        FROM ocr_unidad_keywords uk
        JOIN unidades_funcionales uf ON uf.id = uk.unidad_funcional_id
        WHERE uk.activo = TRUE
        ORDER BY uk.peso DESC
    """)
    
    keywords_unidades = cursor.fetchall()
    
    # Agrupar por unidad
    matches_por_unidad = defaultdict(lambda: {'keywords': [], 'score': 0})
    
    for row in keywords_unidades:
        keyword = row['keyword'].upper()
        if keyword in texto:
            unidad_id = row['unidad_funcional_id']
            unidad_nombre = row['unidad_nombre']
            matches_por_unidad[unidad_nombre]['keywords'].append({
                'keyword': keyword,
                'peso': row['peso']
            })
            matches_por_unidad[unidad_nombre]['score'] += row['peso']
    
    # Mostrar resultados
    print("\n📊 KEYWORDS QUE COINCIDEN POR UNIDAD:")
    print("-" * 80)
    
    # Ordenar por score
    sorted_unidades = sorted(
        matches_por_unidad.items(),
        key=lambda x: x[1]['score'],
        reverse=True
    )
    
    for unidad_nombre, data in sorted_unidades[:5]:  # Top 5
        print(f"\n🏢 {unidad_nombre}")
        print(f"   Score total: {data['score']}")
        print(f"   Keywords coincidentes: {len(data['keywords'])}")
        
        # Mostrar top keywords
        top_keywords = sorted(data['keywords'], key=lambda x: x['peso'], reverse=True)[:10]
        for kw in top_keywords:
            print(f"      • {kw['keyword']} (peso: {kw['peso']})")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    analizar_keywords_duplicadas()
    
    # Si se proporciona un XML, analizar esa factura específica
    if len(sys.argv) > 1:
        xml_path = sys.argv[1]
        if Path(xml_path).exists():
            analizar_clasificacion_factura(xml_path)
        else:
            print(f"\n⚠️  Archivo no encontrado: {xml_path}")
