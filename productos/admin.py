from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Area, Campus, Sede, Pabellon, Ambiente, TipoItem, PerfilUsuario, Item, 
    EspecificacionesSistemas, Movimiento, HistorialCambio, Notificacion
)


# ============================================================================
# INLINE PARA PERFIL DE USUARIO
# ============================================================================

class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil'
    fk_name = 'usuario'
    fields = ('rol', 'area', 'campus', 'campus_asignados', 'departamento', 'telefono', 'activo')
    filter_horizontal = ('campus_asignados',)

    def get_readonly_fields(self, request, obj=None):
        # Si ya es externo, mostrar is_active como referencia
        return []

    class Media:
        js = ('admin/js/perfil_campus.js',)  # JS para mostrar/ocultar campos según rol


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
            if perfil.rol == 'admin':
                return 'Todos'
            elif perfil.rol == 'supervisor':
                campus_list = perfil.campus_asignados.all()
                if campus_list:
                    return ', '.join([c.nombre for c in campus_list[:3]])
                return 'Sin asignar'
            elif perfil.rol == 'operador':
                return perfil.campus.nombre if perfil.campus else 'Sin asignar'
        return '-'
    get_campus_info.short_description = 'Campus'

    def get_area_o_depto(self, obj):
        if hasattr(obj, 'perfil'):
            if obj.perfil.rol == 'externo' and obj.perfil.departamento:
                return f"📋 {obj.perfil.departamento}"
            elif obj.perfil.area:
                return obj.perfil.area.nombre
            return 'Todas (Admin)'
        return '-'
    get_area_o_depto.short_description = 'Área/Depto'


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
# INLINE PARA ESPECIFICACIONES DE SISTEMAS
# ============================================================================

class EspecificacionesSistemasInline(admin.StackedInline):
    model = EspecificacionesSistemas
    can_delete = False
    verbose_name = 'Especificaciones Técnicas (Sistemas)'
    verbose_name_plural = 'Especificaciones Técnicas (Sistemas)'
    
    fieldsets = (
        ('Identificación', {
            'fields': ('marca', 'modelo')
        }),
        ('Procesador', {
            'fields': ('procesador', 'generacion_procesador')
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
    extra = 0
    readonly_fields = ('tipo', 'estado', 'solicitado_por', 'autorizado_por', 'fecha_solicitud')
    can_delete = False
    ordering = ('-fecha_solicitud',)
    show_change_link = True
    
    fields = ('tipo', 'estado', 'motivo', 'solicitado_por', 'autorizado_por', 'fecha_solicitud')
    
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
            'nuevo': '#22c55e',      # Verde
            'instalado': '#3b82f6',  # Azul
            'dañado': '#f59e0b',     # Naranja
            'obsoleto': '#ef4444',   # Rojo
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

@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = (
        'item', 'tipo', 'estado_badge', 'es_emergencia_badge',
        'solicitado_por', 'autorizado_por', 'fecha_solicitud'
    )
    list_filter = ('estado', 'tipo', 'es_emergencia', 'escalado')
    search_fields = ('item__codigo_utp', 'item__nombre', 'motivo')
    ordering = ('-fecha_solicitud',)
    readonly_fields = ('fecha_solicitud', 'fecha_respuesta', 'fecha_ejecucion')
    autocomplete_fields = ('item', 'ambiente_origen', 'ambiente_destino', 'usuario_anterior', 'usuario_nuevo')
    date_hierarchy = 'fecha_solicitud'
    
    fieldsets = (
        ('Información del Movimiento', {
            'fields': ('item', 'tipo', 'estado', 'es_emergencia')
        }),
        ('Cambio de Ubicación', {
            'fields': ('ambiente_origen', 'ambiente_destino'),
            'classes': ('collapse',)
        }),
        ('Cambio de Estado', {
            'fields': ('estado_item_anterior', 'estado_item_nuevo'),
            'classes': ('collapse',)
        }),
        ('Cambio de Asignación', {
            'fields': ('usuario_anterior', 'usuario_nuevo'),
            'classes': ('collapse',)
        }),
        ('Justificación', {
            'fields': ('motivo', 'observaciones')
        }),
        ('Autorización', {
            'fields': ('solicitado_por', 'autorizado_por')
        }),
        ('Respuesta', {
            'fields': ('motivo_rechazo',),
            'classes': ('collapse',)
        }),
        ('Evidencia', {
            'fields': ('foto_evidencia', 'notas_evidencia'),
            'classes': ('collapse',)
        }),
        ('Escalamiento', {
            'fields': ('escalado', 'fecha_escalamiento', 'escalado_a'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('fecha_solicitud', 'fecha_respuesta', 'fecha_ejecucion'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['aprobar_movimientos', 'rechazar_movimientos']
    
    def estado_badge(self, obj):
        colores = {
            'pendiente': '#f59e0b',
            'aprobado': '#22c55e',
            'rechazado': '#ef4444',
            'ejecutado': '#3b82f6',
            'ejecutado_emergencia': '#8b5cf6',
            'revertido': '#6b7280',
        }
        color = colores.get(obj.estado, '#6b7280')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; border-radius:4px; font-size:11px;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def es_emergencia_badge(self, obj):
        if obj.es_emergencia:
            return format_html(
                '<span style="background:#ef4444; color:white; padding:2px 6px; border-radius:4px; font-size:10px;">⚠️ Emergencia</span>'
            )
        return '-'
    es_emergencia_badge.short_description = 'Emergencia'
    
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
# CONFIGURACIÓN DEL SITIO ADMIN
# ============================================================================

admin.site.site_header = 'Inventario UTP'
admin.site.site_title = 'Inventario UTP'
admin.site.index_title = 'Panel de Administración'
