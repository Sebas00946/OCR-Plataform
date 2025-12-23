"""
Script de prueba para verificar el auto-aprendizaje
Procesa solo 10 correos de una carpeta para validar
"""
import sys
from pathlib import Path

# Modificar el script principal temporalmente
import auto_learning_from_mailbox as al

# Cambiar tamaño de lote a 10 para prueba
al.BATCH_SIZE = 10
al.MAX_WORKERS = 3  # Solo 3 workers para prueba

# Modificar el mapeo para probar solo una carpeta
TEST_FOLDER_MAPPING = {
    "1. NEIVA/1.1. PROVEEDORES MEDICOS E IPS": {"sucursal_id": 4, "unidad_id": 7},  # Neiva - Administración
}

class TestProcessor(al.AutoLearningProcessor):
    """Procesador de prueba que solo procesa 10 correos"""
    
    def load_progress(self):
        """Sobrescribir para ignorar progreso anterior en pruebas"""
        return {'processed_folders': {}, 'last_folder': None}
    
    def get_all_subfolders_recursive(self, parent_folder_id, max_depth=10, current_depth=0):
        """Sobrescribir para limitar subcarpetas en prueba"""
        # Obtener solo las primeras 5 subcarpetas para prueba rápida
        all_subfolders = al.AutoLearningProcessor.get_all_subfolders_recursive(
            self, parent_folder_id, max_depth, current_depth
        )
        
        # Limitar a 5 subcarpetas para prueba
        limited = all_subfolders[:5]
        
        if current_depth == 0 and len(all_subfolders) > 5:
            print(f"   MODO PRUEBA: Limitado a {len(limited)} subcarpetas (de {len(all_subfolders)} totales)")
            self.log(f"MODO PRUEBA: Procesando solo {len(limited)} subcarpetas")
        
        return limited
    
    def get_emails_from_folder_and_subfolders(self, folder_id, start_date="2025-01-01"):
        """Sobrescribir para limitar a 10 correos"""
        # Llamar al método padre usando la clase base directamente
        all_emails = al.AutoLearningProcessor.get_emails_from_folder_and_subfolders(
            self, folder_id, start_date
        )
        
        # Limitar a 10 correos para prueba
        limited = all_emails[:10]
        
        print(f"   MODO PRUEBA: Limitado a {len(limited)} correos (de {len(all_emails)} totales)")
        self.log(f"MODO PRUEBA: Procesando solo {len(limited)} correos")
        
        return limited
    
    def run(self):
        """Ejecuta el procesamiento de prueba"""
        print("=" * 80)
        print("PRUEBA DE AUTO-APRENDIZAJE (10 CORREOS)")
        print("=" * 80)
        print()
        print(f"Buzon: {al.SHARED_MAILBOX}")
        print(f"Carpeta de prueba: 1.1. PROVEEDORES MEDICOS E IPS (Neiva)")
        print(f"Correos a procesar: 10")
        print()
        
        # Obtener token
        print("Obteniendo token de acceso...")
        if not self.get_access_token():
            print("ERROR: No se pudo obtener token")
            return
        
        print("Token obtenido")
        print()
        
        # Procesar solo la carpeta de prueba
        for folder_path, classification in TEST_FOLDER_MAPPING.items():
            self.process_folder(folder_path, classification)
        
        # Resumen
        print("\n" + "=" * 80)
        print("RESUMEN DE PRUEBA")
        print("=" * 80)
        print(f"Total procesados: {self.results['total_processed']}")
        print(f"Exitosos: {self.results['successful']}")
        print(f"Fallidos: {self.results['failed']}")
        print(f"Saltados: {self.results['skipped']}")
        print()
        
        if self.results['errors']:
            print("ERRORES ENCONTRADOS:")
            for error in self.results['errors'][:5]:  # Mostrar primeros 5
                print(f"   - {error.get('error', 'Unknown')}")
            if len(self.results['errors']) > 5:
                print(f"   ... y {len(self.results['errors']) - 5} mas")
            print()
        
        print("Prueba completada")
        print()
        print("Si todo funciona correctamente, ejecuta:")
        print("   python auto_learning_from_mailbox.py")
        print()


if __name__ == "__main__":
    processor = TestProcessor()
    processor.run()
