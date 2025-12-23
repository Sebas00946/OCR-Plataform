"""
Script para verificar que NO hay duplicados en las tablas de keywords
"""
import os
import psycopg2
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

print("=" * 80)
print("VERIFICACIÓN DE DUPLICADOS EN KEYWORDS")
print("=" * 80)
print()

try:
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    # Verificar duplicados en sucursal_keywords
    print("📊 Verificando ocr_sucursal_keywords...")
    cursor.execute("""
        SELECT sucursal_id, keyword, COUNT(*) as duplicados
        FROM ocr_sucursal_keywords
        GROUP BY sucursal_id, keyword
        HAVING COUNT(*) > 1
    """)
    
    duplicados_sucursal = cursor.fetchall()
    
    if duplicados_sucursal:
        print(f"❌ Se encontraron {len(duplicados_sucursal)} duplicados:")
        for row in duplicados_sucursal[:10]:
            print(f"   • Sucursal {row[0]}, keyword '{row[1]}': {row[2]} veces")
    else:
        print("✅ No hay duplicados en ocr_sucursal_keywords")
    
    print()
    
    # Verificar duplicados en unidad_keywords
    print("📊 Verificando ocr_unidad_keywords...")
    cursor.execute("""
        SELECT unidad_funcional_id, keyword, COUNT(*) as duplicados
        FROM ocr_unidad_keywords
        GROUP BY unidad_funcional_id, keyword
        HAVING COUNT(*) > 1
    """)
    
    duplicados_unidad = cursor.fetchall()
    
    if duplicados_unidad:
        print(f"❌ Se encontraron {len(duplicados_unidad)} duplicados:")
        for row in duplicados_unidad[:10]:
            print(f"   • Unidad {row[0]}, keyword '{row[1]}': {row[2]} veces")
    else:
        print("✅ No hay duplicados en ocr_unidad_keywords")
    
    print()
    print("=" * 80)
    print("ESTADÍSTICAS DE KEYWORDS")
    print("=" * 80)
    print()
    
    # Estadísticas de sucursales
    cursor.execute("""
        SELECT s.nombre, COUNT(*) as total_keywords, 
               AVG(k.peso) as peso_promedio,
               MAX(k.peso) as peso_maximo
        FROM ocr_sucursal_keywords k
        JOIN sucursales s ON s.id = k.sucursal_id
        WHERE k.activo = true
        GROUP BY s.nombre
        ORDER BY total_keywords DESC
    """)
    
    print("📊 Keywords por Sucursal:")
    for row in cursor.fetchall():
        print(f"   • {row[0]}: {row[1]} keywords (peso promedio: {float(row[2]):.2f}, máximo: {float(row[3]):.1f})")
    
    print()
    
    # Estadísticas de unidades
    cursor.execute("""
        SELECT u.nombre, COUNT(*) as total_keywords, 
               AVG(k.peso) as peso_promedio,
               MAX(k.peso) as peso_maximo
        FROM ocr_unidad_keywords k
        JOIN unidades_funcionales u ON u.id = k.unidad_funcional_id
        WHERE k.activo = true
        GROUP BY u.nombre
        ORDER BY total_keywords DESC
    """)
    
    print("📊 Keywords por Unidad Funcional:")
    for row in cursor.fetchall():
        print(f"   • {row[0]}: {row[1]} keywords (peso promedio: {float(row[2]):.2f}, máximo: {float(row[3]):.1f})")
    
    print()
    print("=" * 80)
    print("EJEMPLO: KEYWORDS CON MAYOR PESO (MÁS REFORZADAS)")
    print("=" * 80)
    print()
    
    # Keywords más reforzadas de Neiva
    cursor.execute("""
        SELECT keyword, peso, updated_at
        FROM ocr_sucursal_keywords
        WHERE sucursal_id = 4 AND activo = true
        ORDER BY peso DESC, updated_at DESC
        LIMIT 10
    """)
    
    print("🏆 Top 10 keywords de Neiva (más reforzadas):")
    for row in cursor.fetchall():
        print(f"   • '{row[0]}' - peso: {float(row[1]):.1f} (actualizado: {row[2]})")
    
    print()
    
    cursor.close()
    conn.close()
    
    print("✅ Verificación completada")
    print()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
