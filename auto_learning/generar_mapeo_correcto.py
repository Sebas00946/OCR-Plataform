"""
Script para generar el FOLDER_MAPPING correcto
basado en los IDs reales de sucursales y unidades funcionales
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
print("GENERADOR DE FOLDER_MAPPING CORRECTO")
print("=" * 80)
print()

try:
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    # Obtener todas las sucursales y unidades
    cursor.execute("SELECT id, nombre FROM sucursales WHERE activo = true ORDER BY id")
    sucursales = {row[1]: row[0] for row in cursor.fetchall()}
    
    cursor.execute("SELECT id, nombre FROM unidades_funcionales WHERE activo = true ORDER BY id")
    unidades = {row[1]: row[0] for row in cursor.fetchall()}
    
    print("📍 Sucursales disponibles:")
    for nombre, id in sucursales.items():
        print(f"   ID {id}: {nombre}")
    print()
    
    print("🏢 Unidades funcionales disponibles:")
    for nombre, id in unidades.items():
        print(f"   ID {id}: {nombre}")
    print()
    
    # Generar mapeo sugerido
    print("=" * 80)
    print("FOLDER_MAPPING SUGERIDO")
    print("=" * 80)
    print()
    print("FOLDER_MAPPING = {")
    
    # NEIVA
    neiva_id = sucursales.get('Clinica Medilaser S.A.S - Neiva')
    if neiva_id:
        print(f"    # NEIVA (ID {neiva_id})")
        
        # 1.1. PROVEEDORES MEDICOS E IPS → Administración
        admin_nva = unidades.get('Administración - NVA')
        if admin_nva:
            print(f'    "1. NEIVA/1.1. PROVEEDORES MEDICOS E IPS": {{"sucursal_id": {neiva_id}, "unidad_id": {admin_nva}}},  # Neiva - Administración')
        
        # 1.2. PROVEEDORES MEDICAMENTOS → Almacén
        almacen_nva = unidades.get('Almacén - NVA')
        if almacen_nva:
            print(f'    "1. NEIVA/1.2. PROVEEDORES MEDICAMENTOS": {{"sucursal_id": {neiva_id}, "unidad_id": {almacen_nva}}},  # Neiva - Almacén')
        
        # 1.3. GASTOS → Administración
        if admin_nva:
            print(f'    "1. NEIVA/1.3. GASTOS": {{"sucursal_id": {neiva_id}, "unidad_id": {admin_nva}}},  # Neiva - Administración')
        print()
    
    # TUNJA
    tunja_id = sucursales.get('Clinica Medilaser S.A.S - Tunja')
    if tunja_id:
        print(f"    # TUNJA (ID {tunja_id})")
        
        admin_tja = unidades.get('Administración - TJA')
        almacen_tja = unidades.get('Almacén - TJA')
        
        if admin_tja:
            print(f'    "2. TUNJA/2.1. PROVEEDORES MEDICOS E IPS": {{"sucursal_id": {tunja_id}, "unidad_id": {admin_tja}}},  # Tunja - Administración')
        if almacen_tja:
            print(f'    "2. TUNJA/2.2. PROVEEDORES MEDICAMENTOS": {{"sucursal_id": {tunja_id}, "unidad_id": {almacen_tja}}},  # Tunja - Almacén')
        if admin_tja:
            print(f'    "2. TUNJA/2.3. GASTOS": {{"sucursal_id": {tunja_id}, "unidad_id": {admin_tja}}},  # Tunja - Administración')
        print()
    
    # FLORENCIA
    florencia_id = sucursales.get('Clinica Medilaser S.A.S - Florencia')
    if florencia_id:
        print(f"    # FLORENCIA (ID {florencia_id})")
        
        admin_fla = unidades.get('Administración - FLA')
        almacen_fla = unidades.get('Almacén - FLA')
        
        if admin_fla:
            print(f'    "3. FLORENCIA/3.1. PROVEEDORES MEDICOS E IPS": {{"sucursal_id": {florencia_id}, "unidad_id": {admin_fla}}},  # Florencia - Administración')
        if almacen_fla:
            print(f'    "3. FLORENCIA/3.2. PROVEEDORES MEDICAMENTOS": {{"sucursal_id": {florencia_id}, "unidad_id": {almacen_fla}}},  # Florencia - Almacén')
        if admin_fla:
            print(f'    "3. FLORENCIA/3.3. GASTOS": {{"sucursal_id": {florencia_id}, "unidad_id": {admin_fla}}},  # Florencia - Administración')
        print()
    
    # PITALITO
    pitalito_id = sucursales.get('Clinica Medilaser S.A.S - Pitalito')
    if pitalito_id:
        print(f"    # PITALITO (ID {pitalito_id})")
        
        almacen_pto = unidades.get('Almacén - PTO')
        
        # No hay Administración - PTO, usar la que exista
        if almacen_pto:
            print(f'    "4. PITALITO/4.1. PROVEEDORES MEDICOS E IPS": {{"sucursal_id": {pitalito_id}, "unidad_id": {almacen_pto}}},  # Pitalito - Almacén (no hay Admin)')
            print(f'    "4. PITALITO/4.2. PROVEEDORES MEDICAMENTOS": {{"sucursal_id": {pitalito_id}, "unidad_id": {almacen_pto}}},  # Pitalito - Almacén')
            print(f'    "4. PITALITO/4.3. GASTOS": {{"sucursal_id": {pitalito_id}, "unidad_id": {almacen_pto}}},  # Pitalito - Almacén (no hay Admin)')
        print()
    
    # FACATATIVA (BOGOTA?)
    facatativa_id = sucursales.get('Clinica Medilaser S.A.S - Facatativa')
    if facatativa_id:
        print(f"    # FACATATIVA/BOGOTA (ID {facatativa_id})")
        
        admin_kta = unidades.get('Administración - KTA')
        almacen_kta = unidades.get('Almacén - KTA')
        
        if admin_kta:
            print(f'    "5. BOGOTA/5.1. PROVEEDORES MEDICOS E IPS": {{"sucursal_id": {facatativa_id}, "unidad_id": {admin_kta}}},  # Facatativa - Administración')
        if almacen_kta:
            print(f'    "5. BOGOTA/5.2. PROVEEDORES MEDICAMENTOS": {{"sucursal_id": {facatativa_id}, "unidad_id": {almacen_kta}}},  # Facatativa - Almacén')
        if admin_kta:
            print(f'    "5. BOGOTA/5.3. GASTOS": {{"sucursal_id": {facatativa_id}, "unidad_id": {admin_kta}}},  # Facatativa - Administración')
        print()
    
    print("}")
    print()
    
    print("=" * 80)
    print("NOTAS IMPORTANTES")
    print("=" * 80)
    print()
    print("⚠️  Verifica los nombres de las carpetas en el buzón de correo")
    print("⚠️  Algunos nombres pueden tener espacios diferentes")
    print("⚠️  Pitalito solo tiene Almacén, no tiene Administración")
    print("⚠️  Facatativa aparece como 'BOGOTA' en las carpetas")
    print()
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
