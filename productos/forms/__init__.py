"""
Paquete de formularios del modulo productos.

Este paquete organiza los formularios en modulos separados para mejor mantenibilidad.
Para compatibilidad hacia atras, todos los formularios se re-exportan aqui.

Estructura:
- item_forms.py: ItemForm, ItemSistemasForm, TipoItemForm
- movimiento_forms.py: MovimientoForm, RechazoForm (pendiente migracion)
- ubicacion_forms.py: CampusForm, SedeForm, PabellonForm, AmbienteForm (pendiente)
- mantenimiento_forms.py: MantenimientoForm, MantenimientoFinalizarForm, MantenimientoLoteForm (pendiente)
- colaborador_forms.py: GerenciaForm, ColaboradorForm (pendiente)
- acta_forms.py: ActaEntregaForm, ActaItemForm, etc. (pendiente)
"""

# Importar formularios ya migrados a modulos separados
from .item_forms import ItemForm, ItemSistemasForm, TipoItemForm

# Importar formularios desde el archivo legacy (pendientes de migracion)
# Estos se migraran gradualmente a sus propios modulos
from productos.forms_legacy import (
    MovimientoForm,
    RechazoForm,
    AmbienteForm,
    CampusForm,
    SedeForm,
    PabellonForm,
    MantenimientoForm,
    MantenimientoFinalizarForm,
    MantenimientoLoteForm,
    GerenciaForm,
    ColaboradorForm,
    SoftwareEstandarForm,
    ActaEntregaForm,
    ActaItemForm,
    ActaItemFormSet,
    ActaFotoForm,
    ActaFotoFormSet,
    FirmaForm,
    SeleccionarItemsActaForm,
    SeleccionarSoftwareForm,
)

__all__ = [
    # Items
    'ItemForm',
    'ItemSistemasForm',
    'TipoItemForm',
    # Movimientos
    'MovimientoForm',
    'RechazoForm',
    # Ubicaciones
    'AmbienteForm',
    'CampusForm',
    'SedeForm',
    'PabellonForm',
    # Mantenimiento
    'MantenimientoForm',
    'MantenimientoFinalizarForm',
    'MantenimientoLoteForm',
    # Colaboradores
    'GerenciaForm',
    'ColaboradorForm',
    # Actas
    'SoftwareEstandarForm',
    'ActaEntregaForm',
    'ActaItemForm',
    'ActaItemFormSet',
    'ActaFotoForm',
    'ActaFotoFormSet',
    'FirmaForm',
    'SeleccionarItemsActaForm',
    'SeleccionarSoftwareForm',
]
