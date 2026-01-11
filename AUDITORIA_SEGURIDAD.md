# AUDITORÍA DE SEGURIDAD Y CALIDAD DE CÓDIGO
**Sistema de Inventario UTP**
**Fecha**: 10 de enero de 2026
**Auditor**: Claude Sonnet 4.5

---

## 1. RESUMEN EJECUTIVO

Se realizó una auditoría completa del código del Sistema de Inventario UTP, evaluando aspectos de seguridad, validación de datos, manejo de errores y buenas prácticas. El sistema presenta una base sólida con buenas prácticas de Django, pero se identificaron áreas de mejora críticas y recomendaciones.

**Estado General**: 🟡 Bueno con mejoras necesarias

---

## 2. HALLAZGOS CRÍTICOS (🔴 ALTA PRIORIDAD)

### 2.1 Falta de Validación de Tamaño de Archivos Excel

**Ubicación**: `productos/views.py` líneas 1732-1748

**Problema**:
```python
def post(self, request, *args, **kwargs):
    archivo = request.FILES.get('archivo_excel')
    # No hay validación de tamaño antes de load_workbook
    wb = load_workbook(archivo, data_only=True)
```

**Riesgo**: Ataque DoS (Denial of Service) mediante archivos extremadamente grandes.

**Impacto**: Un atacante puede subir un archivo Excel de 100MB+ y consumir toda la memoria del servidor.

**Recomendación**:
```python
# Agregar ANTES de cargar el archivo:
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
if archivo.size > MAX_FILE_SIZE:
    messages.error(request, f'El archivo es demasiado grande. Máximo: 10MB')
    return redirect('productos:item-importar')
```

**Acción**: Implementar validación inmediata.

---

### 2.2 Límite de Filas No Validado a Nivel de Settings

**Ubicación**: `config/settings.py`

**Problema**: Los límites de upload están en valores por defecto de Django:
- `FILE_UPLOAD_MAX_MEMORY_SIZE`: 2.5MB (por defecto)
- `DATA_UPLOAD_MAX_MEMORY_SIZE`: 2.5MB (por defecto)

**Riesgo**: Inconsistencia entre validación en código (10MB mencionado en template) y configuración real.

**Recomendación**:
```python
# Agregar en settings.py:
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644
```

---

### 2.3 SQL Injection Potencial en Búsquedas (BAJO RIESGO ACTUAL)

**Ubicación**: Uso de ORM correcto en todo el código ✅

**Estado**: NO SE ENCONTRARON consultas `.raw()` o `exec()`.

**Calificación**: ✅ EXCELENTE - Uso consistente del ORM de Django.

---

### 2.4 Validación de Tipo de Archivo Insuficiente

**Ubicación**: `productos/views.py` línea 1742

**Problema**:
```python
if not archivo.name.endswith('.xlsx'):
    messages.error(request, 'El archivo debe ser formato .xlsx')
```

**Riesgo**: Un atacante puede renombrar un archivo malicioso como `malware.exe.xlsx`.

**Recomendación**:
```python
import magic  # python-magic

# Validar tanto extensión como MIME type
if not archivo.name.endswith('.xlsx'):
    messages.error(request, 'El archivo debe ser formato .xlsx')
    return redirect('productos:item-importar')

# Validar contenido real del archivo
try:
    mime = magic.from_buffer(archivo.read(2048), mime=True)
    archivo.seek(0)  # Reset para lectura posterior
    if mime not in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
        messages.error(request, 'El archivo no es un Excel válido')
        return redirect('productos:item-importar')
except Exception:
    messages.error(request, 'No se pudo validar el archivo')
    return redirect('productos:item-importar')
```

**Acción**: Instalar `python-magic` y agregar validación de MIME type.

---

## 3. HALLAZGOS IMPORTANTES (🟡 MEDIA PRIORIDAD)

### 3.1 Falta de Rate Limiting en Importación

**Problema**: Un usuario supervisor puede subir archivos Excel ilimitadamente.

**Riesgo**: Abuso de recursos del servidor.

**Recomendación**:
```python
# Instalar django-ratelimit
from django_ratelimit.decorators import ratelimit

# En ItemImportarView:
@method_decorator(ratelimit(key='user', rate='5/h', method='POST'), name='dispatch')
class ItemImportarView(SupervisorRequeridoMixin, TemplateView):
    ...
```

**Acción**: Implementar límite de 5 importaciones por hora por usuario.

---

### 3.2 Manejo de Excepciones Genérico

**Ubicación**: `productos/views.py` líneas 1900-1903 (ItemImportarView)

**Problema**:
```python
except Exception as e:
    messages.error(request, f'Error al procesar el archivo: {str(e)}')
    return redirect('productos:item-importar')
```

**Riesgo**:
1. Exposición de información sensible del servidor en mensajes de error
2. No se registran errores en logs para debugging

