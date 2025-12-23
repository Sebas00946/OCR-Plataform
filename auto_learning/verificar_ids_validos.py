"""
Script para verificar qué IDs de sucursales y unidades funcionales existen
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
print("VERIFICACIÓN DE IDs VÁLIDOS")
print("=" * 80)
print()

try:
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    # Listar sucursales
    print("📍 SUCURSALES DISPONIBLES:")
    print("-" * 80)
    cursor.execute("""
        SELECT id, nombre, activo
        FROM sucursales
        ORDER BY id
    """)
    
    sucursales = cursor.fetchall()
    for row in sucursales:
        estado = "✅" if row[2] else "❌"
        print(f"   {estado} ID {row[0]}: {row[1]}")
    
    print()
    print(f"Total: {len(sucursales)} sucursales")
    print()
    
    # Listar unidades funcionales
    print("🏢 UNIDADES FUNCIONALES DISPONIBLES:")
    print("-" * 80)
    cursor.execute("""
        SELECT id, nombre, activo
        FROM unidades_funcionales
        ORDER BY id
    """)
    
    unidades = cursor.fetchall()
    for row in unidades:
        estado = "✅" if row[2] else "❌"
        print(f"   {estado} ID {row[0]}: {row[1]}")
    
    print()
    print(f"Total: {len(unidades)} unidades funcionales")
    print()
    
    # Verificar el mapeo actual
    print("=" * 80)
    print("VERIFICACIÓN DEL MAPEO ACTUAL")
    print("=" * 80)
    print()
    
    FOLDER_MAPPING = {
        "1. NEIVA/1.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 4, "unidad_id": 7},
    }
    
    for folder, mapping in FOLDER_MAPPING.items():
        print(f"📁 {folder}")
        
        # Verificar sucursal
        cursor.execute("SELECT nombre FROM sucursales WHERE id = %s", (mapping['sucursal_id'],))
        sucursal = cursor.fetchone()
        if sucursal:
            print(f"   ✅ Sucursal ID {mapping['sucursal_id']}: {sucursal[0]}")
        else:
            print(f"   ❌ Sucursal ID {mapping['sucursal_id']}: NO EXISTE")
        
        # Verificar unidad
        cursor.execute("SELECT nombre FROM unidades_funcionales WHERE id = %s", (mapping['unidad_id'],))
        unidad = cursor.fetchone()
        if unidad:
            print(f"   ✅ Unidad ID {mapping['unidad_id']}: {unidad[0]}")
        else:
            print(f"   ❌ Unidad ID {mapping['unidad_id']}: NO EXISTE")
        
        print()
    
    # Sugerencias de mapeo correcto
    print("=" * 80)
    print("SUGERENCIAS DE MAPEO CORRECTO")
    print("=" * 80)
    print()
    
    print("Basado en los IDs disponibles, el mapeo debería ser:")
    print()
    
    # Buscar Neiva
    cursor.execute("SELECT id, nombre FROM sucursales WHERE nombre ILIKE '%neiva%'")
    neiva = cursor.fetchone()
    if neiva:
        print(f"📍 Neiva: ID {neiva[0]} ({neiva[1]})")
        
        # Buscar unidades de Neiva
        cursor.execute("""
            SELECT id, nombre 
            FROM unidades_funcionales 
            WHERE nombre ILIKE '%neiva%' OR nombre ILIKE '%nva%'
            ORDER BY id
        """)
        unidades_neiva = cursor.fetchall()
        if unidades_neiva:
            print(f"   Unidades funcionales disponibles:")
            for u in unidades_neiva:
                print(f"      • ID {u[0]}: {u[1]}")
        print()
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
