# CAMBIOS: Implementación de Código UTP Real

**Fecha**: 11 de enero de 2026
**Estado**: ✅ Implementado (Pendiente despliegue)

---

## Resumen Ejecutivo

Se implementó la separación entre el **código interno autogenerado** (ej: SIS-2026-0001) y el **código UTP físico** (ej: UTP296375) que logística pega en los equipos.

### Antes
- `codigo_utp`: Autogenerado (SIS-2026-0001)
- Los usuarios NO podían ingresar el código real de la etiqueta física

### Después
- `codigo_interno`: Autogenerado (SIS-2026-0001) - para uso interno
- `codigo_utp`: Ingresado manualmente (UTP296375) o "PENDIENTE" si aún no tiene etiqueta

---

## Cambios en Base de Datos

### Migración: `0003_cambiar_codigo_utp_a_codigo_interno.py`

**Operaciones:**
1. Renombra `codigo_utp` → `codigo_interno`
2. Marca `codigo_interno` como `editable=False` (autogenerado)
3. Crea nuevo campo `codigo_utp` con `default="PENDIENTE"`
4. Actualiza índices de base de datos

**Impacto en datos existentes:**
- Todos los ítems existentes mantendrán su código actual como `codigo_interno`
- Todos los ítems existentes tendrán `codigo_utp = "PENDIENTE"` hasta que se actualicen manualmente

---

## Cambios en Modelo (`productos/models.py`)

### Campo `codigo_interno`
```python
codigo_interno = models.CharField(
    max_length=50,
    unique=True,
    editable=False,  # No se puede editar manualmente
    help_text="Código interno autogenerado (ej: SIS-2026-0001)"
)
```

### Campo `codigo_utp`
```python
codigo_utp = models.CharField(
    max_length=20,
    default="PENDIENTE",  # Valor por defecto
    help_text="Código de etiqueta física de logística (ej: UTP296375) o PENDIENTE si aún no tiene"
)
```

### Validaciones Implementadas

**Método `clean()`:**
- ✅ Si `codigo_utp != "PENDIENTE"`, debe tener formato `UTP` seguido de números
- ✅ Códigos UTP reales deben ser únicos (excepto "PENDIENTE" que puede repetirse)
- ✅ Regex: `^UTP\d+$`

**Método `save()`:**
- ✅ Genera automáticamente `codigo_interno` si no existe
- ✅ Ejecuta `full_clean()` antes de guardar

**Propiedad `codigo_utp_pendiente`:**
```python
@property
def codigo_utp_pendiente(self):
    return self.codigo_utp == "PENDIENTE"
```

**Método renombrado:**
- `generar_codigo_utp()` → `generar_codigo_interno()`

---

## Cambios en Formularios (`productos/forms.py`)

### ItemForm

**Nuevo campo en fields:**
```python
fields = [
    'codigo_utp',  # NUEVO - Ahora editable
    'serie', 'nombre', 'descripcion', ...
]
```

**Widget:**
```python
'codigo_utp': forms.TextInput(attrs={
    'class': 'form-control',
    'placeholder': 'UTP seguido de números (ej: UTP296375) o dejar PENDIENTE'
})
```

---

## Cambios en Vistas (`productos/views.py`)

### 1. Importación Excel - Validación (ItemImportarView)

**Nuevo código de validación (líneas 1815-1829):**
```python
# Validar código UTP (opcional)
codigo_utp = get_str(item_data.get('codigo_utp', 'PENDIENTE')).upper()
if not codigo_utp:
    codigo_utp = 'PENDIENTE'
    advertencias.append('Código UTP pendiente - se asignará etiqueta de logística posteriormente')
elif codigo_utp != 'PENDIENTE':
    # Validar formato UTP + números
    if not re.match(r'^UTP\d+$', codigo_utp):
        errores.append(f'Código UTP "{codigo_utp}" inválido - debe ser UTP seguido de números')
    elif Item.objects.filter(codigo_utp=codigo_utp).exists():
        errores.append(f'Código UTP {codigo_utp} ya existe en el sistema')
else:
    advertencias.append('Código UTP pendiente - se asignará etiqueta de logística posteriormente')
```

