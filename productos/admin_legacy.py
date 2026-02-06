from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Area, Campus, Sede, Pabellon, Ambiente, TipoItem, PerfilUsuario, Item,
    EspecificacionesSistemas, Movimiento, MovimientoItem, HistorialCambio,
    Notificacion, MarcaEquipo, ModeloEquipo, ProcesadorEquipo, Colaborador,
    Proveedor, Contrato, AnexoContrato, Lote, Mantenimiento, GarantiaRegistro,
    Gerencia, SoftwareEstandar, ActaEntrega, ActaItem, ActaFoto, ActaSoftware
)


# ============================================================================
# INLINE PARA PERFIL DE USUARIO
# ============================================================================

class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil'
    fk_name = 'usuario'
    fields = ('rol', 'area', 'campus', 'campus_asignados', 'telefono', 'activo')
    filter_horizontal = ('campus_asignados',)

    def get_readonly_fields(self, request, obj=None):
        return []


class UserAdmin(BaseUserAdmin):
    inlines = (PerfilUsuarioInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_rol', 'get_campus_info', 'get_area_o_depto', 'is_active')
    list_filter = BaseUserAdmin.list_filter + ('perfil__rol', 'perfil__campus', 'perfil__area')

    def get_rol(self, obj):
        if hasattr(obj, 'perfil'):
            return obj.perfil.get_rol_display()
        return '-'
    get_rol.short_description = 'Rol'

    def get_campus_info(self, obj):
        if hasattr(obj, 'perfil'):
            perfil = obj.perfil
            if perfil.rol in ['admin', 'gerente', 'almacen']:
                return 'Todos'
            elif perfil.rol == 'supervisor':
                campus_list = perfil.campus_asignados.all()
                if campus_list:
                    return ', '.join([c.nombre for c in campus_list[:3]])
                return 'Sin asignar'
            elif perfil.rol == 'auxiliar':
                return perfil.campus.nombre if perfil.campus else 'Sin asignar'
        return '-'
    get_campus_info.short_description = 'Campus'

    def get_area_o_depto(self, obj):
        if hasattr(obj, 'perfil'):
            if obj.perfil.area:
                return obj.perfil.area.nombre
            return 'Todas'
        return '-'
    get_area_o_depto.short_description = 'Área'


# Re-registrar UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# ============================================================================
# MODELOS DE CONFIGURACIÓN
# ============================================================================

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'descripcion', 'activo', 'total_items')
    list_filter = ('activo',)
    search_fields = ('nombre', 'codigo')
    ordering = ('nombre',)
    
    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Total Ítems'


# ============================================================================
# MODELOS DE UBICACIÓN (Jerarquía)
# ============================================================================

@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'activo', 'total_sedes')
    list_filter = ('activo',)
    search_fields = ('nombre', 'codigo')
    ordering = ('nombre',)
    
    def total_sedes(self, obj):
        return obj.sedes.count()
    total_sedes.short_description = 'Sedes'


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_sede', 'codigo', 'campus', 'activo', 'total_pabellones')
    list_filter = ('campus', 'activo')
    search_fields = ('nombre', 'codigo', 'codigo_sede', 'campus__nombre')
    ordering = ('campus', 'codigo_sede')

    def total_pabellones(self, obj):
        return obj.pabellones.count()
    total_pabellones.short_description = 'Pabellones'


@admin.register(Pabellon)
class PabellonAdmin(admin.ModelAdmin):
    list_display = ('letra', 'nombre', 'sede', 'pisos', 'sotanos', 'activo', 'total_ambientes')
    list_filter = ('sede__campus', 'sede', 'activo')
    search_fields = ('letra', 'nombre', 'sede__nombre', 'sede__campus__nombre')
    ordering = ('sede', 'letra')

    def total_ambientes(self, obj):
        return obj.ambientes.count()
    total_ambientes.short_description = 'Ambientes'


