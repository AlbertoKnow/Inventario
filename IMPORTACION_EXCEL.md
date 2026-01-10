# IMPORTACIÓN MASIVA DESDE EXCEL - DOCUMENTACIÓN

**Fecha de implementación**: 10 de enero de 2026
**Funcionalidad**: Importación masiva de ítems al inventario desde archivos Excel

---

## 📋 DESCRIPCIÓN GENERAL

La funcionalidad de importación masiva permite a supervisores y administradores cargar múltiples ítems al inventario desde un archivo Excel (.xlsx), facilitando la gestión de inventarios grandes sin necesidad de crear ítems uno por uno.

---

## ✨ CARACTERÍSTICAS IMPLEMENTADAS

### 1. Descarga de Plantilla Excel
- **URL**: `/productos/items/importar/plantilla/`
- **Acceso**: Supervisores y Administradores
- **Funcionalidad**:
  - Genera archivo Excel con columnas predefinidas
  - Incluye hoja de instrucciones detalladas
  - Contiene 2 filas de ejemplo
  - Columnas codificadas por colores:
    - **Rojo**: Obligatorias
    - **Gris**: Opcionales
    - **Azul**: Específicas para área de Sistemas

### 2. Carga y Validación de Archivo
- **URL**: `/productos/items/importar/`
- **Acceso**: Supervisores y Administradores
- **Funcionalidad**:
  - Subir archivo Excel (.xlsx)
  - Opción de crear un nuevo lote para los ítems
  - Opción de asociar a un lote existente
  - Vista previa con validación automática

### 3. Vista Previa Interactiva
- Muestra todos los ítems del archivo
- Validaciones en tiempo real:
  - ✅ **Verde**: Ítem válido, listo para importar
  - ⚠️ **Amarillo**: Advertencias (no bloquea importación)
  - ❌ **Rojo**: Errores bloqueantes (debe corregirse)
- Resumen estadístico (válidos, advertencias, errores, total)
- Tabla detallada con observaciones por fila

### 4. Confirmación e Importación
- **URL**: `/productos/items/importar/confirmar/`
- **Funcionalidad**:
  - Importación atómica (todo o nada)
  - Generación automática de códigos UTP
  - Creación de especificaciones para área Sistemas
  - Registro de auditoría (creado_por)
  - Mensaje de éxito con cantidad de ítems importados

---

## 📊 COLUMNAS DE LA PLANTILLA

### Columnas Obligatorias (Rojo)
| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| serie | Texto | Número de serie único del fabricante | SN123456789 |
| nombre | Texto | Nombre descriptivo del ítem | Laptop Dell Latitude 5430 |
| area | Texto | sistemas, operaciones o laboratorio | sistemas |
| tipo_item | Texto | Debe existir en el sistema para el área | Laptop |
| precio | Numérico | Precio de adquisición | 3500.00 |
| fecha_adquisicion | Fecha | Formato YYYY-MM-DD | 2026-01-10 |

### Columnas Opcionales (Gris)
| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| descripcion | Texto | Descripción adicional | Laptop corporativa i7 |
| ambiente_codigo | Texto | Código del ambiente | CLN-SP-A-P1-LC-001 |
| estado | Texto | nuevo, instalado, dañado, obsoleto | nuevo |
| garantia_hasta | Fecha | Fecha de vencimiento de garantía | 2028-01-10 |
| observaciones | Texto | Observaciones adicionales | - |
| lote_codigo | Texto | Código de lote existente | LOT-2026-0001 |
| es_leasing | Texto | SI o NO | NO |
| leasing_empresa | Texto | Nombre de la empresa de leasing | - |
| leasing_contrato | Texto | Número de contrato de leasing | - |
| leasing_vencimiento | Fecha | Fecha de vencimiento del leasing | - |

### Columnas para Sistemas (Azul)
Solo se deben llenar si `area = sistemas`

| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| marca | Texto | Marca del equipo | Dell |
| modelo | Texto | Modelo del equipo | Latitude 5430 |
| procesador | Texto | Procesador | Intel Core i7-1365U |
| generacion_procesador | Texto | Generación del procesador | 13th Gen |
| ram_total_gb | Numérico | RAM total en GB | 16 |
| ram_configuracion | Texto | Configuración de RAM | 2x8GB |
| ram_tipo | Texto | DDR3, DDR4, DDR5 | DDR4 |
| almacenamiento_gb | Numérico | Almacenamiento en GB | 512 |
| almacenamiento_tipo | Texto | HDD, SSD, NVMe, eMMC | NVMe |
| sistema_operativo | Texto | Sistema operativo | Windows 11 Pro |

---

## 🔒 VALIDACIONES IMPLEMENTADAS

### Validaciones Bloqueantes (Errores)
- ❌ Serie vacía
- ❌ Serie duplicada en la base de datos
- ❌ Área inválida (debe ser sistemas, operaciones o laboratorio)
- ❌ Área no coincide con el perfil del usuario (si no es admin)
- ❌ Tipo de ítem no existe para el área especificada
- ❌ Precio inválido o negativo
- ❌ Fecha de adquisición inválida o vacía
- ❌ Ambiente especificado no existe
- ❌ Lote especificado no existe

### Validaciones de Advertencia (No bloquean)
- ⚠️ Sin ubicación asignada
- ⚠️ Sin fecha de garantía
- ⚠️ Estado inválido (se usará 'nuevo' por defecto)
- ⚠️ Fecha de garantía inválida

---

## 🔐 PERMISOS Y RESTRICCIONES

