"""
Script de prueba que muestra el procesamiento de subcarpetas (proveedores)
Procesa 20 correos para ver el detalle
"""
import sys
from pathlib import Path

# Modificar el script principal temporalmente
import auto_learning_from_mailbox as al

# Cambiar tamaño de lote para prueba
al.BATCH_SIZE = 20
al.MAX_WORKERS = 5

# Mapeo de prueba
TEST_FOLDER_MAPPING = {
    "1. NEIVA/1.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 4, "unidad_id": 7},
}

class TestProcessorWithSubfolders(al.AutoLearningProcessor):
    """Procesador de prueba que muestra subcarpetas"""
    
    def load_progress(self):
        """Ignorar progreso anterior"""
        return {'processed_folders': {}, 'last_folder': None}
    
    def get_all_subfolders_recursive(self, parent_folder_id, max_depth=10, current_depth=0):
        """Limitar a 10 subcarpetas para prueba"""
        all_subfolders = al.AutoLearningProcessor.get_all_subfolders_recursive(
            self, parent_folder_id, max_depth, current_depth
        )
        
        # Limitar a 10 subcarpetas para prueba rápida
        limited = all_subfolders[:10]
        
        if current_depth == 0 and len(all_subfolders) > 10:
            print(f"\n   ⚠️  MODO PRUEBA: Limitado a {len(limited)} subcarpetas (de {len(all_subfolders)} totales)")
            self.log(f"MODO PRUEBA: Procesando solo {len(limited)} subcarpetas")
        
        return limited
    
    def get_emails_from_folder_and_subfolders(self, folder_id, start_date="2025-01-01"):
        """Obtener correos y limitar a 20 para prueba"""
        # Llamar al método padre
        all_emails = al.AutoLearningProcessor.get_emails_from_folder_and_subfolders(
            self, folder_id, start_date
        )
        
        # Limitar a 20 correos para prueba
        limited = all_emails[:20]
        
        if len(all_emails) > 20:
            print(f"\n   ⚠️  MODO PRUEBA: Limitado a {len(limited)} correos (de {len(all_emails)} totales)")
            self.log(f"MODO PRUEBA: Procesando solo {len(limited)} correos")
        
        return limited
    
    def run(self):
        """Ejecuta el procesamiento de prueba"""
        print("=" * 80)
        print("PRUEBA CON SUBCARPETAS (20 CORREOS)")
        print("=" * 80)
        print()
        print(f"Buzón: {al.SHARED_MAILBOX}")
        print(f"Carpeta: 1. NEIVA/1.1. PROVEEDORES MEDICOS E IPS")
        print(f"Workers: 5")
        print(f"Objetivo: Ver procesamiento de subcarpetas de proveedores")
        print()
        print("💡 LEYENDA:")
        print("   ✅ = Clasificación correcta (refuerza keywords)")
        print("   ❌ = Clasificación incorrecta (APRENDE y crea keywords)")
        print("   ⏭️  = Saltado (duplicado)")
        print("   ⚠️  = Error técnico")
        print()
        print("   Los ❌ NO son errores. El sistema aprende de ellos.")
        print()
        
        # Obtener token
        print("🔑 Obteniendo token de acceso...")
        if not self.get_access_token():
            print("❌ ERROR: No se pudo obtener token")
            return
        
        print("✅ Token obtenido\n")
        
        # Procesar carpeta
        for folder_path, classification in TEST_FOLDER_MAPPING.items():
            self.process_folder(folder_path, classification)
        
        # Resumen
        print("\n" + "=" * 80)
        print("RESUMEN DE PRUEBA")
        print("=" * 80)
        print(f"Total procesados: {self.results['total_processed']}")
        print(f"✅ Correctos: {self.results['successful']}")
        print(f"❌ Incorrectos: {self.results['failed']}")
        print(f"⏭️  Saltados: {self.results['skipped']}")
        print()
        print("💡 AUTO-APRENDIZAJE:")
        print(f"   • {self.results['successful']} correos reforzaron keywords existentes")
        print(f"   • {self.results['failed']} correos crearon/actualizaron keywords nuevas")
        print(f"   • Total aprendizajes: {self.results['successful'] + self.results['failed']}")
        print()
        print("📚 Verifica que las keywords se guardaron en BD:")
        print("   SELECT s.nombre, COUNT(*) as keywords")
        print("   FROM ocr_sucursal_keywords k")
        print("   JOIN sucursales s ON s.id = k.sucursal_id")
        print("   WHERE k.activo = true")
        print("   GROUP BY s.nombre;")
        print()
        
        if self.results['errors']:
            print("⚠️  ERRORES ENCONTRADOS:")
            for error in self.results['errors'][:5]:
                print(f"   - {error.get('error', 'Unknown')}")
            if len(self.results['errors']) > 5:
                print(f"   ... y {len(self.results['errors']) - 5} más")
            print()
        
        print("✅ Prueba completada")
        print()
        print("Si todo se ve bien, ejecuta el procesamiento completo:")
        print("   python auto_learning/auto_learning_from_mailbox.py")
        print()


if __name__ == "__main__":
    processor = TestProcessorWithSubfolders()
    processor.run()
