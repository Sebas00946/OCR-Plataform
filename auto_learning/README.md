# Sistema de Auto-Aprendizaje OCR

Sistema automatizado para entrenar el OCR de clasificación de facturas usando correos del buzón compartido de Medilaser.

## 📋 Descripción

Este sistema procesa automáticamente los correos del buzón compartido `recepcionfe@medilaser.com.co` para entrenar el OCR. Cada correo está clasificado manualmente en carpetas por sucursal y tipo, lo que permite al sistema aprender las keywords correctas.

**🚀 Características:**
- **Procesamiento paralelo** con 10 workers simultáneos
- **Lotes de 100 correos** para optimizar rendimiento
- **Renovación automática de token** cada 50 minutos
- **Guardado de progreso** cada lote procesado
- **Manejo robusto de errores** con reintentos automáticos
- **Velocidad**: ~4,500 correos/hora

## 📁 Estructura del Buzón

```
SUCURSALES/
├── 1. NEIVA/
│   ├── 1.1. PROVEEDORES MEDICOS E IPS/ (295 proveedores)
│   ├── 1.2. PROVEEDORES MEDICAMENTOS/ (36 proveedores)
│   └── 1.3. GASTOS/ (714 proveedores)
├── 2. TUNJA/
│   ├── 2.1. PROVEEDORES MEDICOS E IPS/ (139 proveedores)
│   ├── 2.2. PROVEEDORES MEDICAMENTOS/ (17 proveedores)
│   └── 2.3. GASTOS/ (392 proveedores)
├── 3.FLORENCIA/
│   ├── 3.1. PROVEEDORES MEDICOS E IPS/ (97 proveedores)
│   ├── 3.2. PROVEEDORES MEDICAMENTOS/ (17 proveedores)
│   └── 3.3. GASTOS/ (372 proveedores)
├── 4. PITALITO/
│   ├── 4.1. PROVEEDORES MEDICOS E IPS/ (3 proveedores)
│   ├── 4.2. PROVEEDORES MEDICAMENTOS/ (6 proveedores)
│   └── 4.3. GASTOS/ (104 proveedores)
├── 5. BOGOTA/
│   ├── 5.1. PROVEEDORES MEDICOS E IPS/ (1 proveedor)
│   ├── 5.2. PROVEEDORES MEDICAMENTOS/ (0 proveedores)
│   └── 5.3. GASTOS/ (187 proveedores)
├── 6. FACATATIVA/
│   ├── 6.1. PROVEEDORES MEDICOS E IPS/ (20 proveedores)
│   ├── 6.2. PROVEEDORES MEDICAMENTOS/ (4 proveedores)
│   └── 6.3 GASTOS/ (57 proveedores)
└── 7. DUITAMA/
    ├── 7.1. PROVEEDORES MÉDICOS E IPS/ (1 proveedor)
    └── 7.3. GASTOS/ (35 proveedores)
```

Cada carpeta de proveedor contiene correos con facturas clasificadas manualmente.

## 🚀 Uso

### Ejecutar Auto-Aprendizaje

```bash
python auto_learning/auto_learning_from_mailbox.py
```

El script:
- ✅ Procesa todas las carpetas del buzón
- ✅ Extrae XML y PDF de archivos ZIP
- ✅ Clasifica cada factura
- ✅ Aprende de clasificaciones correctas e incorrectas
- ✅ Guarda progreso automáticamente
- ✅ Puede interrumpirse y reanudarse

### Herramientas de Diagnóstico

```bash
# Ver estado actual del procesamiento
python auto_learning/diagnostico.py

# Resetear progreso (continuar o empezar desde cero)
python auto_learning/reset_progress.py
```

## 📊 Monitoreo

Durante la ejecución verás:

```
================================================================================
📁 PROCESANDO: 1. NEIVA/1.1. PROVEEDORES MEDICOS E IPS
================================================================================
🔍 Buscando carpeta...
✅ Carpeta encontrada
📧 Obteniendo correos del 2025 (incluyendo subcarpetas)...
   📂 Encontradas 295 subcarpetas (proveedores)
✅ 6,351 correos encontrados

📦 Lote 1/64 (100 correos) - Procesando con 10 workers...
   ✅ 100/6351 (1.6%) - ✅ 85 | ❌ 10 | ⏭️ 5 | ⚠️ 0 | ⏱️ ETA: 42min
   💾 Progreso guardado
```

