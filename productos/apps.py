from django.apps import AppConfig


class ProductosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'productos'
    verbose_name = 'Inventario UTP'
    
    def ready(self):
        """Importar signals cuando la app esté lista."""
        import productos.signals  # noqa
