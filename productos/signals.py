from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Item, PerfilUsuario, HistorialCambio, Movimiento, Notificacion
import threading

# Variable para almacenar el usuario actual (thread-local)
_thread_locals = threading.local()


def get_current_user():
    """Obtiene el usuario actual del thread local."""
    return getattr(_thread_locals, 'user', None)


def set_current_user(user):
    """Establece el usuario actual en el thread local."""
    _thread_locals.user = user


class CurrentUserMiddleware:
    """Middleware para capturar el usuario actual en cada request."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        set_current_user(request.user if request.user.is_authenticated else None)
        response = self.get_response(request)
        return response


# ============================================================================
# SEÑALES PARA PERFIL DE USUARIO
# ============================================================================

# NOTA: La creación del perfil se maneja desde el admin.py con el inline
# No usamos signals aquí para evitar conflictos de unicidad


# ============================================================================
# SEÑALES PARA HISTORIAL DE CAMBIOS EN ITEMS
# ============================================================================

# Campos que se deben rastrear
CAMPOS_RASTREADOS = [
    'nombre', 'descripcion', 'tipo_item', 'ambiente', 'estado',
    'usuario_asignado', 'observaciones', 'fecha_adquisicion', 'precio',
    'garantia_hasta', 'es_leasing', 'leasing_empresa', 'leasing_contrato',
    'leasing_vencimiento', 'serie'
]

# Campos que NO deben cambiarse (inmutables después de crear)
CAMPOS_INMUTABLES = ['codigo_utp', 'area']


@receiver(pre_save, sender=Item)
def capturar_valores_anteriores(sender, instance, **kwargs):
    """Captura los valores anteriores antes de guardar."""
    if instance.pk:
        try:
            instance._valores_anteriores = Item.objects.get(pk=instance.pk)
        except Item.DoesNotExist:
            instance._valores_anteriores = None
    else:
        instance._valores_anteriores = None


@receiver(post_save, sender=Item)
def registrar_cambios_item(sender, instance, created, **kwargs):
    """Registra los cambios realizados en un ítem."""
    usuario = get_current_user()
    
    if created:
        # Registrar la creación del ítem
        HistorialCambio.objects.create(
            item=instance,
            usuario=usuario,
            campo='_creacion',
            valor_anterior='',
            valor_nuevo=f'Ítem creado: {instance.codigo_utp}'
        )
        return
    
    # Si hay valores anteriores, comparar y registrar cambios
    anterior = getattr(instance, '_valores_anteriores', None)
    if not anterior:
        return
    
    for campo in CAMPOS_RASTREADOS:
        valor_anterior = getattr(anterior, campo, None)
        valor_nuevo = getattr(instance, campo, None)
        
        # Convertir a string para comparación
        str_anterior = str(valor_anterior) if valor_anterior is not None else ''
        str_nuevo = str(valor_nuevo) if valor_nuevo is not None else ''
        
        if str_anterior != str_nuevo:
            # Obtener nombres legibles para ForeignKeys
            if campo in ['tipo_item', 'ambiente', 'usuario_asignado']:
                str_anterior = str(valor_anterior) if valor_anterior else 'Sin asignar'
                str_nuevo = str(valor_nuevo) if valor_nuevo else 'Sin asignar'
            
            HistorialCambio.objects.create(
                item=instance,
                usuario=usuario,
                campo=campo,
                valor_anterior=str_anterior,
                valor_nuevo=str_nuevo
            )


# ============================================================================
# SEÑALES PARA NOTIFICACIONES DE MOVIMIENTOS
# ============================================================================

@receiver(post_save, sender=Movimiento)
def notificar_movimiento(sender, instance, created, **kwargs):
    """Crea notificaciones cuando se crea o actualiza un movimiento."""

    if created:
        # Notificar a supervisores del área del ítem
        from django.contrib.auth.models import User
        supervisores = User.objects.filter(
            perfil__rol__in=['supervisor', 'gerente'],
            perfil__area=instance.item.area,
            perfil__activo=True,
            is_active=True
        )

        for supervisor in supervisores:
            Notificacion.objects.create(
                usuario=supervisor,
                tipo='solicitud',
                titulo=f"Nueva solicitud de {instance.get_tipo_display()}",
                mensaje=f"{instance.solicitado_por} solicita {instance.get_tipo_display().lower()} del ítem {instance.item.codigo_interno}. Motivo: {instance.motivo}",
                url=f"/movimientos/{instance.pk}/",
                movimiento=instance,
                urgente=False
            )
    else:
        # Notificar cambios de estado
        if instance.estado == 'aprobado':
            Notificacion.objects.create(
                usuario=instance.solicitado_por,
                tipo='aprobado',
                titulo=f"Solicitud aprobada",
                mensaje=f"Tu solicitud de {instance.get_tipo_display().lower()} para {instance.item.codigo_utp} fue aprobada.",
                url=f"/movimientos/{instance.pk}/",
                movimiento=instance,
                urgente=False
            )
        elif instance.estado == 'rechazado':
            Notificacion.objects.create(
                usuario=instance.solicitado_por,
                tipo='rechazado',
                titulo=f"Solicitud rechazada",
                mensaje=f"Tu solicitud de {instance.get_tipo_display().lower()} para {instance.item.codigo_utp} fue rechazada. Motivo: {instance.motivo_rechazo}",
                url=f"/movimientos/{instance.pk}/",
                movimiento=instance,
                urgente=False
            )
