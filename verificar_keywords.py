"""
Verificar que las keywords se guardaron correctamente
"""
import psycopg2
import psycopg2.extras
from src.config import get_db_config

config = get_db_config()
conn = psycopg2.connect(**config)
cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=" * 100)
print("VERIFICANDO KEYWORDS DE ALMACÉN - TJA (ID: 9)")
print("=" * 100)
print()

cursor.execute("""
    SELECT keyword, peso, activo, created_at
    FROM ocr_unidad_keywords
    WHERE unidad_funcional_id = 9
    ORDER BY created_at DESC
    LIMIT 15
""")

keywords = cursor.fetchall()

print(f"Total de keywords: {len(keywords)}")
print()
print("Keywords más recientes:")
print("-" * 100)

for kw in keywords:
    estado = "✅" if kw['activo'] else "❌"
    fecha = kw['created_at'].strftime('%Y-%m-%d %H:%M:%S') if kw['created_at'] else 'N/A'
    print(f"{estado} {kw['keyword']:<40} Peso: {kw['peso']:<3} Creada: {fecha}")

print()
print("=" * 100)
print("VERIFICANDO LOG DE APRENDIZAJE")
print("=" * 100)
print()

cursor.execute("""
    SELECT accion, keyword, peso_nuevo, razon, created_at
    FROM ocr_learning_log
    ORDER BY created_at DESC
    LIMIT 10
""")

logs = cursor.fetchall()

if logs:
    print(f"Últimas {len(logs)} acciones de aprendizaje:")
    print("-" * 100)
    
    for log in logs:
        fecha = log['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{fecha}] {log['accion']}: '{log['keyword']}' → peso {log['peso_nuevo']}")
        print(f"   Razón: {log['razon']}")
        print()
else:
    print("⚠️  No hay registros en el log de aprendizaje aún")
    print("   (La tabla ocr_learning_log puede no estar implementada todavía)")

cursor.close()
conn.close()

print("=" * 100)
print("✅ VERIFICACIÓN COMPLETADA")
print("=" * 100)
