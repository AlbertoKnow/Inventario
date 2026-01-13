from django.urls import path
from . import views

app_name = 'productos'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Items (usando codigo_utp como slug)
    path('', views.ItemListView.as_view(), name='item-list'),
    path('items/crear/', views.ItemCreateView.as_view(), name='item-create'),
    path('items/importar/', views.ItemImportarView.as_view(), name='item-importar'),
    path('items/importar/plantilla/', views.ItemImportarPlantillaView.as_view(), name='item-importar-plantilla'),
    path('items/importar/confirmar/', views.ItemImportarConfirmarView.as_view(), name='item-importar-confirmar'),
    path('items/<str:codigo>/', views.ItemDetailView.as_view(), name='item-detail'),
    path('items/<str:codigo>/editar/', views.ItemUpdateView.as_view(), name='item-update'),
    path('items/<str:codigo>/eliminar/', views.ItemDeleteView.as_view(), name='item-delete'),
    
    # Movimientos
    path('movimientos/', views.MovimientoListView.as_view(), name='movimiento-list'),
    path('movimientos/pendientes/', views.MovimientoPendientesView.as_view(), name='movimiento-pendientes'),
    path('movimientos/crear/', views.MovimientoCreateView.as_view(), name='movimiento-create'),
    path('movimientos/<int:pk>/', views.MovimientoDetailView.as_view(), name='movimiento-detail'),
    path('movimientos/<int:pk>/aprobar/', views.MovimientoAprobarView.as_view(), name='movimiento-aprobar'),
    path('movimientos/<int:pk>/rechazar/', views.MovimientoRechazarView.as_view(), name='movimiento-rechazar'),
    
    # Notificaciones
    path('notificaciones/', views.NotificacionListView.as_view(), name='notificacion-list'),
    path('notificaciones/<int:pk>/leer/', views.NotificacionMarcarLeidaView.as_view(), name='notificacion-leer'),
    path('notificaciones/leer-todas/', views.NotificacionMarcarTodasLeidasView.as_view(), name='notificacion-leer-todas'),
    
    # Tipos de Ítem (creación por operadores)
    path('tipos-item/', views.TipoItemListView.as_view(), name='tipoitem-list'),
    path('tipos-item/crear/', views.TipoItemCreateView.as_view(), name='tipoitem-create'),
    
    # Ubicaciones (Ambientes)
    path('ubicaciones/', views.UbicacionListView.as_view(), name='ubicacion-list'),
    path('ubicaciones/crear/', views.UbicacionCreateView.as_view(), name='ubicacion-create'),
    path('ubicaciones/<int:pk>/', views.UbicacionDetailView.as_view(), name='ubicacion-detail'),
    path('ubicaciones/<int:pk>/editar/', views.UbicacionUpdateView.as_view(), name='ubicacion-update'),
    
    # Gestión de Jerarquía de Ubicación (solo admins)
    # Campus
    path('campus/', views.CampusListView.as_view(), name='campus-list'),
    path('campus/crear/', views.CampusCreateView.as_view(), name='campus-create'),
    path('campus/<int:pk>/editar/', views.CampusUpdateView.as_view(), name='campus-update'),
    path('campus/<int:pk>/eliminar/', views.CampusDeleteView.as_view(), name='campus-delete'),
    
    # Sedes
    path('sedes/', views.SedeListView.as_view(), name='sede-list'),
    path('sedes/crear/', views.SedeCreateView.as_view(), name='sede-create'),
    path('sedes/<int:pk>/editar/', views.SedeUpdateView.as_view(), name='sede-update'),
    path('sedes/<int:pk>/eliminar/', views.SedeDeleteView.as_view(), name='sede-delete'),
    
    # Pabellones
    path('pabellones/', views.PabellonListView.as_view(), name='pabellon-list'),
    path('pabellones/crear/', views.PabellonCreateView.as_view(), name='pabellon-create'),
    path('pabellones/<int:pk>/editar/', views.PabellonUpdateView.as_view(), name='pabellon-update'),
    path('pabellones/<int:pk>/eliminar/', views.PabellonDeleteView.as_view(), name='pabellon-delete'),
    
    # Proveedores (solo supervisor/admin)
    path('proveedores/', views.ProveedorListView.as_view(), name='proveedor-list'),
    path('proveedores/crear/', views.ProveedorCreateView.as_view(), name='proveedor-create'),
    path('proveedores/<int:pk>/', views.ProveedorDetailView.as_view(), name='proveedor-detail'),
    path('proveedores/<int:pk>/editar/', views.ProveedorUpdateView.as_view(), name='proveedor-update'),
    
    # Contratos (solo supervisor/admin)
    path('contratos/', views.ContratoListView.as_view(), name='contrato-list'),
    path('contratos/crear/', views.ContratoCreateView.as_view(), name='contrato-create'),
    path('contratos/<int:pk>/', views.ContratoDetailView.as_view(), name='contrato-detail'),
    path('contratos/<int:pk>/editar/', views.ContratoUpdateView.as_view(), name='contrato-update'),
    path('contratos/<int:pk>/anexo/', views.AnexoContratoCreateView.as_view(), name='anexo-create'),
    
    # Lotes
    path('lotes/', views.LoteListView.as_view(), name='lote-list'),
    path('lotes/crear/', views.LoteCreateView.as_view(), name='lote-create'),
    path('lotes/<int:pk>/', views.LoteDetailView.as_view(), name='lote-detail'),
    path('lotes/<int:pk>/editar/', views.LoteUpdateView.as_view(), name='lote-update'),

    # Reportes y Exportación
    path('reportes/', views.ReportesView.as_view(), name='reportes'),
    path('reportes/exportar/inventario-excel/', views.ExportarInventarioExcelView.as_view(), name='exportar-inventario-excel'),
    path('reportes/exportar/inventario-pdf/', views.ExportarInventarioPDFView.as_view(), name='exportar-inventario-pdf'),
    path('reportes/exportar/por-area-excel/', views.ExportarReportePorAreaExcelView.as_view(), name='exportar-por-area-excel'),
    path('reportes/exportar/por-area-pdf/', views.ExportarReportePorAreaPDFView.as_view(), name='exportar-por-area-pdf'),
    path('reportes/exportar/garantias-excel/', views.ExportarGarantiasVencenExcelView.as_view(), name='exportar-garantias-excel'),

    # Mantenimiento
    path('mantenimientos/', views.MantenimientoListView.as_view(), name='mantenimiento-list'),
    path('mantenimientos/crear/', views.MantenimientoCreateView.as_view(), name='mantenimiento-create'),
    path('mantenimientos/lote/', views.MantenimientoLoteView.as_view(), name='mantenimiento-lote'),
    path('mantenimientos/<int:pk>/', views.MantenimientoDetailView.as_view(), name='mantenimiento-detail'),
    path('mantenimientos/<int:pk>/editar/', views.MantenimientoUpdateView.as_view(), name='mantenimiento-update'),
    path('mantenimientos/<int:pk>/iniciar/', views.MantenimientoIniciarView.as_view(), name='mantenimiento-iniciar'),
    path('mantenimientos/<int:pk>/finalizar/', views.MantenimientoFinalizarView.as_view(), name='mantenimiento-finalizar'),
    path('mantenimientos/<int:pk>/cancelar/', views.MantenimientoCancelarView.as_view(), name='mantenimiento-cancelar'),
    path('mantenimientos/<int:pk>/eliminar/', views.MantenimientoDeleteView.as_view(), name='mantenimiento-delete'),

    # API endpoints (JSON)
    path('api/tipos-item/', views.TiposItemPorAreaView.as_view(), name='api-tipos-item'),
    path('api/supervisores/', views.SupervisoresPorAreaView.as_view(), name='api-supervisores'),
    path('api/sedes/', views.SedesPorCampusView.as_view(), name='api-sedes'),
    path('api/pabellones/', views.PabellonesPorSedeView.as_view(), name='api-pabellones'),
    path('api/ambientes/', views.AmbientesPorPabellonView.as_view(), name='api-ambientes'),
    path('api/items-buscar/', views.BuscarItemsView.as_view(), name='api-items-buscar'),
    path('api/item-detalle/', views.ObtenerItemDetalleView.as_view(), name='api-item-detalle'),
]
