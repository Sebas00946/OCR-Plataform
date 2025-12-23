# Sistema de Auto-Aprendizaje OCR

Sistema automatizado para entrenar el OCR de clasificación de facturas usando correos del buzón compartido.

## 📋 Descripción

Este sistema procesa automáticamente los correos del buzón compartido `recepcionfe@medilaser.com.co` para entrenar el OCR. Cada correo está clasificado manualmente en carpetas por sucursal y tipo, lo que permite al sistema aprender las keywords correctas.

**🚀 Optimizado con procesamiento paralelo:**
- **10 workers** procesando simultáneamente
- **Lotes de 100 correos**
- **Velocidad**: 8-10x más rápido que versión secuencial
- **Tiempo estimado**: 4-6 horas (vs 36-40 horas)

## 📁 Archivos

### Scripts Principales

- **`auto_learning_from_mailbox.py`** - Script principal de auto-aprendizaje
  - Procesa ~52,942 correos del 2025
  - **Procesamiento paralelo con 10 workers**
  - Extrae XML/PDF de archivos ZIP
  - Clasifica y aprende automáticamente
  - Guarda progreso cada 100 correos
  - **Tiempo estimado: 4-6 horas** (optimizado)

- **`test_auto_learning.py`** - Script de prueba
  - Procesa solo 10 correos para validar
  - Útil para verificar cambios antes de ejecutar el completo

- **`list_email_folders.py`** - Utilidad para listar carpetas del buzón
  - Lista todas las carpetas y subcarpetas
  - Cuenta correos por carpeta
  - Genera reporte en JSON

### Archivos de Progreso (generados automáticamente)

- **`auto_learning_progress.json`** - Progreso del procesamiento
- **`auto_learning_results.json`** - Resultados y estadísticas
- **`auto_learning.log`** - Log detallado de ejecución

## 🚀 Uso

### 1. Prueba (Recomendado primero)

```bash
python auto_learning/test_auto_learning.py
```

Esto procesará solo 10 correos para validar que todo funciona correctamente.

### 2. Procesamiento Completo

```bash
python auto_learning/auto_learning_from_mailbox.py
```

Esto iniciará el procesamiento de todos los correos del 2025 (~52,942 correos).

**IMPORTANTE:** 
- El proceso toma **4-6 horas** (procesamiento paralelo optimizado)
- Se puede interrumpir con Ctrl+C y reanudar después
- El progreso se guarda cada 100 correos
- Usa **10 workers** procesando simultáneamente

### 3. Reanudar Procesamiento Interrumpido

Si el proceso se interrumpe, simplemente ejecuta de nuevo:

```bash
python auto_learning/auto_learning_from_mailbox.py
```

El sistema detectará automáticamente dónde quedó y continuará desde ahí.

## 📊 Estructura de Carpetas del Buzón

```
SUCURSALES/
├── 1. NEIVA/
│   ├── 1.1. PROVEEDORES MEDICOS E IPS (→ Neiva - Administración)
│   ├── 1.2. PROVEEDORES MEDICAMENTOS (→ Neiva - Almacén)
│   └── 1.3. GASTOS (→ Neiva - Administración)
├── 2. TUNJA/
│   ├── 2.1. PROVEEDORES MEDICOS E IPS (→ Tunja - Administración)
│   ├── 2.2. PROVEEDORES MEDICAMENTOS (→ Tunja - Almacén)
│   └── 2.3. GASTOS (→ Tunja - Administración)
├── 3.FLORENCIA/
│   ├── 3.1. PROVEEDORES MEDICOS E IPS (→ Florencia - Administración)
│   ├── 3.2. PROVEEDORES MEDICAMENTOS (→ Florencia - Almacén)
│   └── 3.3. GASTOS (→ Florencia - Administración)
├── 4. PITALITO/
│   ├── 4.1. PROVEEDORES MEDICOS E IPS (→ Pitalito - Administración)
│   ├── 4.2. PROVEEDORES MEDICAMENTOS (→ Pitalito - Almacén)
│   └── 4.3. GASTOS (→ Pitalito - Administración)
├── 5. BOGOTA/
│   ├── 5.1. PROVEEDORES MEDICOS E IPS (→ Bogotá - Administración)
│   ├── 5.2. PROVEEDORES MEDICAMENTOS (→ Bogotá - Almacén)
│   └── 5.3. GASTOS (→ Bogotá - Administración)
└── 7. DUITAMA/
    └── 7.1. PROVEEDORES MÉDICOS E IPS (→ Duitama - Administración)
```