### 2. Importación Excel - Creación (ItemImportarConfirmarView)

**Cambio en líneas 2023-2026:**
```python
# Antes:
codigo_utp = Item.generar_codigo_utp(area.codigo)

# Después:
codigo_utp = get_str(data.get('codigo_utp', 'PENDIENTE')).upper()
if not codigo_utp:
    codigo_utp = 'PENDIENTE'
```

### 3. Plantilla Excel - Nuevos Headers

**Headers opcionales actualizado (línea 1572):**
```python
headers_opcionales = [
    'codigo_utp',  # NUEVO - Primera columna opcional
    'descripcion', 'ambiente_codigo', ...
]
```

**Ejemplos actualizados:**
- Ejemplo 1: `'UTP296375'` (con código real)
- Ejemplo 2: `'PENDIENTE'` (sin etiqueta aún)

**Instrucciones actualizadas:**
```
2. COLUMNAS OPCIONALES (Gris):
   - codigo_utp: Código de etiqueta física (ej: UTP296375)
     Dejar vacío o PENDIENTE si aún no tiene etiqueta de logística
     Formato: UTP seguido de números
```

---

## Flujo de Trabajo

### Escenario 1: Crear ítem SIN código UTP
```
1. Usuario crea ítem
2. Deja campo codigo_utp vacío o escribe "PENDIENTE"
3. Sistema guarda:
   - codigo_interno: SIS-2026-0042 (auto)
   - codigo_utp: PENDIENTE
4. ⚠️ Advertencia visible: "Código UTP pendiente"
```

### Escenario 2: Crear ítem CON código UTP
```
1. Usuario crea ítem
2. Ingresa codigo_utp: UTP296375
3. Sistema valida formato y unicidad
4. Sistema guarda:
   - codigo_interno: SIS-2026-0042 (auto)
   - codigo_utp: UTP296375
5. ✅ Sin advertencias
```

### Escenario 3: Actualizar ítem pendiente
```
1. Logística envía etiquetas físicas
2. Usuario edita ítem
3. Cambia codigo_utp de "PENDIENTE" a "UTP296375"
4. Sistema valida y guarda
5. ✅ Advertencia desaparece
```

### Escenario 4: Importación Excel masiva
```
1. Usuario descarga plantilla Excel
2. Llena columna codigo_utp:
   - Con código real: UTP123456
   - Sin código: PENDIENTE o vacío
3. Sube archivo
4. Vista previa muestra:
   - ⚠️ Advertencia para ítems PENDIENTE
   - ❌ Error si formato inválido
   - ❌ Error si código duplicado
5. Confirma importación
```

---

## Validaciones por Capa

| Validación | Modelo | Formulario | Vista Excel | Nivel |
|------------|--------|------------|-------------|-------|
| Formato UTP\d+ | ✅ | ✅ | ✅ | Crítico |
| Unicidad (UTP reales) | ✅ | ✅ | ✅ | Crítico |
| PENDIENTE permitido múltiple | ✅ | ✅ | ✅ | Normal |
| Default PENDIENTE | ✅ | ❌ | ✅ | Normal |
| Case insensitive (upper) | ❌ | ❌ | ✅ | Mejora |

---

## Impacto en UI/UX

### Templates Pendientes de Actualizar:

1. **item_detail.html** - Mostrar advertencia si `codigo_utp_pendiente`
2. **item_list.html** - Badge de advertencia en listado
3. **item_form.html** - Campo codigo_utp editable
4. **dashboard.html** - Contador de "Ítems sin código UTP"

