"""
Context processors para la aplicación productos.
"""


def perfil_usuario(request):
    """
    Añade el perfil del usuario al contexto de todos los templates.
    """
    perfil = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, 'perfil', None)
    return {'perfil': perfil}
