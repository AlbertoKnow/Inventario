"""
Vistas del sistema de inventario.

Este paquete organiza las vistas por dominio:
- dashboard: HomeView, DashboardView
- item: ItemListView, ItemDetailView, ItemCreateView, etc.
- movimiento: MovimientoListView, aprobar, rechazar, ejecutar, etc.
- ubicacion: Campus, Sede, Pabellon, Ambiente views
- proveedor: Proveedor, Contrato, Lote views
- mantenimiento: Mantenimiento views
- garantia: Garantía views
- acta: Acta views
- colaborador: Colaborador, Gerencia views
- catalogo: TipoItem, Marca, Modelo, Procesador, Software views
- reportes: Reportes y exportaciones
- notificacion: Notificaciones
- api: Endpoints AJAX (búsquedas, autocomplete)

NOTA: Durante la migración, todas las vistas se importan desde views_legacy.
"""

# Re-exportar todo desde el archivo original
from productos.views_legacy import *

# También exportar mixins para uso directo
from productos.views_legacy import (
    PerfilRequeridoMixin,
    SupervisorRequeridoMixin,
    AdminRequeridoMixin,
    AlmacenRequeridoMixin,
    CampusFilterMixin,
)