### Advertencia Sugerida:
```html
{% if item.codigo_utp_pendiente %}
<div class="alert alert-warning">
    <i class="fas fa-exclamation-triangle"></i>
    <strong>Código UTP Pendiente:</strong>
    Este ítem aún no tiene etiqueta física de logística asignada.
</div>
{% endif %}
```

---

## Testing Requerido

### Antes de Desplegar:

1. ✅ **Migración:**
   - Ejecutar en local primero
   - Verificar que datos existentes se migran correctamente
   - Backup de base de datos

2. ⏳ **Crear ítem nuevo:**
   - Con codigo_utp vacío → debe quedar PENDIENTE
   - Con UTP123456 → debe guardarse correctamente
   - Con utp999 (minúsculas) → debe convertirse a UTP999
   - Con UTP999ABC → debe dar error de formato

3. ⏳ **Editar ítem existente:**
   - Cambiar PENDIENTE → UTP123 → debe guardar
   - Cambiar UTP123 → PENDIENTE → debe permitir
   - Cambiar UTP123 → UTP999 (duplicado) → debe dar error

4. ⏳ **Importación Excel:**
   - Archivo con códigos mezclados (algunos PENDIENTE, algunos reales)
   - Archivo con código duplicado → debe mostrar error en preview
   - Archivo con formato inválido → debe mostrar error en preview

---

## Comandos de Despliegue

### Local (Testing):
```bash
# 1. Aplicar migración
python manage.py migrate productos

# 2. Verificar que todo funciona
python manage.py check

# 3. Crear superusuario si es necesario
python manage.py createsuperuser
```

### Producción:
```bash
# 1. Conectar al servidor
ssh inventario

# 2. Ir al directorio
cd /var/www/inventario

# 3. Activar entorno virtual
source venv/bin/activate

# 4. Backup de base de datos
pg_dump inventario_db > backup_antes_codigo_utp_$(date +%Y%m%d).sql

# 5. Pull de cambios
git pull

# 6. Aplicar migraciones
python manage.py migrate productos

# 7. Recolectar archivos estáticos
python manage.py collectstatic --noinput

# 8. Reiniciar servicio
sudo systemctl restart inventario

# 9. Verificar estado
sudo systemctl status inventario
```

---

## Archivos Modificados

| Archivo | Cambios | Líneas |
|---------|---------|--------|
| `productos/models.py` | Renombrar campo, validaciones, propiedad | +60 |
| `productos/forms.py` | Agregar campo codigo_utp | +5 |
| `productos/views.py` | Validación Excel, plantilla | +40 |
| `productos/migrations/0003_*.py` | Migración de datos | NEW |
| `CAMBIOS_CODIGO_UTP.md` | Este archivo | NEW |

---

## Riesgos y Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Migración falla | Baja | Alto | Backup antes de migrar |
| Código duplicado en producción | Media | Bajo | Validación en 3 capas |
| Usuarios confundidos | Alta | Bajo | Documentación clara |
| full_clean() muy estricto | Media | Medio | Try-except en imports masivos |

---

## Próximos Pasos (Post-Despliegue)

1. ⏳ Actualizar templates con advertencias visuales
2. ⏳ Agregar filtro "Sin código UTP" en listado
3. ⏳ Dashboard: Contador de ítems pendientes
4. ⏳ Reportes: Exportar ítems sin código UTP
5. ⏳ Notificaciones: Alertar cuando haya muchos PENDIENTE

---

## Notas Adicionales

- El código interno (`codigo_interno`) NUNCA debe editarse manualmente
- El código UTP puede editarse libremente (supervisores/admins)
- "PENDIENTE" NO es case-sensitive en validación
- Formato regex: `^UTP\d+$` (UTP seguido SOLO de dígitos)
- No hay límite en la cantidad de dígitos después de "UTP"

---

**Implementado por**: Claude Sonnet 4.5
**Revisado por**: Pendiente
**Aprobado para producción**: Pendiente
