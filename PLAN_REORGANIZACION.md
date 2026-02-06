# Plan de Reorganización - Inventario UTP

## Estructura Actual (Problemática)

```
productos/
├── models.py          # 2,347 líneas - 29 modelos en un solo archivo
├── views.py           # 4,996 líneas - 95+ vistas en un solo archivo
├── forms_legacy.py    # 1,365 líneas - todos los formularios
├── admin.py           # 780 líneas - toda la configuración admin
├── urls.py            # 169 líneas
├── forms/             # Carpeta nueva parcialmente usada
│   ├── base.py
│   └── item_forms.py
├── utils/
│   ├── acta_pdf.py
│   ├── acta_email.py
│   └── export_utils.py
└── management/commands/
```

**Problemas:**
1. Archivos monolíticos muy difíciles de mantener
2. Mezcla de dominios (Items, Movimientos, Actas, Garantías, etc.)
3. No sigue el principio de responsabilidad única
4. Difícil de escalar y testear

---

## Estructura Propuesta

Seguiremos el patrón **"Django App por Dominio"** + **"Package per Layer"**:

```
productos/                          # App principal (core)
├── __init__.py
├── apps.py
├── constants.py                    # Constantes compartidas (ESTADOS, TIPOS, etc.)
├── mixins.py                       # Mixins de permisos y filtros
├── validators.py                   # Validadores compartidos
├── signals.py
├── context_processors.py
├── ratelimit.py
│
├── models/                         # Modelos divididos por dominio
│   ├── __init__.py                 # Re-exporta todos los modelos
│   ├── ubicacion.py                # Area, Campus, Sede, Pabellon, Ambiente
│   ├── item.py                     # Item, TipoItem, EspecificacionesSistemas
│   ├── equipo.py                   # MarcaEquipo, ModeloEquipo, ProcesadorEquipo
│   ├── movimiento.py               # Movimiento, MovimientoItem
│   ├── proveedor.py                # Proveedor, Contrato, AnexoContrato, Lote
│   ├── mantenimiento.py            # Mantenimiento
│   ├── garantia.py                 # GarantiaRegistro
│   ├── acta.py                     # ActaEntrega, ActaItem, ActaFoto, ActaSoftware
│   ├── usuario.py                  # PerfilUsuario
│   ├── organizacion.py             # Gerencia, Colaborador, SoftwareEstandar
│   └── auditoria.py                # HistorialCambio, Notificacion
│
├── views/                          # Vistas divididas por dominio
│   ├── __init__.py                 # Re-exporta todas las vistas
│   ├── dashboard.py                # HomeView, DashboardView
│   ├── item.py                     # ItemListView, ItemCreateView, etc.
│   ├── movimiento.py               # MovimientoListView, aprobar, rechazar, etc.
│   ├── ubicacion.py                # Campus, Sede, Pabellon, Ambiente views
│   ├── proveedor.py                # Proveedor, Contrato, Lote views
│   ├── mantenimiento.py            # Mantenimiento views
│   ├── garantia.py                 # Garantía views
│   ├── acta.py                     # Acta views
│   ├── colaborador.py              # Colaborador, Gerencia views
│   ├── catalogo.py                 # TipoItem, Marca, Modelo, Procesador, Software
│   ├── reportes.py                 # Reportes y exportaciones
│   ├── notificacion.py             # Notificaciones
│   └── api.py                      # Endpoints AJAX (búsquedas, autocomplete)
│
├── forms/                          # Formularios divididos por dominio
│   ├── __init__.py
│   ├── base.py                     # Formularios base y widgets
│   ├── item.py                     # ItemForm, ItemImportForm
│   ├── movimiento.py               # MovimientoForm
│   ├── ubicacion.py                # AmbienteForm, CampusForm, etc.
│   ├── proveedor.py                # ProveedorForm, ContratoForm, LoteForm
│   ├── mantenimiento.py            # MantenimientoForm
│   ├── garantia.py                 # GarantiaRegistroForm
│   ├── acta.py                     # ActaForm
│   └── organizacion.py             # ColaboradorForm, GerenciaForm
│
├── admin/                          # Admin dividido por dominio
│   ├── __init__.py                 # Registra todos los admins
│   ├── item.py                     # ItemAdmin, TipoItemAdmin
│   ├── ubicacion.py                # Campus, Sede, Pabellon, Ambiente
│   ├── movimiento.py               # MovimientoAdmin
│   ├── proveedor.py                # Proveedor, Contrato, Lote
│   ├── mantenimiento.py            # MantenimientoAdmin
│   ├── garantia.py                 # GarantiaRegistroAdmin
│   ├── acta.py                     # ActaEntregaAdmin
│   ├── usuario.py                  # UserAdmin con PerfilUsuario
│   └── organizacion.py             # Gerencia, Colaborador, Software
│
├── urls/                           # URLs divididas por dominio
│   ├── __init__.py                 # URL principal que incluye las demás
│   ├── item.py
│   ├── movimiento.py
│   ├── ubicacion.py
│   ├── proveedor.py
│   ├── mantenimiento.py
│   ├── garantia.py
│   ├── acta.py
│   ├── colaborador.py
│   ├── catalogo.py
│   ├── reportes.py
│   └── api.py
│
├── services/                       # Lógica de negocio compleja (nuevo)
│   ├── __init__.py
│   ├── movimiento_service.py       # Flujo de trabajo de movimientos
│   ├── acta_service.py             # Generación de actas, PDF, email
│   ├── importacion_service.py      # Importación de Excel
│   └── exportacion_service.py      # Exportación de reportes
│
├── utils/                          # Utilidades
│   ├── __init__.py
│   ├── pdf.py                      # Generación de PDFs
│   ├── email.py                    # Envío de correos
│   ├── excel.py                    # Manejo de Excel
│   └── helpers.py                  # Funciones auxiliares
│
├── templatetags/
│   ├── __init__.py
│   └── productos_filters.py
│
├── management/
│   └── commands/
│       ├── __init__.py
│       └── ...
│
├── migrations/
│   └── ...
│
└── tests/                          # Tests organizados por módulo
    ├── __init__.py
    ├── test_models/
    ├── test_views/
    └── test_services/
```

