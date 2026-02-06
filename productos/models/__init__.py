"""
Modelos del sistema de inventario.

Este paquete contiene todos los modelos organizados por dominio:
- ubicacion: Area, Campus, Sede, Pabellon, Ambiente, TipoItem
- proveedor: Proveedor, Contrato, AnexoContrato, Lote
- usuario: PerfilUsuario
- item: Item, MarcaEquipo, ModeloEquipo, ProcesadorEquipo, EspecificacionesSistemas
- movimiento: Movimiento, MovimientoItem
- mantenimiento: Mantenimiento
- garantia: GarantiaRegistro
- organizacion: Gerencia, Colaborador, SoftwareEstandar
- acta: ActaEntrega, ActaItem, ActaFoto, ActaSoftware
- auditoria: HistorialCambio, Notificacion

NOTA: Durante la migración, algunos modelos aún se importan del archivo monolítico.
Una vez completada la migración, todos vendrán de sus respectivos módulos.
"""

# Por ahora, re-exportamos todo desde el archivo original para mantener compatibilidad
# TODO: Migrar gradualmente cada modelo a su propio archivo
from productos.models_legacy import (
    # Ubicación
    Area,
    Campus,
    Sede,
    Pabellon,
    Ambiente,
    TipoItem,
    # Proveedor
    Proveedor,
    Contrato,
    AnexoContrato,
    Lote,
    # Usuario
    PerfilUsuario,
    # Item
    Item,
    MarcaEquipo,
    ModeloEquipo,
    ProcesadorEquipo,
    EspecificacionesSistemas,
    # Movimiento
    Movimiento,
    MovimientoItem,
    # Mantenimiento
    Mantenimiento,
    # Garantía
    GarantiaRegistro,
    # Organización
    Gerencia,
    Colaborador,
    SoftwareEstandar,
    # Actas
    ActaEntrega,
    ActaItem,
    ActaFoto,
    ActaSoftware,
    # Auditoría
    HistorialCambio,
    Notificacion,
)

__all__ = [
    # Ubicación
    'Area',
    'Campus',
    'Sede',
    'Pabellon',
    'Ambiente',
    'TipoItem',
    # Proveedor
    'Proveedor',
    'Contrato',
    'AnexoContrato',
    'Lote',
    # Usuario
    'PerfilUsuario',
    # Item
    'Item',
    'MarcaEquipo',
    'ModeloEquipo',
    'ProcesadorEquipo',
    'EspecificacionesSistemas',
    # Movimiento
    'Movimiento',
    'MovimientoItem',
    # Mantenimiento
    'Mantenimiento',
    # Garantía
    'GarantiaRegistro',
    # Organización
    'Gerencia',
    'Colaborador',
    'SoftwareEstandar',
    # Actas
    'ActaEntrega',
    'ActaItem',
    'ActaFoto',
    'ActaSoftware',
    # Auditoría
    'HistorialCambio',
    'Notificacion',
]