@admin.register(Ambiente)
class AmbienteAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'tipo', 'pabellon', 'piso', 'numero', 'get_campus', 'activo', 'total_items')
    list_filter = ('pabellon__sede__campus', 'pabellon__sede', 'pabellon', 'tipo', 'activo')
    search_fields = ('codigo', 'nombre', 'pabellon__letra', 'pabellon__sede__nombre')
    ordering = ('pabellon__sede__campus', 'pabellon__sede', 'pabellon', 'piso', 'numero')
    readonly_fields = ('codigo',)

    fieldsets = (
        ('Ubicación', {
            'fields': ('pabellon', 'piso', 'numero')
        }),
        ('Ambiente', {
            'fields': ('tipo', 'nombre', 'capacidad')
        }),
        ('Información Adicional', {
            'fields': ('descripcion', 'activo'),
            'classes': ('collapse',)
        }),
        ('Código Generado', {
            'fields': ('codigo',),
            'classes': ('collapse',)
        }),
    )

    def get_campus(self, obj):
        return obj.pabellon.sede.campus.nombre
    get_campus.short_description = 'Campus'
    get_campus.admin_order_field = 'pabellon__sede__campus__nombre'

    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Ítems'


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('ruc', 'razon_social', 'nombre_comercial', 'telefono', 'email', 'contacto', 'activo')
    list_filter = ('activo',)
    search_fields = ('ruc', 'razon_social', 'nombre_comercial', 'contacto')
    ordering = ('razon_social',)


class AnexoContratoInline(admin.TabularInline):
    model = AnexoContrato
    extra = 0
    fields = ('numero_anexo', 'fecha', 'descripcion', 'monto_modificacion')


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('numero_contrato', 'proveedor', 'estado', 'fecha_inicio', 'fecha_fin', 'monto_total')
    list_filter = ('estado', 'proveedor')
    search_fields = ('numero_contrato', 'proveedor__razon_social', 'descripcion')
    ordering = ('-fecha_inicio',)
    readonly_fields = ('creado_por', 'creado_en', 'modificado_en')
    date_hierarchy = 'fecha_inicio'
    inlines = [AnexoContratoInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('codigo_interno', 'codigo_lote', 'descripcion', 'contrato', 'fecha_adquisicion', 'cantidad_items', 'activo')
    list_filter = ('activo', 'contrato__proveedor')
    search_fields = ('codigo_interno', 'codigo_lote', 'descripcion')
    ordering = ('-fecha_adquisicion',)
    readonly_fields = ('codigo_interno', 'creado_por', 'creado_en')

    def cantidad_items(self, obj):
        return obj.cantidad_items
    cantidad_items.short_description = 'Ítems'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(TipoItem)
class TipoItemAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'area', 'descripcion', 'activo', 'total_items')
    list_filter = ('area', 'activo')
    search_fields = ('nombre',)
    ordering = ('area', 'nombre')

    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Total'


# ============================================================================
# CATÁLOGOS DE EQUIPOS (Marca, Modelo, Procesador)
# ============================================================================

class ModeloEquipoInline(admin.TabularInline):
    model = ModeloEquipo
    extra = 1
    fields = ('nombre', 'activo')


@admin.register(MarcaEquipo)
class MarcaEquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'total_modelos')
    list_filter = ('activo',)
    search_fields = ('nombre',)
    ordering = ('nombre',)
    inlines = [ModeloEquipoInline]

    def total_modelos(self, obj):
        return obj.modelos.count()
    total_modelos.short_description = 'Modelos'


@admin.register(ModeloEquipo)
class ModeloEquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'marca', 'activo')
    list_filter = ('marca', 'activo')
    search_fields = ('nombre', 'marca__nombre')
    ordering = ('marca__nombre', 'nombre')


@admin.register(ProcesadorEquipo)
class ProcesadorEquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)
    ordering = ('nombre',)


# ============================================================================
# INLINE PARA ESPECIFICACIONES DE SISTEMAS
# ============================================================================

