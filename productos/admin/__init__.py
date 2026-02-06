"""
Configuración de admin del sistema de inventario.

Este paquete organiza los admins por dominio:
- usuario: UserAdmin con PerfilUsuarioInline
- ubicacion: Area, Campus, Sede, Pabellon, Ambiente, TipoItem
- item: ItemAdmin con EspecificacionesSistemasInline
- movimiento: MovimientoAdmin con MovimientoItemInline
- proveedor: Proveedor, Contrato, AnexoContrato, Lote
- mantenimiento: MantenimientoAdmin
- garantia: GarantiaRegistroAdmin
- acta: ActaEntregaAdmin con inlines
- organizacion: Gerencia, Colaborador, SoftwareEstandar

NOTA: Durante la migración, todo se importa desde admin_legacy.
"""

# Re-exportar todo desde el archivo original
from productos.admin_legacy import *
