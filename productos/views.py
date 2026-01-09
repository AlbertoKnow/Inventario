from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum, Count
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from .models import (
    Area, Campus, Sede, Pabellon, Ambiente, TipoItem, Item, EspecificacionesSistemas,
    Movimiento, HistorialCambio, Notificacion, PerfilUsuario,
    Proveedor, Contrato, AnexoContrato, Lote
)
from .forms import ItemForm, ItemSistemasForm, MovimientoForm, TipoItemForm, AmbienteForm, CampusForm, SedeForm, PabellonForm
from .signals import set_current_user


# ============================================================================
# MIXINS DE PERMISOS
# ============================================================================

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


# ============================================================================
# VISTA DE INICIO
# ============================================================================

class HomeView(TemplateView):
    """Página de inicio - accesible a todos."""
    template_name = 'index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            user = self.request.user
            perfil = getattr(user, 'perfil', None)
            
            # Filtrar por área si no es admin
            items = Item.objects.all()
            if perfil and perfil.rol != 'admin' and perfil.area:
                items = items.filter(area=perfil.area)
            
            context['total_items'] = items.count()
            context['items_nuevos'] = items.filter(estado='nuevo').count()
            context['items_instalados'] = items.filter(estado='instalado').count()
            context['items_dañados'] = items.filter(estado='dañado').count()
            context['valor_total'] = items.aggregate(valor=Sum('precio'))['valor'] or 0
            
            # Notificaciones no leídas
            context['notificaciones_count'] = Notificacion.objects.filter(
                usuario=user, leida=False
            ).count()
            
            # Movimientos pendientes (para supervisores)
            if perfil and perfil.rol in ['admin', 'supervisor']:
                pendientes = Movimiento.objects.filter(estado='pendiente')
                if perfil.rol == 'supervisor' and perfil.area:
                    pendientes = pendientes.filter(item__area=perfil.area)
                context['movimientos_pendientes'] = pendientes.count()
        
        return context


# ============================================================================
# DASHBOARD
# ============================================================================

class DashboardView(PerfilRequeridoMixin, TemplateView):
    """Dashboard principal del inventario."""
    template_name = 'productos/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        perfil = getattr(user, 'perfil', None)
        
        # Base queryset
        items = Item.objects.all()
        if perfil and perfil.rol != 'admin' and perfil.area:
            items = items.filter(area=perfil.area)
        
        # Estadísticas generales
        context['total_items'] = items.count()
        context['items_por_estado'] = {
            'nuevo': items.filter(estado='nuevo').count(),
            'instalado': items.filter(estado='instalado').count(),
            'dañado': items.filter(estado='dañado').count(),
            'obsoleto': items.filter(estado='obsoleto').count(),
        }
        context['valor_total'] = items.aggregate(valor=Sum('precio'))['valor'] or 0
        
        # Items por área
        context['items_por_area'] = Area.objects.annotate(
            total=Count('items')
        ).values('nombre', 'total')
        
        # Garantías próximas a vencer (30 días)
        fecha_limite = timezone.now().date() + timezone.timedelta(days=30)
        context['garantias_proximas'] = items.filter(
            garantia_hasta__lte=fecha_limite,
            garantia_hasta__gte=timezone.now().date()
        ).count()
        
        # Últimos movimientos
        movimientos = Movimiento.objects.select_related('item', 'solicitado_por')
        if perfil and perfil.rol != 'admin' and perfil.area:
            movimientos = movimientos.filter(item__area=perfil.area)
        context['ultimos_movimientos'] = movimientos[:10]
        
        # Movimientos pendientes de aprobar
        if perfil and perfil.rol in ['admin', 'supervisor']:
            pendientes = Movimiento.objects.filter(estado='pendiente')
            if perfil.rol == 'supervisor' and perfil.area:
                pendientes = pendientes.filter(item__area=perfil.area)
            context['movimientos_pendientes'] = pendientes[:5]
        
        # Notificaciones
        context['notificaciones'] = Notificacion.objects.filter(
            usuario=user, leida=False
        )[:5]
        
        return context


# ============================================================================
# VISTAS DE ITEMS
# ============================================================================