---

## Beneficios de la Nueva Estructura

1. **Separación de responsabilidades**: Cada archivo tiene un propósito claro
2. **Escalabilidad**: Fácil agregar nuevos módulos sin afectar otros
3. **Mantenibilidad**: Archivos más pequeños y enfocados (~200-400 líneas)
4. **Testabilidad**: Cada módulo puede testearse independientemente
5. **Colaboración**: Varios desarrolladores pueden trabajar sin conflictos
6. **Navegación**: Fácil encontrar código por dominio

---

## Plan de Migración (Orden de Ejecución)

### Fase 1: Preparación
1. Crear estructura de carpetas vacías
2. Crear archivos `__init__.py` con imports

### Fase 2: Models (Base - sin dependencias)
1. Crear `models/ubicacion.py` - Area, Campus, Sede, Pabellon, Ambiente
2. Crear `models/equipo.py` - MarcaEquipo, ModeloEquipo, ProcesadorEquipo
3. Crear `models/organizacion.py` - Gerencia, Colaborador, SoftwareEstandar
4. Crear `models/usuario.py` - PerfilUsuario
5. Crear `models/proveedor.py` - Proveedor, Contrato, AnexoContrato, Lote
6. Crear `models/item.py` - TipoItem, Item, EspecificacionesSistemas
7. Crear `models/movimiento.py` - Movimiento, MovimientoItem
8. Crear `models/mantenimiento.py` - Mantenimiento
9. Crear `models/garantia.py` - GarantiaRegistro
10. Crear `models/acta.py` - ActaEntrega, ActaItem, ActaFoto, ActaSoftware
11. Crear `models/auditoria.py` - HistorialCambio, Notificacion
12. Actualizar `models/__init__.py` para re-exportar todo

### Fase 3: Forms
1. Migrar forms a sus respectivos archivos
2. Actualizar `forms/__init__.py`

### Fase 4: Admin
1. Dividir admin.py en módulos
2. Actualizar `admin/__init__.py`

### Fase 5: Views
1. Crear `mixins.py` con los mixins de permisos
2. Dividir views en módulos por dominio
3. Actualizar `views/__init__.py`

### Fase 6: URLs
1. Dividir urls.py en módulos
2. Crear `urls/__init__.py` principal

### Fase 7: Services (Nuevo)
1. Extraer lógica compleja de las views a services

### Fase 8: Limpieza
1. Eliminar archivos monolíticos antiguos
2. Verificar que todo funciona
3. Actualizar documentación

---

## Notas Importantes

- **Compatibilidad**: Los imports desde otras partes del proyecto seguirán funcionando gracias a los re-exports en `__init__.py`
- **Migraciones**: No se tocan - Django las maneja automáticamente
- **Templates**: No se mueven - estructura actual está bien
- **Deploy**: Después de cada fase, verificar en producción