**Recomendación**:
```python
import logging
logger = logging.getLogger(__name__)

try:
    # ... código de procesamiento
except openpyxl.utils.exceptions.InvalidFileException:
    messages.error(request, 'El archivo Excel está corrupto o no es válido')
    return redirect('productos:item-importar')
except MemoryError:
    logger.error(f'MemoryError al procesar archivo de {request.user.username}')
    messages.error(request, 'El archivo es demasiado grande para procesar')
    return redirect('productos:item-importar')
except Exception as e:
    logger.exception(f'Error inesperado en importación de {request.user.username}: {e}')
    messages.error(request, 'Ocurrió un error al procesar el archivo. Contacte al administrador.')
    return redirect('productos:item-importar')
```

---

### 3.3 Falta de Validación de Series Duplicadas en Sesión

**Ubicación**: `productos/views.py` línea 1794

**Problema**: Solo valida contra la base de datos, no contra otras filas del mismo archivo.

```python
elif Item.objects.filter(serie=serie).exists():
    errores.append(f'Serie {serie} ya existe en el sistema')
```

**Riesgo**: Si el Excel tiene 2 filas con la misma serie, ambas pasarán la validación de preview.

**Recomendación**:
```python
# Al inicio del bucle, mantener un set de series ya procesadas
series_en_archivo = set()

# Dentro del bucle:
if serie in series_en_archivo:
    errores.append(f'Serie {serie} duplicada dentro del archivo')
elif Item.objects.filter(serie=serie).exists():
    errores.append(f'Serie {serie} ya existe en el sistema')
else:
    series_en_archivo.add(serie)
```

---

### 3.4 Datos Sensibles en Session sin Encriptación

**Ubicación**: `productos/views.py` línea 1920

**Problema**:
```python
request.session['items_preview_data'] = items_preview
```

**Riesgo**: Los datos de preview se almacenan en sesión sin encriptar. Si un atacante obtiene acceso a las sesiones, puede ver los datos.

**Recomendación**:
1. Usar caché con timeout en lugar de sesión
2. Encriptar datos sensibles antes de almacenar

```python
from django.core.cache import cache
import hashlib
import json

# Generar key única
cache_key = f'import_preview_{request.user.id}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}'
cache.set(cache_key, items_preview, timeout=600)  # 10 minutos
request.session['import_cache_key'] = cache_key
```

---

### 3.5 Falta de Logging de Acciones Críticas

**Problema**: No se registran acciones de importación masiva para auditoría.

**Recomendación**:
```python
import logging
audit_logger = logging.getLogger('audit')

# En ItemImportarConfirmarView después de importación exitosa:
audit_logger.info(
    f'IMPORT_SUCCESS: User={request.user.username}, '
    f'Items={items_creados}, Area={area_usuario or "todas"}, '
    f'IP={request.META.get("REMOTE_ADDR")}'
)
```

**Acción**: Configurar logger de auditoría en settings.py.

---

## 4. BUENAS PRÁCTICAS ENCONTRADAS ✅

### 4.1 Autenticación y Autorización
- ✅ Uso correcto de `LoginRequiredMixin` en todas las vistas
- ✅ Mixins personalizados (`PerfilRequeridoMixin`, `SupervisorRequeridoMixin`) bien implementados
- ✅ Restricciones por área funcionando correctamente

### 4.2 CSRF Protection
- ✅ `{% csrf_token %}` presente en todos los formularios
- ✅ Middleware CSRF activo en settings.py

### 4.3 Validación de Formularios
- ✅ Uso de `ModelForm` con validaciones robustas
- ✅ Método `clean()` personalizado en formularios complejos
- ✅ Validaciones en cascada para evitar datos inconsistentes

### 4.4 Transacciones Atómicas
- ✅ Uso de `@transaction.atomic` en importación masiva (línea 1945)
- ✅ Rollback automático en caso de errores

### 4.5 Configuración de Seguridad
- ✅ `DEBUG = False` en producción
- ✅ `SECURE_SSL_REDIRECT` activado
- ✅ `SESSION_COOKIE_SECURE = True` en producción
- ✅ `CSRF_COOKIE_SECURE = True` en producción
- ✅ HSTS configurado (1 año)
- ✅ `X_FRAME_OPTIONS = 'DENY'`

### 4.6 Passwords
- ✅ Validadores de contraseña configurados
- ✅ No hay contraseñas hardcodeadas (uso de `decouple`)

---

## 5. HALLAZGOS MENORES (🟢 BAJA PRIORIDAD)

### 5.1 Falta de Documentación en Funciones Complejas

**Recomendación**: Agregar docstrings a métodos de validación complejos.