**Indicadores:**
- ✅ = Clasificación correcta (refuerza keywords)
- ❌ = Clasificación incorrecta (aprende nuevas keywords)
- ⏭️ = Saltado (duplicado o sin archivos)
- ⚠️ = Error técnico

## 🔧 Configuración

Las credenciales están en `.env`:

```env
AZURE_CLIENT_ID=7965d8f8-9618-4add-82db-211c20e70433
AZURE_CLIENT_SECRET=nzp8Q~hLTUf4I8Od2qDTj5hBFsb6GPD3nlCDsdrE
AZURE_TENANT_ID=c51cdb8c-7df6-40f1-889c-abece1950a33
SHARED_MAILBOX_EMAIL=recepcionfe@medilaser.com.co
```

## 📈 Rendimiento

- **Workers paralelos**: 10
- **Tamaño de lote**: 100 correos
- **Velocidad**: ~4,500 correos/hora
- **Tiempo estimado**: Variable según cantidad de correos
- **Renovación de token**: Automática cada 50 minutos

## 🔍 Solución de Problemas

### El script se detuvo

Si el script se interrumpe, simplemente ejecútalo de nuevo:

```bash
python auto_learning/auto_learning_from_mailbox.py
```

Continuará desde donde quedó gracias al archivo de progreso.

### Ver qué carpetas faltan procesar

```bash
python auto_learning/diagnostico.py
```

Esto mostrará:
- Carpetas ya procesadas
- Carpetas pendientes
- Estadísticas de procesamiento
- Últimos errores

### Reiniciar desde cero

```bash
python auto_learning/reset_progress.py
```

Selecciona la opción 1 para borrar todo el progreso y empezar de nuevo.

### Token expirado

El script ahora renueva automáticamente el token cada 50 minutos. Si aún así hay problemas:
1. Verifica las credenciales en `.env`
2. Verifica permisos del usuario en Azure AD

## 💡 Cómo Funciona el Aprendizaje

### Clasificaciones Correctas (✅)
Cuando el OCR clasifica correctamente:
- Refuerza las keywords existentes
- Aumenta la confianza en esos patrones
- No crea nuevas keywords

### Clasificaciones Incorrectas (❌)
Cuando el OCR clasifica incorrectamente:
- **Extrae keywords del texto**
- **Las agrega a la clasificación correcta**
- Aprende nuevos patrones
- Mejora para futuras clasificaciones

### Correos Saltados (⏭️)
Se saltan correos que:
- Ya fueron procesados (por CUFE)
- No tienen XML ni PDF
- No tienen adjuntos

## 📝 Archivos Generados

- **`auto_learning_progress.json`** - Progreso del procesamiento
- **`auto_learning_results.json`** - Resultados y estadísticas
- **`auto_learning.log`** - Log detallado (si existe)

## 🎯 Objetivo

Al finalizar, el OCR habrá aprendido:
- ✅ Keywords específicas de cada sucursal
- ✅ Patrones de texto que identifican ubicaciones
- ✅ Diferencias entre tipos de facturas
- ✅ Nombres de proveedores asociados a cada sucursal

Esto mejora significativamente la precisión de clasificación automática.

## ⚠️ Notas Importantes

1. **Procesamiento largo**: Puede tomar varias horas dependiendo del número de correos
2. **No interrumpir durante guardado**: Espera el mensaje "💾 Progreso guardado"
3. **Verificación de duplicados**: El sistema usa CUFE para evitar procesar el mismo correo dos veces
4. **Archivos ZIP**: Los correos contienen ZIP con XML y PDF dentro
5. **Subcarpetas de proveedores**: Cada carpeta tipo tiene subcarpetas por proveedor que también se procesan

## 🔄 Mejoras Implementadas

### Versión Actual
- ✅ Renovación automática de token cada 50 minutos
- ✅ Procesamiento paralelo con 10 workers
- ✅ Manejo robusto de errores con timeouts
- ✅ Logging detallado de operaciones
- ✅ Marca carpetas vacías como procesadas
- ✅ Procesa subcarpetas de proveedores recursivamente

### Problemas Resueltos
- ❌ Token expiraba después de 1 hora → ✅ Renovación automática
- ❌ Script se detenía en carpetas vacías → ✅ Las marca como procesadas
- ❌ No procesaba subcarpetas → ✅ Procesamiento recursivo
- ❌ Errores no se reportaban → ✅ Logging detallado

---

**Desarrollado para Medilaser** - Sistema de Auto-Aprendizaje OCR v2.0
