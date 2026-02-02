"""
Imports comunes para todos los formularios.
"""
from django import forms
from django.contrib.auth.models import User

from productos.models import (
    Area, Campus, Sede, Pabellon, Ambiente, TipoItem, Item,
    EspecificacionesSistemas, Movimiento, MovimientoItem, PerfilUsuario, Mantenimiento,
    Gerencia, Colaborador, SoftwareEstandar, ActaEntrega, ActaItem, ActaFoto,
    MarcaEquipo, ModeloEquipo, ProcesadorEquipo
)
from productos.validators import validate_image