```python
def validar_item_excel(self, item_data, area_usuario):
    """
    Valida un ítem del Excel antes de importarlo.

    Args:
        item_data (dict): Datos del ítem desde Excel
        area_usuario (Area|None): Área del usuario (None si es admin)

    Returns:
        tuple: (errores: list, advertencias: list, datos_validados: dict)
    """
```

---

### 5.2 Magic Numbers en Código

**Ubicación**: Múltiples lugares

**Problema**:
```python
if len(items_preview) >= 1000:  # Magic number
```

**Recomendación**:
```python
# En settings.py:
MAX_ITEMS_PER_IMPORT = 1000

# En views.py:
from django.conf import settings
if len(items_preview) >= settings.MAX_ITEMS_PER_IMPORT:
```

---

### 5.3 Falta de Índices en Búsquedas Frecuentes

**Ubicación**: `productos/models.py`

**Recomendación**:
```python
class Item(models.Model):
    serie = models.CharField(max_length=100, unique=True, db_index=True)
    codigo_utp = models.CharField(max_length=20, unique=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['area', 'estado']),
            models.Index(fields=['area', '-fecha_creacion']),
        ]
```

---

## 6. CONFIGURACIONES DE SEGURIDAD RECOMENDADAS

### 6.1 Settings.py - Agregar

```python
# Seguridad de archivos
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Tipos de archivo permitidos
ALLOWED_UPLOAD_EXTENSIONS = ['.xlsx']
ALLOWED_MIME_TYPES = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
]

# Límites de importación
MAX_ITEMS_PER_IMPORT = 1000
IMPORT_RATE_LIMIT = '5/hour'  # Para django-ratelimit

# Logging de auditoría
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'audit': {
            'format': '{asctime} {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'audit.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'audit',
        },
    },
    'loggers': {
        'audit': {
            'handlers': ['audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### 6.2 Requirements.txt - Agregar

```python
python-magic==0.4.27          # Validación de MIME types
django-ratelimit==4.1.0       # Rate limiting
```

---

## 7. PLAN DE ACCIÓN PRIORIZADO

### 🔴 **Crítico - Implementar AHORA**

1. ✅ Agregar validación de tamaño de archivo antes de `load_workbook()`
2. ✅ Configurar límites en `settings.py` (FILE_UPLOAD_MAX_MEMORY_SIZE)
3. ✅ Validar series duplicadas dentro del mismo archivo Excel
4. ✅ Mejorar manejo de excepciones con logging específico

### 🟡 **Importante - Implementar en 1 semana**

5. ⏳ Instalar y configurar `python-magic` para validación MIME
6. ⏳ Implementar rate limiting con `django-ratelimit`
7. ⏳ Migrar preview de sesión a caché con timeout
8. ⏳ Configurar logging de auditoría para importaciones

### 🟢 **Mejoras - Implementar gradualmente**

9. ⏳ Agregar docstrings a funciones complejas
10. ⏳ Extraer magic numbers a settings
11. ⏳ Agregar índices de base de datos para optimización
12. ⏳ Crear tests unitarios para validaciones de importación

---

## 8. MÉTRICAS DE SEGURIDAD

| Aspecto | Calificación | Notas |
|---------|--------------|-------|
| Autenticación | 🟢 Excelente | Mixins bien implementados |
| Autorización | 🟢 Excelente | Restricciones por área funcionan |
| Validación de Entrada | 🟡 Buena | Falta validación de tamaño/MIME |
| Protección CSRF | 🟢 Excelente | Implementado correctamente |
| SQL Injection | 🟢 Excelente | Uso correcto del ORM |
| XSS Protection | 🟢 Excelente | Django auto-escape activo |
| Manejo de Errores | 🟡 Buena | Mejoras en excepciones específicas |
| Logging | 🔴 Insuficiente | Falta logging de auditoría |
| Rate Limiting | 🔴 Ausente | Sin protección contra abuso |
| Configuración SSL | 🟢 Excelente | HSTS y cookies seguras OK |

**Calificación Global**: 🟡 **7.5/10** - Bueno con mejoras necesarias

---

## 9. CONCLUSIONES

El Sistema de Inventario UTP tiene una base de seguridad sólida con buenas prácticas de Django. Los principales puntos a mejorar son:

1. **Validación de archivos**: Crítico para prevenir ataques DoS
2. **Rate limiting**: Importante para prevenir abuso
3. **Logging de auditoría**: Esencial para trazabilidad

Las vulnerabilidades encontradas son de severidad **MEDIA a BAJA** y pueden mitigarse con las correcciones propuestas. No se encontraron vulnerabilidades críticas de SQL Injection o XSS.

**Recomendación**: Implementar las correcciones críticas (🔴) antes de poner en producción con carga real de usuarios.

---

**Auditoría realizada por**: Claude Sonnet 4.5
**Fecha de revisión**: 10 de enero de 2026
**Próxima auditoría recomendada**: Febrero 2026 (post-implementación de correcciones)