class EspecificacionesSistemasInline(admin.StackedInline):
    model = EspecificacionesSistemas
    can_delete = False
    verbose_name = 'Especificaciones Técnicas (Sistemas)'
    verbose_name_plural = 'Especificaciones Técnicas (Sistemas)'

    fieldsets = (
        ('Identificación', {
            'fields': ('marca_equipo', 'modelo_equipo')
        }),
        ('Procesador', {
            'fields': ('procesador_equipo', 'generacion_procesador')
        }),
        ('Memoria RAM', {
            'fields': ('ram_total_gb', 'ram_configuracion', 'ram_tipo')
        }),
        ('Almacenamiento', {
            'fields': ('almacenamiento_gb', 'almacenamiento_tipo')
        }),
        ('Software', {
            'fields': ('sistema_operativo',)
        }),
    )


class HistorialCambioInline(admin.TabularInline):
    model = HistorialCambio
    extra = 0
    readonly_fields = ('usuario', 'fecha', 'campo', 'valor_anterior', 'valor_nuevo')
    can_delete = False
    ordering = ('-fecha',)
    
    def has_add_permission(self, request, obj=None):
        return False


class MovimientoInline(admin.TabularInline):
    model = Movimiento
    fk_name = 'item'  # Especificar que usa el FK principal, no item_reemplazo
    extra = 0
    readonly_fields = ('tipo', 'estado', 'solicitado_por', 'aprobado_por', 'fecha_solicitud')
    can_delete = False
    ordering = ('-fecha_solicitud',)
    show_change_link = True

    fields = ('tipo', 'estado', 'motivo', 'solicitado_por', 'aprobado_por', 'fecha_solicitud')

    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# ITEM PRINCIPAL