Cada carpeta contiene subcarpetas por proveedor con los correos clasificados.

## 🔧 Configuración

Las credenciales están en el archivo `.env` en la raíz del proyecto:

```env
# Azure AD B2C Configuration
AZURE_CLIENT_ID=7965d8f8-9618-4add-82db-211c20e70433
AZURE_CLIENT_SECRET=nzp8Q~hLTUf4I8Od2qDTj5hBFsb6GPD3nlCDsdrE
AZURE_TENANT_ID=c51cdb8c-7df6-40f1-889c-abece1950a33

# Buzón compartido
SHARED_MAILBOX_EMAIL=recepcionfe@medilaser.com.co
```

## 📈 Estadísticas

- **Total de correos**: ~52,942 (año 2025)
- **Carpetas a procesar**: 19
- **Subcarpetas (proveedores)**: ~295 solo en Neiva
- **Workers paralelos**: 10
- **Tamaño de lote**: 100 correos
- **Velocidad estimada**: 0.3-0.5 segundos por correo (paralelo)
- **Tiempo total**: 4-6 horas (optimizado con paralelización)

## 🔍 Monitoreo

Durante la ejecución, el sistema muestra:

```
📦 Lote 1/530 (100 correos) - Procesando con 10 workers...
   ✅ 90/6351 (1.4%) - ✅ 60 | ❌ 20 | ⏭️ 10 | ⚠️ 0
   💾 Progreso guardado
```

Donde:
- ✅ = Clasificación correcta (aprende)
- ❌ = Clasificación incorrecta (no aprende)
- ⏭️ = Saltado (sin XML/PDF o duplicado)
- ⚠️ = Error al procesar

**Nota**: Con 10 workers, verás múltiples correos procesándose simultáneamente.

## 🛠️ Solución de Problemas

### Error de conexión

Si hay error de conexión al buzón:
1. Verificar credenciales en `.env`
2. Verificar que el usuario tiene permisos delegados al buzón compartido

### Proceso muy lento

El proceso ahora es **8-10x más rápido** gracias a:
- Procesamiento paralelo con 10 workers
- Lotes de 100 correos
- Optimización de I/O

Si aún es lento, puedes ajustar en el código:
```python
MAX_WORKERS = 15  # Aumentar workers (cuidado con límites de API)
BATCH_SIZE = 150  # Aumentar tamaño de lote
```

### Reiniciar desde cero

Si quieres reiniciar el procesamiento:

```bash
del auto_learning/auto_learning_progress.json
del auto_learning/auto_learning_results.json
python auto_learning/auto_learning_from_mailbox.py
```

## 📝 Notas Importantes

1. **No interrumpir durante guardado**: Espera a que termine de guardar el progreso
2. **Verificar duplicados**: El sistema verifica por CUFE para evitar duplicados
3. **Archivos ZIP**: Los correos contienen ZIP con XML y PDF dentro
4. **Aprendizaje incremental**: La precisión mejora a medida que procesa más correos

## 🎯 Objetivo

Al finalizar el procesamiento, el OCR habrá aprendido:
- Keywords específicas de cada sucursal
- Patrones de texto que identifican cada ubicación
- Diferencias entre tipos de facturas (médicos, medicamentos, gastos)

Esto mejorará significativamente la precisión de clasificación automática.
