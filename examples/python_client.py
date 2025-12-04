"""
Ejemplo de cliente Python para la API OCR
"""
import requests
import time
from typing import Optional


class OCRClient:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key} if api_key else {}
    
    def health_check(self) -> dict:
        """Verificar estado de la API"""
        response = requests.get(f"{self.base_url}/api/v1/health")
        response.raise_for_status()
        return response.json()
    
    def process_image(
        self,
        file_path: str,
        language: str = "spa+eng",
        quality: str = "balanced"
    ) -> dict:
        """Procesar una imagen"""
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"language": language, "quality": quality}
            response = requests.post(
                f"{self.base_url}/api/v1/ocr/image",
                headers=self.headers,
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()
    
    def process_pdf(
        self,
        file_path: str,
        language: str = "spa+eng",
        quality: str = "balanced"
    ) -> dict:
        """Procesar un PDF"""
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"language": language, "quality": quality}
            response = requests.post(
                f"{self.base_url}/api/v1/ocr/pdf",
                headers=self.headers,
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()
    
    def process_batch(
        self,
        file_paths: list[str],
        language: str = "spa+eng",
        quality: str = "balanced"
    ) -> list[dict]:
        """Procesar múltiples archivos"""
        files = [("files", open(path, "rb")) for path in file_paths]
        data = {"language": language, "quality": quality}
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/ocr/batch",
                headers=self.headers,
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()
        finally:
            for _, f in files:
                f.close()
    
    def get_job_status(self, job_id: str) -> dict:
        """Obtener estado de un trabajo"""
        response = requests.get(
            f"{self.base_url}/api/v1/ocr/jobs/{job_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_job_result(self, job_id: str) -> dict:
        """Obtener resultado de un trabajo"""
        response = requests.get(
            f"{self.base_url}/api/v1/ocr/jobs/{job_id}/result",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(
        self,
        job_id: str,
        timeout: int = 300,
        poll_interval: int = 2
    ) -> Optional[dict]:
        """Esperar a que un trabajo se complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_job_status(job_id)
            
            if status["status"] == "completed":
                return self.get_job_result(job_id)
            elif status["status"] == "failed":
                raise Exception(f"Job failed: {status.get('error_message')}")
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")
    
    def get_history(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> dict:
        """Obtener historial de trabajos"""
        params = {"skip": skip, "limit": limit}
        if status:
            params["status"] = status
        
        response = requests.get(
            f"{self.base_url}/api/v1/ocr/history",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()


def main():
    """Ejemplo de uso"""
    # Crear cliente
    client = OCRClient(
        base_url="http://localhost:8000",
        api_key="your-secret-api-key-here"
    )
    
    # Verificar salud de la API
    print("Verificando API...")
    health = client.health_check()
    print(f"API Status: {health['status']}")
    print(f"Version: {health['version']}")
    
    # Procesar una imagen
    print("\nProcesando imagen...")
    job = client.process_image(
        "sample_image.png",
        language="spa+eng",
        quality="balanced"
    )
    print(f"Job ID: {job['id']}")
    print(f"Status: {job['status']}")
    
    # Esperar resultado
    print("\nEsperando resultado...")
    result = client.wait_for_completion(job['id'])
    print(f"Texto extraído ({len(result['text'])} caracteres):")
    print(result['text'][:200] + "..." if len(result['text']) > 200 else result['text'])
    print(f"Confianza: {result['confidence']:.2f}%")
    print(f"Tiempo de procesamiento: {result['processing_time']:.2f}s")
    
    # Ver historial
    print("\nHistorial reciente:")
    history = client.get_history(limit=5)
    print(f"Total de trabajos: {history['total']}")
    for job in history['jobs']:
        print(f"- {job['id']}: {job['file_name']} ({job['status']})")


if __name__ == "__main__":
    main()