# ============================================================================

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        'codigo_utp', 'nombre', 'area', 'tipo_item', 'ambiente', 
        'estado_badge', 'usuario_asignado', 'garantia_badge', 'leasing_badge'
    )
    list_filter = ('area', 'estado', 'tipo_item', 'ambiente__pabellon__sede__campus', 'es_leasing')
    search_fields = ('codigo_utp', 'serie', 'nombre', 'descripcion')
    ordering = ('-creado_en',)
    readonly_fields = ('codigo_utp', 'creado_por', 'creado_en', 'modificado_por', 'modificado_en')
    autocomplete_fields = ('tipo_item', 'ambiente', 'usuario_asignado')
    date_hierarchy = 'fecha_adquisicion'
    
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo_utp', 'serie', 'nombre', 'descripcion')
        }),
        ('Clasificación', {
            'fields': ('area', 'tipo_item', 'ambiente')
        }),
        ('Estado y Asignación', {
            'fields': ('estado', 'usuario_asignado', 'observaciones')
        }),
        ('Información Económica', {
            'fields': ('fecha_adquisicion', 'precio')
        }),
        ('Garantía', {
            'fields': ('garantia_hasta',),
            'classes': ('collapse',)
        }),
        ('Leasing', {
            'fields': ('es_leasing', 'leasing_empresa', 'leasing_contrato', 'leasing_vencimiento'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'creado_en', 'modificado_por', 'modificado_en'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [EspecificacionesSistemasInline, MovimientoInline, HistorialCambioInline]
    
    def get_inlines(self, request, obj=None):
        """Solo mostrar inline de especificaciones si es del área de Sistemas."""
        inlines = [MovimientoInline, HistorialCambioInline]
        if obj and obj.area and obj.area.codigo == 'sistemas':
            inlines.insert(0, EspecificacionesSistemasInline)
        return inlines
    
    def estado_badge(self, obj):
        colores = {
            'backup': '#22c55e',       # Verde
            'custodia': '#8b5cf6',     # Púrpura
            'instalado': '#3b82f6',    # Azul
            'garantia': '#f59e0b',     # Naranja
            'mantenimiento': '#eab308', # Amarillo
            'transito': '#06b6d4',     # Cyan
            'baja': '#ef4444',         # Rojo
        }
        color = colores.get(obj.estado, '#6b7280')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; border-radius:4px; font-size:11px;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def garantia_badge(self, obj):
        if obj.en_garantia:
            return format_html(
                '<span style="background:#22c55e; color:white; padding:2px 6px; border-radius:4px; font-size:10px;">✓ Vigente</span>'
            )
        elif obj.garantia_hasta:
            return format_html(
                '<span style="background:#ef4444; color:white; padding:2px 6px; border-radius:4px; font-size:10px;">Vencida</span>'
            )
        return '-'
    garantia_badge.short_description = 'Garantía'
    
    def leasing_badge(self, obj):
        if obj.es_leasing:
            if obj.leasing_vigente:
                return format_html(
                    '<span style="background:#8b5cf6; color:white; padding:2px 6px; border-radius:4px; font-size:10px;">Leasing</span>'
                )
            return format_html(
                '<span style="background:#f59e0b; color:white; padding:2px 6px; border-radius:4px; font-size:10px;">L. Vencido</span>'
            )
        return '-'
    leasing_badge.short_description = 'Leasing'
    
    def save_model(self, request, obj, form, change):
        """Guardar el usuario que crea/modifica."""
        if not change:
            obj.creado_por = request.user
            # Auto-generar código UTP si está vacío
            if not obj.codigo_utp:
                obj.codigo_utp = Item.generar_codigo_utp(obj.area.codigo)
        obj.modificado_por = request.user
        super().save_model(request, obj, form, change)


# ============================================================================
# MOVIMIENTOS
# ============================================================================

class MovimientoItemInline(admin.TabularInline):
    model = MovimientoItem
    extra = 0
    fields = ('item', 'estado_item_destino', 'observaciones')
    readonly_fields = ('agregado_en',)


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = (
        'item', 'tipo', 'estado_badge', 'campus_info',
        'solicitado_por', 'aprobado_por', 'fecha_solicitud'
    )
    list_filter = ('estado', 'tipo', 'ambiente_origen__pabellon__sede__campus')
    search_fields = ('item__codigo_interno', 'item__codigo_utp', 'item__nombre', 'motivo')
    ordering = ('-fecha_solicitud',)
    readonly_fields = ('fecha_solicitud', 'fecha_aprobacion', 'fecha_en_ejecucion', 'fecha_en_transito', 'fecha_ejecucion')
    autocomplete_fields = ('item', 'item_reemplazo', 'ambiente_origen', 'ambiente_destino')
    date_hierarchy = 'fecha_solicitud'

    fieldsets = (
        ('Información del Movimiento', {
            'fields': ('item', 'tipo', 'estado')
        }),
        ('Ítem de Reemplazo', {
            'fields': ('item_reemplazo', 'reemplazo_es_temporal'),
            'classes': ('collapse',),
            'description': 'Para mantenimiento, garantía, reemplazo o leasing'
        }),
        ('Ubicaciones', {
            'fields': ('ambiente_origen', 'ambiente_destino', 'estado_item_destino')
        }),
        ('Asignación de Colaborador', {
            'fields': ('colaborador_anterior', 'colaborador_nuevo'),
            'classes': ('collapse',)
        }),
        ('Préstamo', {
            'fields': ('fecha_devolucion_esperada', 'fecha_devolucion_real'),
            'classes': ('collapse',)
        }),
        ('Justificación', {
            'fields': ('motivo', 'observaciones')
        }),
        ('Flujo de Trabajo', {
            'fields': ('solicitado_por', 'aprobado_por', 'ejecutado_por', 'motivo_rechazo')
        }),
        ('Evidencia', {
            'fields': ('foto_evidencia', 'notas_evidencia'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('fecha_solicitud', 'fecha_aprobacion', 'fecha_en_ejecucion', 'fecha_en_transito', 'fecha_ejecucion'),
            'classes': ('collapse',)
        }),
    )

    actions = ['aprobar_movimientos', 'rechazar_movimientos']
    inlines = [MovimientoItemInline]

    def estado_badge(self, obj):
        colores = {
            'pendiente': '#f59e0b',
            'aprobado': '#22c55e',
            'en_ejecucion': '#06b6d4',
            'en_transito': '#8b5cf6',
            'ejecutado': '#3b82f6',
            'rechazado': '#ef4444',
            'cancelado': '#6b7280',
        }
        color = colores.get(obj.estado, '#6b7280')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; border-radius:4px; font-size:11px;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

    def campus_info(self, obj):
        origen = obj.campus_origen.codigo if obj.campus_origen else '?'
        destino = obj.campus_destino.codigo if obj.campus_destino else '?'
        if obj.es_entre_campus:
            return format_html(
                '<span style="color:#8b5cf6; font-weight:bold;">{} → {}</span>',
                origen, destino
            )
        return f"{origen}"
    campus_info.short_description = 'Campus'

    @admin.action(description='Aprobar movimientos seleccionados')
    def aprobar_movimientos(self, request, queryset):
        count = 0
        for mov in queryset.filter(estado='pendiente'):
            mov.aprobar(request.user)
            count += 1
        self.message_user(request, f'{count} movimiento(s) aprobado(s).')

    @admin.action(description='Rechazar movimientos seleccionados')
    def rechazar_movimientos(self, request, queryset):
        count = 0
        for mov in queryset.filter(estado='pendiente'):
            mov.rechazar(request.user, 'Rechazado en lote desde admin')
            count += 1
        self.message_user(request, f'{count} movimiento(s) rechazado(s).')


# ============================================================================
# HISTORIAL DE CAMBIOS
# ============================================================================

@admin.register(HistorialCambio)
class HistorialCambioAdmin(admin.ModelAdmin):
    list_display = ('item', 'campo', 'valor_anterior', 'valor_nuevo', 'usuario', 'fecha')
    list_filter = ('campo', 'fecha')
    search_fields = ('item__codigo_utp', 'campo')
    ordering = ('-fecha',)
    readonly_fields = ('item', 'usuario', 'fecha', 'campo', 'valor_anterior', 'valor_nuevo')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================================
# NOTIFICACIONES
# ============================================================================

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'usuario', 'tipo', 'leida', 'urgente', 'fecha')
    list_filter = ('tipo', 'leida', 'urgente')
    search_fields = ('titulo', 'mensaje', 'usuario__username')
    ordering = ('-fecha',)
    readonly_fields = ('fecha',)
    
    actions = ['marcar_como_leidas']
    
    @admin.action(description='Marcar como leídas')
    def marcar_como_leidas(self, request, queryset):
        queryset.update(leida=True)
        self.message_user(request, f'{queryset.count()} notificación(es) marcada(s) como leída(s).')


# ============================================================================
# COLABORADORES
# ============================================================================

@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ('dni', 'nombre_completo', 'cargo', 'gerencia', 'sede', 'activo')
    list_filter = ('gerencia', 'sede', 'activo')
    search_fields = ('dni', 'nombre_completo', 'cargo', 'correo')
    ordering = ('nombre_completo',)

    fieldsets = (
        ('Identificación', {
            'fields': ('dni', 'nombre_completo')
        }),
        ('Datos Laborales', {
            'fields': ('cargo', 'gerencia', 'sede')
        }),
        ('Contacto', {
            'fields': ('anexo', 'correo')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )


# ============================================================================
# GERENCIAS Y SOFTWARE
# ============================================================================

@admin.register(Gerencia)
class GerenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(SoftwareEstandar)
class SoftwareEstandarAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'es_basico', 'orden', 'activo')
    list_filter = ('es_basico', 'activo')
    search_fields = ('nombre',)
    ordering = ('orden', 'nombre')


# ============================================================================
# MANTENIMIENTO Y GARANTÍAS
# ============================================================================

@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ('item', 'tipo', 'estado_badge', 'fecha_programada', 'responsable', 'tecnico_asignado', 'resultado')
    list_filter = ('tipo', 'estado', 'resultado')
    search_fields = ('item__codigo_interno', 'item__codigo_utp', 'item__nombre', 'descripcion_problema', 'tecnico_asignado')
    ordering = ('-fecha_programada',)
    readonly_fields = ('creado_por', 'creado_en', 'actualizado_en')
    date_hierarchy = 'fecha_programada'

    fieldsets = (
        ('Equipo', {
            'fields': ('item', 'tipo')
        }),
        ('Programación', {
            'fields': ('estado', 'fecha_programada', 'fecha_inicio', 'fecha_finalizacion')
        }),
        ('Trabajo', {
            'fields': ('descripcion_problema', 'trabajo_realizado', 'resultado')
        }),
        ('Responsables', {
            'fields': ('responsable', 'tecnico_asignado', 'proveedor_servicio')
        }),
        ('Costo y Próximo', {
            'fields': ('costo', 'proximo_mantenimiento'),
            'classes': ('collapse',)
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )

    def estado_badge(self, obj):
        colores = {
            'pendiente': '#f59e0b',
            'en_proceso': '#06b6d4',
            'completado': '#22c55e',
            'cancelado': '#6b7280',
        }
        color = colores.get(obj.estado, '#6b7280')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; border-radius:4px; font-size:11px;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(GarantiaRegistro)
class GarantiaRegistroAdmin(admin.ModelAdmin):
    list_display = ('item', 'estado_badge', 'tipo_problema', 'proveedor', 'numero_caso', 'fecha_reporte', 'fecha_envio', 'fecha_recepcion')
    list_filter = ('estado', 'tipo_problema', 'proveedor')
    search_fields = ('item__codigo_interno', 'item__codigo_utp', 'item__nombre', 'numero_caso', 'descripcion_problema')
    ordering = ('-creado_en',)
    readonly_fields = ('fecha_reporte', 'creado_por', 'creado_en', 'actualizado_en')

    fieldsets = (
        ('Equipo', {
            'fields': ('item',)
        }),
        ('Problema', {
            'fields': ('tipo_problema', 'descripcion_problema')
        }),
        ('Estado y Proveedor', {
            'fields': ('estado', 'proveedor', 'numero_caso', 'contacto_proveedor')
        }),
        ('Fechas', {
            'fields': ('fecha_reporte', 'fecha_envio', 'fecha_recepcion')
        }),
        ('Resultado', {
            'fields': ('diagnostico_proveedor', 'solucion_aplicada', 'equipo_reemplazo'),
            'classes': ('collapse',)
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )

    def estado_badge(self, obj):
        colores = {
            'pendiente': '#f59e0b',
            'enviado': '#3b82f6',
            'en_revision': '#6b7280',
            'reparado': '#22c55e',
            'reemplazado': '#8b5cf6',
            'rechazado': '#ef4444',
            'devuelto': '#06b6d4',
            'cancelado': '#374151',
        }
        color = colores.get(obj.estado, '#6b7280')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; border-radius:4px; font-size:11px;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


# ============================================================================
# ACTAS DE ENTREGA/DEVOLUCIÓN
# ============================================================================

class ActaItemInline(admin.TabularInline):
    model = ActaItem
    extra = 0
    fields = ('item', 'acc_cargador', 'acc_cable_seguridad', 'acc_bateria', 'acc_maletin', 'acc_cable_red', 'acc_teclado_mouse')


class ActaFotoInline(admin.TabularInline):
    model = ActaFoto
    extra = 0
    fields = ('foto', 'descripcion')


class ActaSoftwareInline(admin.TabularInline):
    model = ActaSoftware
    extra = 0
    fields = ('software',)


@admin.register(ActaEntrega)
class ActaEntregaAdmin(admin.ModelAdmin):
    list_display = ('numero_acta', 'tipo', 'colaborador', 'cantidad_items', 'correo_enviado', 'creado_por', 'fecha')
    list_filter = ('tipo', 'correo_enviado')
    search_fields = ('numero_acta', 'colaborador__nombre_completo', 'colaborador__dni')
    ordering = ('-fecha',)
    readonly_fields = ('numero_acta', 'fecha', 'fecha_envio_correo')
    date_hierarchy = 'fecha'
    inlines = [ActaItemInline, ActaSoftwareInline, ActaFotoInline]

    def cantidad_items(self, obj):
        return obj.cantidad_items
    cantidad_items.short_description = 'Ítems'


# ============================================================================
# CONFIGURACIÓN DEL SITIO ADMIN
# ============================================================================

admin.site.site_header = 'Inventario UTP'
admin.site.site_title = 'Inventario UTP'
admin.site.index_title = 'Panel de Administración'
