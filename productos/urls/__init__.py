"""
URLs del sistema de inventario.

Este paquete organizará las URLs por dominio:
- item: URLs de items
- movimiento: URLs de movimientos
- ubicacion: URLs de ubicaciones
- proveedor: URLs de proveedores
- mantenimiento: URLs de mantenimiento
- garantia: URLs de garantías
- acta: URLs de actas
- colaborador: URLs de colaboradores
- catalogo: URLs de catálogos
- reportes: URLs de reportes
- api: URLs de API/AJAX

NOTA: Durante la migración, todo se importa desde urls_legacy.
"""

# Re-exportar urlpatterns desde el archivo original
from productos.urls_legacy import urlpatterns, app_name
