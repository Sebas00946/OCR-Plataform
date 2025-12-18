"""
Sistema de logging para el API OCR
Registra todas las peticiones y archivos procesados
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import os

# Crear directorio de logs si no existe
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Configurar formato de logs
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class OCRLogger:
    """Logger personalizado para el sistema OCR"""
    
    def __init__(self):
        # Logger principal
        self.logger = logging.getLogger('OCR_API')
        self.logger.setLevel(logging.INFO)
        
        # Evitar duplicados
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Handler para archivo general
        general_handler = logging.FileHandler(
            LOGS_DIR / 'api_requests.log',
            encoding='utf-8'
        )
        general_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        self.logger.addHandler(general_handler)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        self.logger.addHandler(console_handler)
        
        # Logger específico para archivos procesados
        self.file_logger = logging.getLogger('OCR_FILES')
        self.file_logger.setLevel(logging.INFO)
        
        if self.file_logger.handlers:
            self.file_logger.handlers.clear()
        
        file_handler = logging.FileHandler(
            LOGS_DIR / 'processed_files.log',
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        self.file_logger.addHandler(file_handler)
        
        # Logger para estadísticas
        self.stats_logger = logging.getLogger('OCR_STATS')
        self.stats_logger.setLevel(logging.INFO)
        
        if self.stats_logger.handlers:
            self.stats_logger.handlers.clear()
        
        stats_handler = logging.FileHandler(
            LOGS_DIR / 'statistics.log',
            encoding='utf-8'
        )
        stats_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        self.stats_logger.addHandler(stats_handler)
    
    def log_request(self, endpoint: str, method: str, status_code: int, 
                   duration_ms: float, client_ip: str = None, 
                   extra_data: Dict[str, Any] = None):
        """
        Registra una petición HTTP
        
        Args:
            endpoint: Ruta del endpoint
            method: Método HTTP (GET, POST, etc)
            status_code: Código de respuesta
            duration_ms: Duración en milisegundos
            client_ip: IP del cliente
            extra_data: Datos adicionales
        """
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'duration_ms': round(duration_ms, 2),
            'client_ip': client_ip or 'unknown'
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        log_message = f"[{method}] {endpoint} - Status: {status_code} - Duration: {duration_ms:.2f}ms"
        
        if status_code >= 500:
            self.logger.error(log_message + f" - Data: {json.dumps(log_data)}")
        elif status_code >= 400:
            self.logger.warning(log_message + f" - Data: {json.dumps(log_data)}")
        else:
            self.logger.info(log_message + f" - Data: {json.dumps(log_data)}")
        
        print(f"✅ Log guardado: {endpoint} [{method}] - {status_code}")
    
    def log_file_processing(self, factura_id: Optional[int], 
                           xml_file: Optional[str], 
                           pdf_file: Optional[str],
                           sucursal_detectada: Optional[str],
                           unidad_detectada: Optional[str],
                           success: bool,
                           historial_id: Optional[int] = None):
        """
        Registra el procesamiento de archivos de factura
        
        Args:
            factura_id: ID de la factura
            xml_file: Nombre del archivo XML
            pdf_file: Nombre del archivo PDF
            sucursal_detectada: Sucursal identificada
            unidad_detectada: Unidad funcional identificada
            success: Si el procesamiento fue exitoso
            historial_id: ID del registro en historial
        """
        file_data = {
            'timestamp': datetime.now().isoformat(),
            'factura_id': factura_id,
            'xml_file': xml_file,
            'pdf_file': pdf_file,
            'has_xml': bool(xml_file),
            'has_pdf': bool(pdf_file),
            'sucursal_detectada': sucursal_detectada,
            'unidad_detectada': unidad_detectada,
            'success': success,
            'historial_id': historial_id
        }
        
        files_info = []
        if xml_file:
            files_info.append(f"XML: {xml_file}")
        if pdf_file:
            files_info.append(f"PDF: {pdf_file}")
        
        files_str = " + ".join(files_info) if files_info else "Sin archivos"
        
        log_message = (
            f"Factura procesada - ID: {factura_id or 'N/A'} - "
            f"Archivos: {files_str} - "
            f"Sucursal: {sucursal_detectada or 'No detectada'} - "
            f"Unidad: {unidad_detectada or 'No detectada'} - "
            f"Success: {success}"
        )
        
        if success:
            self.file_logger.info(log_message + f" - Data: {json.dumps(file_data)}")
        else:
            self.file_logger.error(log_message + f" - Data: {json.dumps(file_data)}")
        
        print(f"✅ Log de archivo guardado: Factura {factura_id or 'N/A'} - {files_str}")
    
    def log_validation(self, historial_id: int, es_correcta: bool, 
                      sucursal_correcta_id: Optional[int],
                      unidad_correcta_id: Optional[int],
                      observaciones: Optional[str]):
        """
        Registra una validación de clasificación
        
        Args:
            historial_id: ID del historial
            es_correcta: Si la clasificación fue correcta
            sucursal_correcta_id: ID de sucursal correcta (si aplica)
            unidad_correcta_id: ID de unidad correcta (si aplica)
            observaciones: Observaciones del usuario
        """
        validation_data = {
            'timestamp': datetime.now().isoformat(),
            'historial_id': historial_id,
            'es_correcta': es_correcta,
            'sucursal_correcta_id': sucursal_correcta_id,
            'unidad_correcta_id': unidad_correcta_id,
            'observaciones': observaciones
        }
        
        status = "CORRECTA ✓" if es_correcta else "INCORRECTA ✗"
        log_message = f"Validación - Historial ID: {historial_id} - {status}"
        
        if es_correcta:
            self.logger.info(log_message + f" - Data: {json.dumps(validation_data)}")
        else:
            self.logger.warning(log_message + f" - Data: {json.dumps(validation_data)}")
        
        print(f"✅ Log de validación guardado: Historial {historial_id} - {status}")
    
    def log_statistics(self, stats: Dict[str, Any]):
        """
        Registra consulta de estadísticas
        
        Args:
            stats: Diccionario con estadísticas
        """
        stats_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': stats
        }
        
        log_message = (
            f"Estadísticas consultadas - "
            f"Total: {stats.get('total_clasificaciones', 0)} - "
            f"Precisión: {stats.get('precision', 0)}%"
        )
        
        self.stats_logger.info(log_message + f" - Data: {json.dumps(stats_data)}")
        print(f"✅ Log de estadísticas guardado: Precisión {stats.get('precision', 0)}%")
    
    def log_error(self, endpoint: str, error_message: str, 
                 error_type: str = None, traceback_info: str = None):
        """
        Registra un error
        
        Args:
            endpoint: Endpoint donde ocurrió el error
            error_message: Mensaje de error
            error_type: Tipo de error
            traceback_info: Información de traceback
        """
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'error_message': error_message,
            'error_type': error_type,
            'traceback': traceback_info
        }
        
        log_message = f"ERROR en {endpoint} - {error_message}"
        self.logger.error(log_message + f" - Data: {json.dumps(error_data)}")
        print(f"❌ Log de error guardado: {endpoint} - {error_message}")
    
    def get_request_count(self) -> Dict[str, int]:
        """
        Obtiene el conteo de peticiones por endpoint
        
        Returns:
            Diccionario con conteo por endpoint
        """
        counts = {}
        log_file = LOGS_DIR / 'api_requests.log'
        
        if not log_file.exists():
            return counts
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '[GET]' in line or '[POST]' in line:
                        # Extraer endpoint
                        parts = line.split(' - ')
                        if len(parts) >= 2:
                            endpoint_part = parts[1].split(' ')[0]
                            counts[endpoint_part] = counts.get(endpoint_part, 0) + 1
        except Exception as e:
            self.logger.error(f"Error al contar peticiones: {e}")
        
        return counts
    
    def get_file_processing_count(self) -> Dict[str, int]:
        """
        Obtiene el conteo de archivos procesados
        
        Returns:
            Diccionario con estadísticas de archivos
        """
        stats = {
            'total_facturas': 0,
            'con_xml': 0,
            'con_pdf': 0,
            'con_ambos': 0,
            'exitosas': 0,
            'fallidas': 0
        }
        
        log_file = LOGS_DIR / 'processed_files.log'
        
        if not log_file.exists():
            return stats
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'Factura procesada' in line:
                        stats['total_facturas'] += 1
                        
                        if 'XML:' in line:
                            stats['con_xml'] += 1
                        if 'PDF:' in line:
                            stats['con_pdf'] += 1
                        if 'XML:' in line and 'PDF:' in line:
                            stats['con_ambos'] += 1
                        if 'Success: True' in line:
                            stats['exitosas'] += 1
                        elif 'Success: False' in line:
                            stats['fallidas'] += 1
        except Exception as e:
            self.logger.error(f"Error al contar archivos: {e}")
        
        return stats


# Instancia global del logger
ocr_logger = OCRLogger()