class ItemListView(PerfilRequeridoMixin, ListView):
    """Lista de ítems del inventario."""
    model = Item
    template_name = 'productos/item_list.html'
    context_object_name = 'items'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Item.objects.select_related('area', 'tipo_item', 'ambiente', 'usuario_asignado')
        
        perfil = getattr(self.request.user, 'perfil', None)
        
        # Filtrar por área si no es admin
        if perfil and perfil.rol != 'admin' and perfil.area:
            queryset = queryset.filter(area=perfil.area)
        
        # Filtros de búsqueda
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(codigo_utp__icontains=search) |
                Q(serie__icontains=search) |
                Q(nombre__icontains=search)
            )
        
        # Filtro por área
        area = self.request.GET.get('area')
        if area:
            queryset = queryset.filter(area__codigo=area)
        
        # Filtro por estado
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        # Filtro por ambiente
        ambiente = self.request.GET.get('ambiente')
        if ambiente:
            queryset = queryset.filter(ambiente_id=ambiente)
        
        # Filtro por campus
        campus = self.request.GET.get('campus')
        if campus:
            queryset = queryset.filter(ambiente__pabellon__sede__campus_id=campus)
        
        # Filtro por garantía próxima a vencer (30 días)
        garantia_proxima = self.request.GET.get('garantia_proxima')
        if garantia_proxima:
            fecha_limite = timezone.now().date() + timedelta(days=30)
            queryset = queryset.filter(
                garantia_hasta__lte=fecha_limite,
                garantia_hasta__gte=timezone.now().date()
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['areas'] = Area.objects.filter(activo=True)
        context['campus_list'] = Campus.objects.filter(activo=True)
        context['ambientes'] = Ambiente.objects.filter(activo=True).select_related('pabellon__sede__campus')
        context['estados'] = Item.ESTADOS
        return context


class ItemDetailView(PerfilRequeridoMixin, DetailView):
    """Detalle de un ítem."""
    model = Item
    template_name = 'productos/item_detail.html'
    context_object_name = 'item'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.object
        
        # Especificaciones de sistemas si aplica
        if item.area.codigo == 'sistemas':
            context['especificaciones'] = getattr(item, 'especificaciones_sistemas', None)
        
        # Historial de movimientos
        context['movimientos'] = item.movimientos.select_related(
            'solicitado_por', 'autorizado_por'
        )[:10]
        
        # Historial de cambios
        context['historial'] = item.historial_cambios.select_related('usuario')[:10]
        
        return context


class ItemCreateView(PerfilRequeridoMixin, CreateView):
    """Crear un nuevo ítem."""
    model = Item
    form_class = ItemForm
    template_name = 'productos/item_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Ítem'
        context['es_sistemas'] = self.request.GET.get('area') == 'sistemas'
        return context
    
    def form_valid(self, form):
        item = form.save(commit=False)
        item.creado_por = self.request.user
        item.modificado_por = self.request.user
        
        # Auto-generar código UTP
        if not item.codigo_utp:
            item.codigo_utp = Item.generar_codigo_utp(item.area.codigo)
        
        item.save()
        
        messages.success(self.request, f'Ítem {item.codigo_utp} creado correctamente.')
        return redirect('productos:item-detail', pk=item.pk)


class ItemUpdateView(PerfilRequeridoMixin, UpdateView):
    """Editar un ítem existente."""
    model = Item
    form_class = ItemForm
    template_name = 'productos/item_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar {self.object.codigo_utp}'
        context['es_sistemas'] = self.object.area.codigo == 'sistemas'
        return context
    
    def form_valid(self, form):
        item = form.save(commit=False)
        item.modificado_por = self.request.user
        item.save()
        
        messages.success(self.request, f'Ítem {item.codigo_utp} actualizado correctamente.')
        return redirect('productos:item-detail', pk=item.pk)


class ItemDeleteView(AdminRequeridoMixin, DeleteView):
    """Eliminar un ítem (solo admin)."""
    model = Item
    template_name = 'productos/item_confirm_delete.html'
    success_url = reverse_lazy('productos:item-list')
    
    def delete(self, request, *args, **kwargs):
        item = self.get_object()
        messages.success(request, f'Ítem {item.codigo_utp} eliminado.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# VISTAS DE MOVIMIENTOS
# ============================================================================

class MovimientoListView(PerfilRequeridoMixin, ListView):
    """Lista de movimientos."""
    model = Movimiento
    template_name = 'productos/movimiento_list.html'
    context_object_name = 'movimientos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Movimiento.objects.select_related(
            'item', 'solicitado_por', 'autorizado_por'
        )
        
        perfil = getattr(self.request.user, 'perfil', None)
        
        # Filtrar por área si no es admin
        if perfil and perfil.rol != 'admin' and perfil.area:
            queryset = queryset.filter(item__area=perfil.area)
        
        # Filtro por estado
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Movimiento.ESTADOS_MOVIMIENTO
        return context


class MovimientoPendientesView(SupervisorRequeridoMixin, ListView):
    """Movimientos pendientes de aprobar."""
    model = Movimiento
    template_name = 'productos/movimiento_pendientes.html'
    context_object_name = 'movimientos'
    
    def get_queryset(self):
        queryset = Movimiento.objects.filter(estado='pendiente').select_related(
            'item', 'solicitado_por'
        )
        
        perfil = getattr(self.request.user, 'perfil', None)
        
        # Supervisor solo ve de su área
        if perfil and perfil.rol == 'supervisor' and perfil.area:
            queryset = queryset.filter(item__area=perfil.area)
        
        return queryset


class MovimientoCreateView(PerfilRequeridoMixin, CreateView):
    """Crear un nuevo movimiento."""
    model = Movimiento
    form_class = MovimientoForm
    template_name = 'productos/movimiento_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # Pre-cargar ítem si viene en la URL
        item_pk = self.request.GET.get('item')
        if item_pk:
            kwargs['item'] = get_object_or_404(Item, pk=item_pk)
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Solicitud de Movimiento'
        
        # Datos para los filtros de búsqueda de ítems
        context['campus_list'] = Campus.objects.filter(activo=True)
        context['areas_list'] = Area.objects.filter(activo=True)
        
        # Ítem preseleccionado si viene en URL
        item_pk = self.request.GET.get('item')
        if item_pk:
            context['item'] = get_object_or_404(Item, pk=item_pk)
        
        return context
    
    def form_valid(self, form):
        movimiento = form.save(commit=False)
        movimiento.solicitado_por = self.request.user
        
        # Si es emergencia, ejecutar inmediatamente
        if movimiento.es_emergencia:
            movimiento.estado = 'ejecutado_emergencia'
            movimiento.fecha_ejecucion = timezone.now()
            
            # Aplicar cambios al ítem
            item = movimiento.item
            if movimiento.tipo == 'traslado' and movimiento.ambiente_destino:
                movimiento.ambiente_origen = item.ambiente
                item.ambiente = movimiento.ambiente_destino
            if movimiento.tipo == 'cambio_estado' and movimiento.estado_item_nuevo:
                movimiento.estado_item_anterior = item.estado
                item.estado = movimiento.estado_item_nuevo
            if movimiento.tipo == 'asignacion':
                movimiento.usuario_anterior = item.usuario_asignado
                item.usuario_asignado = movimiento.usuario_nuevo
            item.save()
        else:
            # Guardar estado actual como origen
            if movimiento.tipo == 'traslado':
                movimiento.ambiente_origen = movimiento.item.ambiente
            if movimiento.tipo == 'cambio_estado':
                movimiento.estado_item_anterior = movimiento.item.estado
            if movimiento.tipo == 'asignacion':
                movimiento.usuario_anterior = movimiento.item.usuario_asignado
        
        movimiento.save()
        
        if movimiento.es_emergencia:
            messages.warning(
                self.request, 
                f'Movimiento de EMERGENCIA ejecutado. Pendiente de validación por {movimiento.autorizado_por}.'
            )
        else:
            messages.success(
                self.request, 
                f'Solicitud creada. Pendiente de aprobación por {movimiento.autorizado_por}.'
            )
        
        return redirect('productos:movimiento-list')


class MovimientoDetailView(PerfilRequeridoMixin, DetailView):
    """Detalle de un movimiento."""
    model = Movimiento
    template_name = 'productos/movimiento_detail.html'
    context_object_name = 'movimiento'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasar el perfil del usuario al contexto
        context['perfil'] = getattr(self.request.user, 'perfil', None)
        # Detectar si viene de pendientes para el breadcrumb
        context['from_pendientes'] = 'pendientes' in self.request.META.get('HTTP_REFERER', '')
        return context


class MovimientoAprobarView(SupervisorRequeridoMixin, View):
    """Aprobar un movimiento."""
    
    def post(self, request, pk):
        movimiento = get_object_or_404(Movimiento, pk=pk)
        
        # Verificar que puede aprobar
        perfil = getattr(request.user, 'perfil', None)
        if perfil and perfil.rol == 'supervisor':
            if perfil.area != movimiento.item.area:
                messages.error(request, 'No puedes aprobar movimientos de otra área.')
                return redirect('productos:movimiento-detail', pk=pk)
        
        if movimiento.estado not in ['pendiente', 'ejecutado_emergencia']:
            messages.error(request, 'Este movimiento no puede ser aprobado.')
            return redirect('productos:movimiento-detail', pk=pk)
        
        # Aprobar
        movimiento.aprobar(request.user)
        
        # Si no era emergencia, ejecutar
        if movimiento.estado != 'ejecutado_emergencia':
            movimiento.ejecutar()
        
        messages.success(request, 'Movimiento aprobado y ejecutado.')
        return redirect('productos:movimiento-pendientes')


class MovimientoRechazarView(SupervisorRequeridoMixin, View):
    """Rechazar un movimiento."""
    
    def post(self, request, pk):
        movimiento = get_object_or_404(Movimiento, pk=pk)
        motivo = request.POST.get('motivo_rechazo', 'Sin motivo especificado')
        
        # Verificar que puede rechazar
        perfil = getattr(request.user, 'perfil', None)
        if perfil and perfil.rol == 'supervisor':
            if perfil.area != movimiento.item.area:
                messages.error(request, 'No puedes rechazar movimientos de otra área.')
                return redirect('productos:movimiento-detail', pk=pk)
        
        if movimiento.estado not in ['pendiente', 'ejecutado_emergencia']:
            messages.error(request, 'Este movimiento no puede ser rechazado.')
            return redirect('productos:movimiento-detail', pk=pk)
        
        # Si era emergencia, revertir cambios
        if movimiento.estado == 'ejecutado_emergencia':
            item = movimiento.item
            if movimiento.ambiente_origen:
                item.ambiente = movimiento.ambiente_origen
            if movimiento.estado_item_anterior:
                item.estado = movimiento.estado_item_anterior
            if movimiento.usuario_anterior:
                item.usuario_asignado = movimiento.usuario_anterior
            item.save()
            movimiento.estado = 'revertido'
        
        movimiento.rechazar(request.user, motivo)
        
        messages.success(request, 'Movimiento rechazado.')
        return redirect('productos:movimiento-pendientes')


# ============================================================================
# VISTAS DE NOTIFICACIONES
# ============================================================================

class NotificacionListView(PerfilRequeridoMixin, ListView):
    """Lista de notificaciones del usuario."""
    model = Notificacion
    template_name = 'productos/notificacion_list.html'
    context_object_name = 'notificaciones'
    paginate_by = 20
    
    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user)


