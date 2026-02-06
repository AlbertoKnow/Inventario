"""
Mixins reutilizables para vistas.

Este módulo contiene los mixins de permisos y filtrado que se usan
en todas las vistas del sistema.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .models import PerfilUsuario, Campus
from .signals import set_current_user


class PerfilRequeridoMixin(LoginRequiredMixin):
    """Mixin que verifica que el usuario tenga perfil."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Establecer usuario actual para signals
            set_current_user(request.user)

            # Crear perfil si no existe
            if not hasattr(request.user, 'perfil'):
                # Superusuarios obtienen rol admin automáticamente
                rol = 'admin' if request.user.is_superuser else 'operador'
                PerfilUsuario.objects.create(usuario=request.user, rol=rol)
        return super().dispatch(request, *args, **kwargs)

    def get_user_area(self):
        """Obtiene el área del usuario actual."""
        if hasattr(self.request.user, 'perfil'):
            return self.request.user.perfil.area
        return None

    def get_user_rol(self):
        """Obtiene el rol del usuario actual."""
        if hasattr(self.request.user, 'perfil'):
            return self.request.user.perfil.rol
        return 'operador'

    def es_admin(self):
        """Verifica si el usuario es admin."""
        return self.get_user_rol() == 'admin'

    def es_supervisor(self):
        """Verifica si el usuario es supervisor."""
        return self.get_user_rol() == 'supervisor'


class SupervisorRequeridoMixin(PerfilRequeridoMixin, UserPassesTestMixin):
    """Solo supervisores y admins pueden acceder."""

    def test_func(self):
        return self.get_user_rol() in ['admin', 'supervisor']


class AdminRequeridoMixin(PerfilRequeridoMixin, UserPassesTestMixin):
    """Solo admins pueden acceder."""

    def test_func(self):
        return self.get_user_rol() == 'admin'


class AlmacenRequeridoMixin(PerfilRequeridoMixin, UserPassesTestMixin):
    """Solo admin, gerente y almacén pueden crear/editar/eliminar items."""

    def test_func(self):
        return self.get_user_rol() in ['admin', 'gerente', 'almacen']


class CampusFilterMixin:
    """
    Mixin para filtrar querysets según los campus permitidos del usuario.

    Uso:
    - Admin: ve todo (sin filtro)
    - Supervisor: ve solo los campus que tiene asignados
    - Operador: ve solo su campus asignado
    """

    def get_campus_permitidos(self):
        """Retorna los campus que el usuario puede ver."""
        if hasattr(self.request.user, 'perfil'):
            return self.request.user.perfil.get_campus_permitidos()
        return Campus.objects.none()

    def filtrar_por_campus(self, queryset, campo_campus='ambiente__pabellon__sede__campus'):
        """
        Filtra un queryset según los campus permitidos del usuario.

        Args:
            queryset: El queryset a filtrar
            campo_campus: El campo que relaciona con campus (ej: 'ambiente__pabellon__sede__campus')

        Returns:
            Queryset filtrado
        """
        if not hasattr(self.request.user, 'perfil'):
            return queryset.none()

        perfil = self.request.user.perfil

        # Admin ve todo
        if perfil.rol == 'admin':
            return queryset

        # Obtener IDs de campus permitidos
        campus_ids = list(self.get_campus_permitidos().values_list('id', flat=True))

        if not campus_ids:
            return queryset.none()

        # Construir filtro dinámico
        filtro = {f'{campo_campus}__in': campus_ids}
        return queryset.filter(**filtro)
