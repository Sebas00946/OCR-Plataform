#!/bin/bash

# Ejemplos de uso de la API OCR con curl

API_URL="http://localhost:8000"
API_KEY="your-secret-api-key-here"

echo "=== OCR API - Ejemplos con curl ==="
echo ""

# 1. Health Check
echo "1. Health Check"
curl -X GET "$API_URL/api/v1/health"
echo -e "\n"

# 2. Procesar imagen
echo "2. Procesar imagen"
curl -X POST "$API_URL/api/v1/ocr/image" \
  -H "X-API-Key: $API_KEY" \
  -F "file=@sample_image.png" \
  -F "language=spa+eng" \
  -F "quality=balanced"
echo -e "\n"

# 3. Procesar PDF
echo "3. Procesar PDF"
curl -X POST "$API_URL/api/v1/ocr/pdf" \
  -H "X-API-Key: $API_KEY" \
  -F "file=@sample_document.pdf" \
  -F "language=spa" \
  -F "quality=accurate"
echo -e "\n"

# 4. Consultar estado de trabajo
echo "4. Consultar estado de trabajo"
JOB_ID="550e8400-e29b-41d4-a716-446655440000"  # Reemplazar con ID real
curl -X GET "$API_URL/api/v1/ocr/jobs/$JOB_ID" \
  -H "X-API-Key: $API_KEY"
echo -e "\n"

# 5. Obtener resultado
echo "5. Obtener resultado"
curl -X GET "$API_URL/api/v1/ocr/jobs/$JOB_ID/result" \
  -H "X-API-Key: $API_KEY"
echo -e "\n"

# 6. Procesamiento por lotes
echo "6. Procesamiento por lotes"
curl -X POST "$API_URL/api/v1/ocr/batch" \
  -H "X-API-Key: $API_KEY" \
  -F "files=@image1.png" \
  -F "files=@image2.jpg" \
  -F "files=@document.pdf" \
  -F "language=spa+eng" \
  -F "quality=balanced"
echo -e "\n"

# 7. Ver historial
echo "7. Ver historial"
curl -X GET "$API_URL/api/v1/ocr/history?skip=0&limit=10" \
  -H "X-API-Key: $API_KEY"
echo -e "\n"

# 8. Filtrar historial por estado
echo "8. Filtrar historial por estado"
curl -X GET "$API_URL/api/v1/ocr/history?status=completed&limit=5" \
  -H "X-API-Key: $API_KEY"
echo -e "\n"

# 9. Eliminar trabajo
echo "9. Eliminar trabajo"
curl -X DELETE "$API_URL/api/v1/ocr/jobs/$JOB_ID" \
  -H "X-API-Key: $API_KEY"
echo -e "\n"

echo "=== Fin de ejemplos ==="