class NotificacionMarcarLeidaView(PerfilRequeridoMixin, View):
    """Marcar notificación como leída."""
    
    def post(self, request, pk):
        notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
        notificacion.marcar_leida()
        
        # Redirigir a la URL de la notificación si existe
        if notificacion.url:
            return redirect(notificacion.url)
        return redirect('productos:notificacion-list')


class NotificacionMarcarTodasLeidasView(PerfilRequeridoMixin, View):
    """Marcar todas las notificaciones como leídas."""
    
    def post(self, request):
        Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
        messages.success(request, 'Todas las notificaciones marcadas como leídas.')
        return redirect('productos:notificacion-list')


# ============================================================================
# API ENDPOINTS (JSON)
# ============================================================================

class TiposItemPorAreaView(PerfilRequeridoMixin, View):
    """Obtiene los tipos de ítem para un área (para formularios dinámicos)."""
    
    def get(self, request):
        area_id = request.GET.get('area')
        tipos = []
        
        if area_id:
            tipos = list(TipoItem.objects.filter(
                area_id=area_id, activo=True
            ).values('id', 'nombre'))
        
        return JsonResponse({'tipos': tipos})


class SupervisoresPorAreaView(PerfilRequeridoMixin, View):
    """Obtiene los supervisores de un área (para seleccionar autorizador)."""
    
    def get(self, request):
        area_id = request.GET.get('area')
        supervisores = []
        
        if area_id:
            from django.contrib.auth.models import User
            supervisores = list(
                User.objects.filter(
                    perfil__area_id=area_id,
                    perfil__rol='supervisor',
                    perfil__activo=True,
                    is_active=True
                ).values('id', 'first_name', 'last_name', 'username')
            )
        
        # Agregar admins siempre
        admins = list(
            User.objects.filter(
                perfil__rol='admin',
                perfil__activo=True,
                is_active=True
            ).values('id', 'first_name', 'last_name', 'username')
        )
        
        return JsonResponse({'supervisores': supervisores + admins})