### Acceso
- **Supervisores**: Solo pueden importar ítems de su área asignada
- **Administradores**: Pueden importar ítems de cualquier área

### Restricciones
- Máximo 1000 ítems por archivo
- Solo archivos .xlsx (Excel 2007+)
- El código UTP se genera automáticamente (no se debe incluir en el Excel)

---

## 🚀 FLUJO DE USO

### Paso 1: Descargar Plantilla
1. Iniciar sesión como supervisor o admin
2. Ir a menú **Inventario** → **Importar desde Excel**
3. Hacer clic en **Descargar Plantilla**
4. Se descarga `plantilla_items_inventario.xlsx`

### Paso 2: Llenar Plantilla
1. Abrir el archivo en Excel
2. Revisar la hoja "Instrucciones"
3. Llenar la hoja "Plantilla Items" con los datos
4. Asegurarse de llenar todas las columnas obligatorias
5. Guardar el archivo

### Paso 3: Subir Archivo
1. Ir a **Inventario** → **Importar desde Excel**
2. Seleccionar el archivo completado
3. (Opcional) Marcar "Crear un nuevo lote" y agregar descripción
4. (Opcional) Seleccionar un lote existente
5. Hacer clic en **Vista Previa**

### Paso 4: Revisar Vista Previa
1. Revisar el resumen estadístico
2. Revisar la tabla de ítems fila por fila
3. Si hay errores en rojo, corregir el Excel y volver a subir
4. Si todo está correcto, hacer clic en **Confirmar Importación**

### Paso 5: Confirmación
1. Confirmar la importación en el diálogo
2. Esperar a que se procesen los ítems
3. Ver el mensaje de éxito con la cantidad importada
4. Los ítems aparecerán en el listado de inventario

---

## 📁 ARCHIVOS MODIFICADOS/CREADOS

### Archivos Nuevos
- `templates/productos/item_importar.html` - Template de importación

### Archivos Modificados
- `productos/views.py` - 3 nuevas vistas:
  - `ItemImportarPlantillaView` (líneas 1552-1718)
  - `ItemImportarView` (líneas 1721-1933)
  - `ItemImportarConfirmarView` (líneas 1936-2106)
- `productos/urls.py` - 3 nuevas rutas (líneas 13-15)
- `templates/base.html` - Enlace en navbar (líneas 523-525)
- `requirements.txt` - Agregado `openpyxl==3.1.2`

---

## 🧪 PRUEBAS RECOMENDADAS

### Caso 1: Importación Exitosa
- Descargar plantilla
- Llenar 5 ítems válidos del área Sistemas
- Subir archivo
- Verificar vista previa (5 válidos)
- Confirmar importación
- Verificar que los 5 ítems estén en el inventario

### Caso 2: Errores de Validación
- Crear archivo con series duplicadas
- Crear archivo con área inválida
- Crear archivo con tipo de ítem inexistente
- Verificar que se muestren los errores en rojo
- Verificar que no se pueda confirmar la importación

### Caso 3: Advertencias
- Crear ítems sin ubicación
- Crear ítems sin garantía
- Verificar que se muestren advertencias en amarillo
- Verificar que sí se pueda confirmar la importación

### Caso 4: Restricción por Área
- Como supervisor de Sistemas, intentar importar ítems de Operaciones
- Verificar que se muestre error de permisos

### Caso 5: Creación de Lote
- Marcar "Crear un nuevo lote"
- Agregar descripción del lote
- Importar ítems
- Verificar que se haya creado el lote
- Verificar que los ítems estén asociados al lote

---

## 🐛 MANEJO DE ERRORES

### Error: "Debe seleccionar un archivo Excel"
- **Causa**: No se seleccionó archivo
- **Solución**: Seleccionar un archivo .xlsx

### Error: "El archivo debe ser formato .xlsx"
- **Causa**: Archivo en formato incorrecto (ej: .xls, .csv)
- **Solución**: Guardar el archivo como .xlsx (Excel 2007+)

### Error: "Falta la columna obligatoria: X"
- **Causa**: La plantilla fue modificada y falta una columna
- **Solución**: Descargar nuevamente la plantilla

### Error: "Serie X ya existe en el sistema"
- **Causa**: Número de serie duplicado
- **Solución**: Cambiar el número de serie a uno único

### Error: "Tipo de ítem 'X' no existe para el área Y"
- **Causa**: El tipo de ítem no está registrado
- **Solución**: Crear el tipo de ítem primero o corregir el nombre

### Error: "No tienes permiso para crear ítems en el área X"
- **Causa**: Supervisor intentando importar ítems de otra área
- **Solución**: Solo importar ítems del área asignada

---

## 💡 MEJORAS FUTURAS (OPCIONALES)

1. **Exportar a Excel**: Exportar el inventario actual a Excel
2. **Importación en background**: Para archivos muy grandes (>1000 ítems)
3. **Validación de tipos de RAM y almacenamiento**: Dropdown con opciones válidas
4. **Importación parcial**: Opción para importar solo los válidos
5. **Histórico de importaciones**: Registro de todas las importaciones realizadas
6. **Preview de especificaciones**: Mostrar specs en la vista previa
7. **Asignación de usuarios**: Permitir asignar usuarios durante importación

---

## 📝 NOTAS TÉCNICAS

- La importación usa transacciones atómicas para garantizar integridad
- Los códigos UTP se generan secuencialmente por área y año
- Las especificaciones de Sistemas solo se crean si hay datos
- La sesión se usa para almacenar la vista previa temporalmente
- El límite de 1000 ítems previene timeouts del servidor

---

**Fin de la documentación**
