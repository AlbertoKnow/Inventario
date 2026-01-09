"""
Filtros personalizados para templates de productos.
"""
from django import template

register = template.Library()


@register.filter
def abs_value(value):
    """Retorna el valor absoluto de un número."""
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value


@register.filter
def piso_display(piso):
    """Muestra el piso de forma legible (Sótano X o Piso X)."""
    try:
        piso = int(piso)
        if piso < 0:
            return f"Sótano {abs(piso)}"
        return f"Piso {piso}"
    except (TypeError, ValueError):
        return piso