# ============================================================================
# VISTAS PARA CREAR TIPO ITEM (accesible a operadores)
# ============================================================================

class TipoItemCreateView(PerfilRequeridoMixin, CreateView):
    """Vista para crear tipos de ítem (accesible a todos los roles excepto externos)."""
    model = TipoItem
    form_class = TipoItemForm
    template_name = 'productos/tipoitem_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Si el usuario tiene área asignada y no es admin, usar esa área
        perfil = getattr(self.request.user, 'perfil', None)
        if perfil and perfil.area and perfil.rol != 'admin':
            form.instance.area = perfil.area
        
        messages.success(
            self.request, 
            f'Tipo de ítem "{form.instance.nombre}" creado exitosamente.'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        # Redirigir a donde vino o al listado de ítems
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('productos:item-create')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Tipo de Ítem'
        
        # Verificar si hay advertencia de tipos similares
        if hasattr(self.get_form(), 'advertencia_similares'):
            context['advertencia_similares'] = self.get_form().advertencia_similares
        
        return context


class TipoItemListView(PerfilRequeridoMixin, ListView):
    """Lista de tipos de ítem."""
    model = TipoItem
    template_name = 'productos/tipoitem_list.html'
    context_object_name = 'tipos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = TipoItem.objects.select_related('area').filter(activo=True)
        
        # Filtrar por área si el usuario no es admin
        perfil = getattr(self.request.user, 'perfil', None)
        if perfil and perfil.rol != 'admin' and perfil.area:
            queryset = queryset.filter(area=perfil.area)
        
        # Filtro por área desde request
        area_id = self.request.GET.get('area')
        if area_id:
            queryset = queryset.filter(area_id=area_id)
        
        # Búsqueda
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(nombre__icontains=search)
        
        return queryset.order_by('area', 'nombre')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['areas'] = Area.objects.filter(activo=True)
        return context


# ============================================================================
# VISTAS PARA UBICACIONES
# ============================================================================

class UbicacionListView(PerfilRequeridoMixin, ListView):
    """Lista de ambientes (ubicaciones)."""
    model = Ambiente
    template_name = 'productos/ubicacion_list.html'
    context_object_name = 'ambientes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Ambiente.objects.filter(activo=True).select_related(
            'pabellon', 'pabellon__sede', 'pabellon__sede__campus'
        )
        
        # Filtros
        campus = self.request.GET.get('campus')
        sede = self.request.GET.get('sede')
        pabellon = self.request.GET.get('pabellon')
        tipo = self.request.GET.get('tipo')
        search = self.request.GET.get('q')
        
        if campus:
            queryset = queryset.filter(pabellon__sede__campus_id=campus)
        if sede:
            queryset = queryset.filter(pabellon__sede_id=sede)
        if pabellon:
            queryset = queryset.filter(pabellon_id=pabellon)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(codigo__icontains=search)
            )
        
        return queryset.order_by('pabellon__sede__campus__nombre', 'pabellon__sede__nombre', 'pabellon__nombre', 'piso')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Valores para filtros (ahora son ForeignKeys)
        context['campus_list'] = Campus.objects.filter(activo=True)
        context['sedes_list'] = Sede.objects.filter(activo=True).select_related('campus')
        context['pabellones_list'] = Pabellon.objects.filter(activo=True).select_related('sede')
        context['tipos_ambiente'] = Ambiente.TIPOS_AMBIENTE
        return context


