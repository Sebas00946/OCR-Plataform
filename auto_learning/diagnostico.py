"""
Script de diagnóstico para entender qué pasó con el auto-aprendizaje
"""
import json
import os
from datetime import datetime

print("=" * 80)
print("DIAGNÓSTICO DE AUTO-APRENDIZAJE")
print("=" * 80)
print()

# Leer archivos
progress_file = "auto_learning_progress.json"
results_file = "auto_learning_results.json"
log_file = "auto_learning.log"

# 1. Progreso
if os.path.exists(progress_file):
    with open(progress_file, 'r') as f:
        progress = json.load(f)
    
    print("📊 PROGRESO:")
    print(f"   Última carpeta procesada: {progress.get('last_folder', 'N/A')}")
    print(f"   Total carpetas procesadas: {len(progress.get('processed_folders', {}))}")
    print()
    
    for folder, count in progress.get('processed_folders', {}).items():
        print(f"   ✅ {folder}")
        print(f"      └─ {count:,} correos procesados")
    print()
else:
    print("⚠️  No hay archivo de progreso")
    print()

# 2. Resultados
if os.path.exists(results_file):
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    print("📈 RESULTADOS:")
    print(f"   Total procesados: {results.get('total_processed', 0):,}")
    print(f"   ✅ Exitosos: {results.get('successful', 0):,}")
    print(f"   ❌ Fallidos: {results.get('failed', 0):,}")
    print(f"   ⏭️  Saltados: {results.get('skipped', 0):,}")
    print()
    
    if results.get('start_time'):
        start = datetime.fromisoformat(results['start_time'])
        print(f"   Inicio: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if results.get('end_time'):
        end = datetime.fromisoformat(results['end_time'])
        print(f"   Fin: {end.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if results.get('start_time'):
            duration = end - start
            print(f"   Duración: {duration.total_seconds() / 3600:.2f} horas")
    print()
    
    # Errores
    if results.get('errors'):
        print(f"⚠️  ERRORES ({len(results['errors'])}):")
        for error in results['errors'][:10]:  # Mostrar solo los primeros 10
            print(f"   • {error.get('folder', 'N/A')}")
            print(f"     └─ {error.get('error', 'N/A')}")
        
        if len(results['errors']) > 10:
            print(f"   ... y {len(results['errors']) - 10} errores más")
        print()
    
    # Por carpeta
    if results.get('by_folder'):
        print("📁 POR CARPETA:")
        for folder, stats in results['by_folder'].items():
            print(f"   {folder}")
            print(f"      Total: {stats.get('total', 0):,}")
            print(f"      ✅ Correctos: {stats.get('correct', 0):,}")
            print(f"      ❌ Incorrectos: {stats.get('incorrect', 0):,}")
            print(f"      ⏭️  Saltados: {stats.get('skipped', 0):,}")
            print(f"      ⚠️  Errores: {stats.get('errors', 0):,}")
        print()
else:
    print("⚠️  No hay archivo de resultados")
    print()

# 3. Log (últimas líneas)
if os.path.exists(log_file):
    print("📝 LOG (últimas 30 líneas):")
    print("-" * 80)
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[-30:]:
            print(line.rstrip())
    
    print("-" * 80)
    print()
else:
    print("⚠️  No hay archivo de log")
    print()

# 4. Análisis
print("=" * 80)
print("🔍 ANÁLISIS:")
print("=" * 80)
print()

if os.path.exists(progress_file):
    with open(progress_file, 'r') as f:
        progress = json.load(f)
    
    processed_folders = progress.get('processed_folders', {})
    
    # Carpetas esperadas
    expected_folders = [
        "1. NEIVA/1.1. PROVEEDORES MEDICOS E IPS",
        "1. NEIVA/1.2. PROVEEDORES MEDICAMENTOS",
        "1. NEIVA/1.3. GASTOS",
        "2. TUNJA/2.1. PROVEEDORES MEDICOS E IPS",
        "2. TUNJA/2.2. PROVEEDORES MEDICAMENTOS",
        "2. TUNJA/2.3. GASTOS",
        "3.FLORENCIA/3.1. PROVEEDORES MEDICOS E IPS",
        "3.FLORENCIA/3.2. PROVEEDORES MEDICAMENTOS",
        "3.FLORENCIA/3.3. GASTOS",
        "4. PITALITO/4.1. PROVEEDORES MEDICOS E IPS",
        "4. PITALITO/4.2. PROVEEDORES MEDICAMENTOS",
        "4. PITALITO/4.3. GASTOS",
        "5. BOGOTA/5.1. PROVEEDORES MEDICOS E IPS",
        "5. BOGOTA/5.2. PROVEEDORES MEDICAMENTOS",
        "5. BOGOTA/5.3. GASTOS",
        "6. FACATATIVA/6.1. PROVEEDORES MEDICOS E IPS",
        "6. FACATATIVA/6.2. PROVEEDORES MEDICAMENTOS",
        "6. FACATATIVA/6.3 GASTOS",
        "7. DUITAMA/7.1. PROVEEDORES MÉDICOS E IPS",
        "7. DUITAMA/7.3. GASTOS",
    ]
    
    missing = [f for f in expected_folders if f not in processed_folders]
    
    if missing:
        print(f"⚠️  Carpetas NO procesadas ({len(missing)}):")
        for folder in missing:
            print(f"   • {folder}")
        print()
        
        print("💡 RECOMENDACIÓN:")
        print("   El script se detuvo después de procesar solo algunas carpetas.")
        print("   Posibles causas:")
        print("   1. Token de acceso expiró")
        print("   2. Error de red o timeout")
        print("   3. El script fue interrumpido")
        print()
        print("   Para continuar:")
        print("   1. Ejecuta: python auto_learning/reset_progress.py")
        print("   2. Selecciona opción 2 (continuar desde donde quedó)")
        print("   3. Ejecuta: python auto_learning/auto_learning_from_mailbox.py")
        print()
    else:
        print("✅ Todas las carpetas fueron procesadas")
        print()

print("=" * 80)
