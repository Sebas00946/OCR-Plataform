"""
Script de debug para procesar un solo correo y ver errores detallados
"""
import sys
from pathlib import Path
import traceback

# Modificar el script principal temporalmente
import auto_learning_from_mailbox as al

# Cambiar configuración para debug
al.BATCH_SIZE = 1
al.MAX_WORKERS = 1

class DebugProcessor(al.AutoLearningProcessor):
    """Procesador de debug que muestra todos los detalles"""
    
    def load_progress(self):
        """Ignorar progreso anterior"""
        return {'processed_folders': {}, 'last_folder': None}
    
    def get_all_subfolders_recursive(self, parent_folder_id, max_depth=10, current_depth=0):
        """Limitar a 1 subcarpeta para debug"""
        all_subfolders = al.AutoLearningProcessor.get_all_subfolders_recursive(
            self, parent_folder_id, max_depth, current_depth
        )
        return all_subfolders[:1]  # Solo 1 subcarpeta
    
    def get_emails_from_folder_and_subfolders(self, folder_id, start_date="2025-01-01"):
        """Obtener solo 1 correo"""
        all_emails = al.AutoLearningProcessor.get_emails_from_folder_and_subfolders(
            self, folder_id, start_date
        )
        
        if all_emails:
            email = all_emails[0]
            print(f"\n{'='*80}")
            print(f"CORREO SELECCIONADO PARA DEBUG:")
            print(f"{'='*80}")
            print(f"ID: {email.get('id', 'N/A')}")
            print(f"Asunto: {email.get('subject', 'N/A')}")
            print(f"Fecha: {email.get('receivedDateTime', 'N/A')}")
            print(f"Tiene adjuntos: {email.get('hasAttachments', False)}")
            print(f"{'='*80}\n")
        
        return all_emails[:1]
    
    def process_email(self, email, correct_classification, folder_name):
        """Sobrescribir para mostrar detalles completos"""
        print(f"\n{'='*80}")
        print(f"PROCESANDO CORREO CON DEBUG DETALLADO")
        print(f"{'='*80}")
        
        try:
            # Llamar al método padre y capturar resultado
            result = al.AutoLearningProcessor.process_email(
                self, email, correct_classification, folder_name
            )
            
            print(f"\nRESULTADO:")
            print(f"  Status: {result.get('status', 'N/A')}")
            
            if result.get('status') == 'error':
                print(f"  ERROR: {result.get('error', 'N/A')}")
            elif result.get('status') == 'skipped':
                print(f"  Razón: {result.get('reason', 'N/A')}")
            elif result.get('status') in ['correct', 'incorrect']:
                print(f"  Clasificado - Sucursal: {result.get('classified_sucursal', 'N/A')}")
                print(f"  Clasificado - Unidad: {result.get('classified_unidad', 'N/A')}")
                print(f"  Correcto - Sucursal: {result.get('correct_sucursal', 'N/A')}")
                print(f"  Correcto - Unidad: {result.get('correct_unidad', 'N/A')}")
            
            return result
            
        except Exception as e:
            print(f"\nEXCEPCIÓN CAPTURADA:")
            print(f"  Tipo: {type(e).__name__}")
            print(f"  Mensaje: {str(e)}")
            print(f"\nTRACEBACK COMPLETO:")
            traceback.print_exc()
            return {'status': 'error', 'error': str(e)}
    
    def run(self):
        """Ejecuta el procesamiento de debug"""
        print("=" * 80)
        print("DEBUG: PROCESANDO 1 SOLO CORREO CON DETALLES COMPLETOS")
        print("=" * 80)
        print()
        print(f"Buzón: {al.SHARED_MAILBOX}")
        print(f"Carpeta: 1. NEIVA/1.1. PROVEEDORES MEDICOS E IPS")
        print()
        
        # Obtener token
        print("Obteniendo token de acceso...")
        if not self.get_access_token():
            print("ERROR: No se pudo obtener token")
            return
        
        print("✅ Token obtenido\n")
        
        # Procesar solo la primera carpeta
        folder_path = "1. NEIVA/1.1. PROVEEDORES MEDICOS E IPS"
        classification = {"sucursal_id": 4, "unidad_id": 7}
        
        self.process_folder(folder_path, classification)
        
        # Resumen
        print("\n" + "=" * 80)
        print("RESUMEN DE DEBUG")
        print("=" * 80)
        print(f"Total procesados: {self.results['total_processed']}")
        print(f"Exitosos: {self.results['successful']}")
        print(f"Fallidos: {self.results['failed']}")
        print(f"Saltados: {self.results['skipped']}")
        
        if self.results['errors']:
            print(f"\nERRORES ENCONTRADOS:")
            for error in self.results['errors']:
                print(f"\n  Carpeta: {error.get('folder', 'N/A')}")
                print(f"  Email ID: {error.get('email_id', 'N/A')}")
                print(f"  Asunto: {error.get('subject', 'N/A')}")
                print(f"  Error: {error.get('error', 'N/A')}")
        
        print()


if __name__ == "__main__":
    processor = DebugProcessor()
    processor.run()