class UbicacionDetailView(PerfilRequeridoMixin, DetailView):
    """Detalle de ambiente (ubicación) con ítems."""
    model = Ambiente
    template_name = 'productos/ubicacion_detail.html'
    context_object_name = 'ambiente'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ítems en este ambiente
        context['items'] = Item.objects.filter(ambiente=self.object).select_related('area', 'tipo_item')
        return context


class UbicacionCreateView(SupervisorRequeridoMixin, CreateView):
    """Crear ambiente (solo supervisores y admins)."""
    model = Ambiente
    form_class = AmbienteForm
    template_name = 'productos/ubicacion_form.html'
    success_url = reverse_lazy('productos:ubicacion-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Ambiente creado exitosamente.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Ambiente'
        return context


class UbicacionUpdateView(SupervisorRequeridoMixin, UpdateView):
    """Editar ambiente (solo supervisores y admins)."""
    model = Ambiente
    form_class = AmbienteForm
    template_name = 'productos/ubicacion_form.html'
    
    def get_success_url(self):
        return reverse_lazy('productos:ubicacion-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Ambiente actualizado exitosamente.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Ambiente'
        context['editando'] = True
        return context


# ============================================================================
# APIs AJAX PARA DROPDOWNS EN CASCADA
# ============================================================================

class SedesPorCampusView(LoginRequiredMixin, View):
    """API para obtener sedes de un campus."""
    
    def get(self, request):
        campus_id = request.GET.get('campus_id')
        if campus_id:
            sedes = Sede.objects.filter(campus_id=campus_id, activo=True).values('id', 'nombre')
            return JsonResponse(list(sedes), safe=False)
        return JsonResponse([], safe=False)


class PabellonesPorSedeView(LoginRequiredMixin, View):
    """API para obtener pabellones de una sede."""
    
    def get(self, request):
        sede_id = request.GET.get('sede_id')
        if sede_id:
            pabellones = Pabellon.objects.filter(sede_id=sede_id, activo=True).values('id', 'nombre')
            return JsonResponse(list(pabellones), safe=False)
        return JsonResponse([], safe=False)


class AmbientesPorPabellonView(LoginRequiredMixin, View):
    """API para obtener ambientes de un pabellón."""
    
    def get(self, request):
        pabellon_id = request.GET.get('pabellon_id')
        if pabellon_id:
            ambientes = Ambiente.objects.filter(pabellon_id=pabellon_id, activo=True).values('id', 'nombre', 'piso', 'tipo')
            return JsonResponse(list(ambientes), safe=False)
        return JsonResponse([], safe=False)


class BuscarItemsView(LoginRequiredMixin, View):
    """API para buscar ítems con autocompletado."""
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        area_id = request.GET.get('area')
        tipo_id = request.GET.get('tipo')
        campus_id = request.GET.get('campus')
        sede_id = request.GET.get('sede')
        pabellon_id = request.GET.get('pabellon')
        ambiente_id = request.GET.get('ambiente')
        
        items = Item.objects.select_related(
            'area', 'tipo_item', 'ambiente', 'ambiente__pabellon',
            'ambiente__pabellon__sede', 'ambiente__pabellon__sede__campus',
            'usuario_asignado'
        )
        
        # Filtrar por área del usuario si no es admin
        perfil = getattr(request.user, 'perfil', None)
        if perfil and perfil.rol != 'admin' and perfil.area:
            items = items.filter(area=perfil.area)
        
        # Búsqueda por texto
        if query:
            items = items.filter(
                Q(codigo_utp__icontains=query) |
                Q(serie__icontains=query) |
                Q(nombre__icontains=query)
            )
        
        # Filtros adicionales
        if area_id:
            items = items.filter(area_id=area_id)
        if tipo_id:
            items = items.filter(tipo_item_id=tipo_id)
        if campus_id:
            items = items.filter(ambiente__pabellon__sede__campus_id=campus_id)
        if sede_id:
            items = items.filter(ambiente__pabellon__sede_id=sede_id)
        if pabellon_id:
            items = items.filter(ambiente__pabellon_id=pabellon_id)
        if ambiente_id:
            items = items.filter(ambiente_id=ambiente_id)
        
        # Limitar resultados
        items = items[:20]
        
        # Formatear respuesta
        resultados = []
        for item in items:
            ubicacion = ""
            if item.ambiente:
                amb = item.ambiente
                ubicacion = f"{amb.pabellon.sede.campus.codigo} > {amb.pabellon.sede.nombre} > Pab. {amb.pabellon.nombre} > {amb.nombre}"
            
            resultados.append({
                'id': item.id,
                'codigo_utp': item.codigo_utp,
                'serie': item.serie,
                'nombre': item.nombre,
                'area': item.area.nombre,
                'tipo': item.tipo_item.nombre if item.tipo_item else '',
                'estado': item.estado,
                'estado_display': item.get_estado_display(),
                'ubicacion': ubicacion,
                'ambiente_id': item.ambiente_id,
                'usuario_asignado': item.usuario_asignado.get_full_name() if item.usuario_asignado else None,
                'texto': f"{item.codigo_utp} - {item.nombre}"
            })
        
        return JsonResponse({'items': resultados})


class ObtenerItemDetalleView(LoginRequiredMixin, View):
    """API para obtener detalles de un ítem específico."""
    
    def get(self, request):
        item_id = request.GET.get('id')
        if not item_id:
            return JsonResponse({'error': 'ID requerido'}, status=400)
        
        try:
            item = Item.objects.select_related(
                'area', 'tipo_item', 'ambiente', 'ambiente__pabellon',
                'ambiente__pabellon__sede', 'ambiente__pabellon__sede__campus',
                'usuario_asignado'
            ).get(pk=item_id)
        except Item.DoesNotExist:
            return JsonResponse({'error': 'Ítem no encontrado'}, status=404)
        
        ubicacion = ""
        ubicacion_completa = {}
        if item.ambiente:
            amb = item.ambiente
            ubicacion = f"{amb.pabellon.sede.campus.nombre} > {amb.pabellon.sede.nombre} > Pabellón {amb.pabellon.nombre} > {amb.nombre}"
            ubicacion_completa = {
                'campus_id': amb.pabellon.sede.campus_id,
                'campus': amb.pabellon.sede.campus.nombre,
                'sede_id': amb.pabellon.sede_id,
                'sede': amb.pabellon.sede.nombre,
                'pabellon_id': amb.pabellon_id,
                'pabellon': amb.pabellon.nombre,
                'ambiente_id': amb.id,
                'ambiente': amb.nombre,
                'piso': amb.piso
            }
        
        return JsonResponse({
            'id': item.id,
            'codigo_utp': item.codigo_utp,
            'serie': item.serie,
            'nombre': item.nombre,
            'descripcion': item.descripcion,
            'area': item.area.nombre,
            'area_id': item.area_id,
            'tipo': item.tipo_item.nombre if item.tipo_item else '',
            'estado': item.estado,
            'estado_display': item.get_estado_display(),
            'ubicacion': ubicacion,
            'ubicacion_completa': ubicacion_completa,
            'usuario_asignado': item.usuario_asignado.get_full_name() if item.usuario_asignado else None,
            'usuario_asignado_id': item.usuario_asignado_id,
        })


# ============================================================================
# VISTAS CRUD PARA CAMPUS
# ============================================================================

class CampusListView(AdminRequeridoMixin, ListView):
    """Listar todos los campus (solo admins)."""
    model = Campus
    template_name = 'productos/campus_list.html'
    context_object_name = 'campus_list'
    
    def get_queryset(self):
        queryset = Campus.objects.annotate(
            total_sedes=Count('sedes')
        ).order_by('nombre')
        
        # Búsqueda
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) | Q(codigo__icontains=q)
            )
        
        # Filtro por estado
        activo = self.request.GET.get('activo')
        if activo == '1':
            queryset = queryset.filter(activo=True)
        elif activo == '0':
            queryset = queryset.filter(activo=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Gestión de Campus'
        return context


class CampusCreateView(AdminRequeridoMixin, CreateView):
    """Crear campus (solo admins)."""
    model = Campus
    form_class = CampusForm
    template_name = 'productos/campus_form.html'
    success_url = reverse_lazy('productos:campus-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Campus creado exitosamente.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Campus'
        return context


class CampusUpdateView(AdminRequeridoMixin, UpdateView):
    """Editar campus (solo admins)."""
    model = Campus
    form_class = CampusForm
    template_name = 'productos/campus_form.html'
    success_url = reverse_lazy('productos:campus-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Campus actualizado exitosamente.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Campus'
        context['editando'] = True
        return context


class CampusDeleteView(AdminRequeridoMixin, DeleteView):
    """Eliminar campus (solo admins)."""
    model = Campus
    template_name = 'productos/campus_confirm_delete.html'
    success_url = reverse_lazy('productos:campus-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Campus eliminado exitosamente.')
        return super().form_valid(form)


# ============================================================================
# VISTAS CRUD PARA SEDES
# ============================================================================

class SedeListView(AdminRequeridoMixin, ListView):
    """Listar todas las sedes (solo admins)."""
    model = Sede
    template_name = 'productos/sede_list.html'
    context_object_name = 'sedes'
    
    def get_queryset(self):
        queryset = Sede.objects.select_related('campus').annotate(
            total_pabellones=Count('pabellones')
        ).order_by('campus__nombre', 'nombre')
        
        # Búsqueda
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) | Q(codigo__icontains=q) | Q(campus__nombre__icontains=q)
            )
        
        # Filtro por campus
        campus_id = self.request.GET.get('campus')
        if campus_id:
            queryset = queryset.filter(campus_id=campus_id)
        
        # Filtro por estado
        activo = self.request.GET.get('activo')
        if activo == '1':
            queryset = queryset.filter(activo=True)
        elif activo == '0':
            queryset = queryset.filter(activo=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Gestión de Sedes'
        context['campus_list'] = Campus.objects.filter(activo=True)
        return context


class SedeCreateView(AdminRequeridoMixin, CreateView):
    """Crear sede (solo admins)."""
    model = Sede
    form_class = SedeForm
    template_name = 'productos/sede_form.html'
    success_url = reverse_lazy('productos:sede-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Sede creada exitosamente.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Sede'
        return context


class SedeUpdateView(AdminRequeridoMixin, UpdateView):
    """Editar sede (solo admins)."""
    model = Sede
    form_class = SedeForm
    template_name = 'productos/sede_form.html'
    success_url = reverse_lazy('productos:sede-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Sede actualizada exitosamente.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Sede'
        context['editando'] = True
        return context


class SedeDeleteView(AdminRequeridoMixin, DeleteView):
    """Eliminar sede (solo admins)."""
    model = Sede
    template_name = 'productos/sede_confirm_delete.html'
    success_url = reverse_lazy('productos:sede-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Sede eliminada exitosamente.')
        return super().form_valid(form)


# ============================================================================
# VISTAS CRUD PARA PABELLONES
# ============================================================================

class PabellonListView(AdminRequeridoMixin, ListView):
    """Listar todos los pabellones (solo admins)."""
    model = Pabellon
    template_name = 'productos/pabellon_list.html'
    context_object_name = 'pabellones'
    
    def get_queryset(self):
        queryset = Pabellon.objects.select_related('sede', 'sede__campus').annotate(
            total_ambientes=Count('ambientes')
        ).order_by('sede__campus__nombre', 'sede__nombre', 'nombre')
        
        # Búsqueda
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) | Q(sede__nombre__icontains=q) | Q(sede__campus__nombre__icontains=q)
            )
        
        # Filtro por campus
        campus_id = self.request.GET.get('campus')
        if campus_id:
            queryset = queryset.filter(sede__campus_id=campus_id)
        
        # Filtro por sede
        sede_id = self.request.GET.get('sede')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
        
        # Filtro por estado
        activo = self.request.GET.get('activo')
        if activo == '1':
            queryset = queryset.filter(activo=True)
        elif activo == '0':
            queryset = queryset.filter(activo=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Gestión de Pabellones'
        context['campus_list'] = Campus.objects.filter(activo=True)
        context['sedes'] = Sede.objects.filter(activo=True).select_related('campus')
        return context


class PabellonCreateView(AdminRequeridoMixin, CreateView):
    """Crear pabellón (solo admins)."""
    model = Pabellon
    form_class = PabellonForm
    template_name = 'productos/pabellon_form.html'
    success_url = reverse_lazy('productos:pabellon-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Pabellón creado exitosamente.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Pabellón'
        return context


class PabellonUpdateView(AdminRequeridoMixin, UpdateView):
    """Editar pabellón (solo admins)."""
    model = Pabellon
    form_class = PabellonForm
    template_name = 'productos/pabellon_form.html'
    success_url = reverse_lazy('productos:pabellon-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Pabellón actualizado exitosamente.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Pabellón'
        context['editando'] = True
        return context


class PabellonDeleteView(AdminRequeridoMixin, DeleteView):
    """Eliminar pabellón (solo admins)."""
    model = Pabellon
    template_name = 'productos/pabellon_confirm_delete.html'
    success_url = reverse_lazy('productos:pabellon-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Pabellón eliminado exitosamente.')
        return super().form_valid(form)


# ============================================================================
# PROVEEDORES (Solo supervisor/admin)
# ============================================================================

class ProveedorListView(SupervisorRequeridoMixin, ListView):
    """Lista de proveedores."""
    model = Proveedor
    template_name = 'productos/proveedor_list.html'
    context_object_name = 'proveedores'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Proveedor.objects.all()
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(ruc__icontains=q) |
                Q(razon_social__icontains=q) |
                Q(nombre_comercial__icontains=q)
            )
        return queryset


class ProveedorCreateView(SupervisorRequeridoMixin, CreateView):
    """Crear proveedor."""
    model = Proveedor
    template_name = 'productos/proveedor_form.html'
    fields = ['ruc', 'razon_social', 'nombre_comercial', 'direccion', 'telefono', 'email', 'contacto']
    success_url = reverse_lazy('productos:proveedor-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Proveedor creado exitosamente.')
        return super().form_valid(form)


class ProveedorDetailView(SupervisorRequeridoMixin, DetailView):
    """Detalle de proveedor."""
    model = Proveedor
    template_name = 'productos/proveedor_detail.html'
    context_object_name = 'proveedor'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contratos'] = self.object.contratos.all()[:10]
        return context


class ProveedorUpdateView(SupervisorRequeridoMixin, UpdateView):
    """Editar proveedor."""
    model = Proveedor
    template_name = 'productos/proveedor_form.html'
    fields = ['ruc', 'razon_social', 'nombre_comercial', 'direccion', 'telefono', 'email', 'contacto', 'activo']
    
    def get_success_url(self):
        return reverse('productos:proveedor-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Proveedor actualizado exitosamente.')
        return super().form_valid(form)


# ============================================================================
# CONTRATOS (Solo supervisor/admin)
# ============================================================================

class ContratoListView(SupervisorRequeridoMixin, ListView):
    """Lista de contratos."""
    model = Contrato
    template_name = 'productos/contrato_list.html'
    context_object_name = 'contratos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Contrato.objects.select_related('proveedor')
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(numero_contrato__icontains=q) |
                Q(proveedor__razon_social__icontains=q)
            )
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Contrato.ESTADOS
        return context


class ContratoCreateView(SupervisorRequeridoMixin, CreateView):
    """Crear contrato."""
    model = Contrato
    template_name = 'productos/contrato_form.html'
    fields = ['numero_contrato', 'proveedor', 'descripcion', 'fecha_inicio', 'fecha_fin', 'monto_total', 'estado', 'observaciones']
    success_url = reverse_lazy('productos:contrato-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proveedores'] = Proveedor.objects.filter(activo=True)
        return context
    
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        messages.success(self.request, 'Contrato creado exitosamente.')
        return super().form_valid(form)


class ContratoDetailView(SupervisorRequeridoMixin, DetailView):
    """Detalle de contrato."""
    model = Contrato
    template_name = 'productos/contrato_detail.html'
    context_object_name = 'contrato'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['anexos'] = self.object.anexos.all()
        context['lotes'] = self.object.lotes.all()
        context['items_directos'] = self.object.items_directos.all()[:20]
        return context


class ContratoUpdateView(SupervisorRequeridoMixin, UpdateView):
    """Editar contrato."""
    model = Contrato
    template_name = 'productos/contrato_form.html'
    fields = ['numero_contrato', 'proveedor', 'descripcion', 'fecha_inicio', 'fecha_fin', 'monto_total', 'estado', 'observaciones']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proveedores'] = Proveedor.objects.filter(activo=True)
        context['editando'] = True
        return context
    
    def get_success_url(self):
        return reverse('productos:contrato-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Contrato actualizado exitosamente.')
        return super().form_valid(form)


class AnexoContratoCreateView(SupervisorRequeridoMixin, CreateView):
    """Crear anexo de contrato."""
    model = AnexoContrato
    template_name = 'productos/anexo_form.html'
    fields = ['numero_anexo', 'fecha', 'descripcion', 'monto_modificacion']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contrato'] = get_object_or_404(Contrato, pk=self.kwargs['pk'])
        return context
    
    def form_valid(self, form):
        form.instance.contrato = get_object_or_404(Contrato, pk=self.kwargs['pk'])
        messages.success(self.request, 'Anexo creado exitosamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('productos:contrato-detail', kwargs={'pk': self.kwargs['pk']})


# ============================================================================
# LOTES
# ============================================================================

class LoteListView(PerfilRequeridoMixin, ListView):
    """Lista de lotes."""
    model = Lote
    template_name = 'productos/lote_list.html'
    context_object_name = 'lotes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Lote.objects.select_related('contrato__proveedor').annotate(
            num_items=Count('items')
        )
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(codigo_lote__icontains=q) |
                Q(codigo_interno__icontains=q) |
                Q(descripcion__icontains=q)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ocultar info de contrato para operadores
        context['mostrar_contrato'] = self.get_user_rol() in ['admin', 'supervisor']
        return context


class LoteCreateView(SupervisorRequeridoMixin, CreateView):
    """Crear lote - solo supervisores y admins."""
    model = Lote
    template_name = 'productos/lote_form.html'
    fields = ['codigo_lote', 'contrato', 'descripcion', 'fecha_adquisicion', 'observaciones']
    success_url = reverse_lazy('productos:lote-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contratos'] = Contrato.objects.filter(estado='vigente')
        context['mostrar_contrato'] = True
        return context
    
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        messages.success(self.request, 'Lote creado exitosamente.')
        return super().form_valid(form)


class LoteDetailView(PerfilRequeridoMixin, DetailView):
    """Detalle de lote."""
    model = Lote
    template_name = 'productos/lote_detail.html'
    context_object_name = 'lote'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.select_related('area', 'tipo_item', 'ambiente')[:50]
        context['mostrar_contrato'] = self.get_user_rol() in ['admin', 'supervisor']
        
        # Alertas de garantía agrupadas
        context['alertas_garantia'] = self.object.items_por_garantia
        return context


class LoteUpdateView(SupervisorRequeridoMixin, UpdateView):
    """Editar lote - solo supervisores y admins."""
    model = Lote
    template_name = 'productos/lote_form.html'
    fields = ['codigo_lote', 'contrato', 'descripcion', 'fecha_adquisicion', 'observaciones', 'activo']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editando'] = True
        context['contratos'] = Contrato.objects.filter(estado='vigente')
        context['mostrar_contrato'] = True
        return context
    
    def get_success_url(self):
        return reverse('productos:lote-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Lote actualizado exitosamente.')
        return super().form_valid(form)


