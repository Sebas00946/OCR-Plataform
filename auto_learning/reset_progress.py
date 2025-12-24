"""
Script para resetear el progreso del auto-aprendizaje
Permite volver a procesar todas las carpetas
"""
import json
import os
from datetime import datetime

PROGRESS_FILE = "auto_learning_progress.json"
RESULTS_FILE = "auto_learning_results.json"

print("=" * 80)
print("RESETEAR PROGRESO DE AUTO-APRENDIZAJE")
print("=" * 80)
print()

# Verificar archivos existentes
if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, 'r') as f:
        progress = json.load(f)
    
    print("📊 Progreso actual:")
    print(f"   Carpetas procesadas: {len(progress.get('processed_folders', {}))}")
    for folder, count in progress.get('processed_folders', {}).items():
        print(f"      • {folder}: {count} correos")
    print()
else:
    print("⚠️  No hay archivo de progreso")
    print()

if os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, 'r') as f:
        results = json.load(f)
    
    print("📈 Resultados actuales:")
    print(f"   Total procesados: {results.get('total_processed', 0)}")
    print(f"   Exitosos: {results.get('successful', 0)}")
    print(f"   Fallidos: {results.get('failed', 0)}")
    print(f"   Saltados: {results.get('skipped', 0)}")
    print()

print("⚠️  OPCIONES:")
print("   1. Resetear TODO (empezar desde cero)")
print("   2. Resetear solo carpetas no procesadas (continuar)")
print("   3. Cancelar")
print()

opcion = input("Selecciona una opción (1/2/3): ").strip()

if opcion == "1":
    # Resetear todo
    print("\n🔄 Reseteando TODO...")
    
    # Backup
    if os.path.exists(PROGRESS_FILE):
        backup_name = f"auto_learning_progress_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.rename(PROGRESS_FILE, backup_name)
        print(f"   ✅ Backup de progreso: {backup_name}")
    
    if os.path.exists(RESULTS_FILE):
        backup_name = f"auto_learning_results_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.rename(RESULTS_FILE, backup_name)
        print(f"   ✅ Backup de resultados: {backup_name}")
    
    # Crear archivos limpios
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({'processed_folders': {}, 'last_folder': None}, f, indent=2)
    
    print("\n✅ Progreso reseteado completamente")
    print("   Ahora puedes ejecutar: python auto_learning/auto_learning_from_mailbox.py")

elif opcion == "2":
    # Solo resetear carpetas no procesadas
    print("\n🔄 Manteniendo carpetas ya procesadas...")
    
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
        
        print(f"   ✅ Se mantendrán {len(progress.get('processed_folders', {}))} carpetas procesadas")
        print("   Las demás carpetas se procesarán")
    
    print("\n✅ Listo para continuar")
    print("   Ejecuta: python auto_learning/auto_learning_from_mailbox.py")

else:
    print("\n❌ Cancelado")
    print("   No se realizaron cambios")

print()
