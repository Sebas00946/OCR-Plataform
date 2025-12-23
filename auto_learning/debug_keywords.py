"""
Script de debug para ver exactamente por qué no se guardan keywords
Procesa 1 solo correo y muestra todos los detalles
"""
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import os
from dotenv import load_dotenv
from learning import LearningSystem

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
print("DEBUG: PRUEBA DE GUARDADO DE KEYWORDS")
print("=" * 80)
print()

# Texto de prueba (simulando una factura de Neiva)
test_text = """
AESTHETIC AND HEALTH S.A.S
NIT: 901842727
Oficina Principal NEIVA
CL 50 A 5 A 47 CA 20 CONJ SOLARIS NEIVA
Email: ginamarcelasalcedorodriguez@gmail.com

REPRESENTACIÓN GRÁFICA
FACTURA ELECTRÓNICA DE VENTA #FAH103
Fecha Generación: 28/11/2025 22:11
Fecha Vencimiento: 02/12/2025
Forma de Pago: CREDITO
Medio de Pago: Transferencia Débito Bancaria

Razón Social: CLINICA MEDILASER SAS
NIT - CC: 813001952
Dirección: CL 11 7 - 70
Ciudad: NEIVA-HUILA
Teléfono: 6088724100

#000008 - ANESTESIOLOGIA - Turnos N y FdS
Subtotal: $3,696,000.00
Total: $3,696,000.00

TOTAL PRODUCTOS: $24,455,964.00
BASE GRAVABLE: $0.00
SUBTOTAL: $24,455,964.00
IVA: $0.00
TOTAL: $24,455,964.00

Notas:
- Dr. German Alirio Villegas Tovar - Nov
"""

print("📄 Texto de prueba:")
print("-" * 80)
print(test_text[:200] + "...")
print("-" * 80)
print()

# Crear sistema de aprendizaje
print("🔧 Creando sistema de aprendizaje...")
try:
    learning = LearningSystem(db_config)
    print("✅ Sistema creado")
except Exception as e:
    print(f"❌ Error creando sistema: {e}")
    exit(1)

print()
print("📚 Intentando guardar keywords...")
print(f"   Sucursal ID: 4 (Neiva)")
print(f"   Unidad ID: 11 (Administración - NVA)")
print()

# Intentar guardar keywords
try:
    learning.reinforce_correct_classification(
        text=test_text,
        sucursal_id=4,
        unidad_id=11  # ID correcto de Administración - NVA
    )
    print()
    print("✅ Método ejecutado sin excepciones")
except Exception as e:
    print(f"❌ Excepción capturada: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("VERIFICACIÓN EN BASE DE DATOS")
print("=" * 80)
print()

# Verificar en BD
import psycopg2

try:
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    # Contar keywords de sucursal
    cursor.execute("""
        SELECT COUNT(*) FROM ocr_sucursal_keywords 
        WHERE sucursal_id = 4 AND activo = true
    """)
    count_sucursal = cursor.fetchone()[0]
    
    # Contar keywords de unidad
    cursor.execute("""
        SELECT COUNT(*) FROM ocr_unidad_keywords 
        WHERE unidad_funcional_id = 11 AND activo = true
    """)
    count_unidad = cursor.fetchone()[0]
    
    print(f"📊 Keywords en BD:")
    print(f"   Sucursal 4 (Neiva): {count_sucursal} keywords")
    print(f"   Unidad 11 (Administración - NVA): {count_unidad} keywords")
    print()
    
    if count_sucursal > 0:
        print("✅ ¡Keywords de sucursal guardadas correctamente!")
        cursor.execute("""
            SELECT keyword, peso, updated_at 
            FROM ocr_sucursal_keywords 
            WHERE sucursal_id = 4 AND activo = true
            ORDER BY updated_at DESC
            LIMIT 10
        """)
        print("\n   Últimas 10 keywords de sucursal:")
        for row in cursor.fetchall():
            print(f"      • {row[0]} (peso: {row[1]}, fecha: {row[2]})")
    else:
        print("❌ No se guardaron keywords de sucursal")
    
    print()
    
    if count_unidad > 0:
        print("✅ ¡Keywords de unidad guardadas correctamente!")
        cursor.execute("""
            SELECT keyword, peso, updated_at 
            FROM ocr_unidad_keywords 
            WHERE unidad_funcional_id = 11 AND activo = true
            ORDER BY updated_at DESC
            LIMIT 10
        """)
        print("\n   Últimas 10 keywords de unidad:")
        for row in cursor.fetchall():
            print(f"      • {row[0]} (peso: {row[1]}, fecha: {row[2]})")
    else:
        print("❌ No se guardaron keywords de unidad")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error verificando BD: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("FIN DEL DEBUG")
print("=" * 80)
