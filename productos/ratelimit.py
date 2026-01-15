"""
Configuración de Rate Limiting para el sistema de inventario.

Este módulo proporciona decoradores y mixins para limitar la tasa de
peticiones a endpoints críticos, protegiendo contra:
- Ataques de fuerza bruta
- Abuso de API
- Sobrecarga del servidor por importaciones masivas
"""

from functools import wraps
from django.http import HttpResponse
from django.core.cache import cache
from django.conf import settings
import time


# Configuración de límites por defecto
RATE_LIMITS = {
    # Importación de archivos: 5 peticiones por minuto
    'import': {'requests': 5, 'window': 60},
    # Búsqueda de items: 30 peticiones por minuto
    'search': {'requests': 30, 'window': 60},
    # Creación de items: 20 peticiones por minuto
    'create': {'requests': 20, 'window': 60},
    # API general: 60 peticiones por minuto
    'api': {'requests': 60, 'window': 60},
    # Exportación de reportes: 10 peticiones por minuto
    'export': {'requests': 10, 'window': 60},
}


def get_client_ip(request):
    """Obtiene la IP real del cliente, considerando proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')
    return ip


def ratelimit(key='default', rate=None, method='ALL'):
    """
    Decorador para aplicar rate limiting a vistas.

    Args:
        key: Identificador del tipo de límite (import, search, create, api, export)
        rate: Tupla (requests, window_seconds) o None para usar RATE_LIMITS[key]
        method: 'GET', 'POST', 'ALL' - métodos HTTP a limitar

    Uso:
        @ratelimit(key='import')
        def mi_vista(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Determinar si aplicar el límite según el método
            if method != 'ALL' and request.method != method:
                return view_func(request, *args, **kwargs)

            # Obtener configuración de límite
            if rate:
                max_requests, window = rate
            else:
                limit_config = RATE_LIMITS.get(key, RATE_LIMITS['api'])
                max_requests = limit_config['requests']
                window = limit_config['window']

            # Generar clave única para este usuario/IP y endpoint
            client_ip = get_client_ip(request)
            user_id = request.user.id if request.user.is_authenticated else 'anon'
            cache_key = f'ratelimit:{key}:{user_id}:{client_ip}'

            # Obtener historial de peticiones
            request_history = cache.get(cache_key, [])
            now = time.time()

            # Limpiar peticiones antiguas fuera de la ventana
            request_history = [t for t in request_history if now - t < window]

            # Verificar límite
            if len(request_history) >= max_requests:
                retry_after = int(window - (now - request_history[0]))
                response = HttpResponse(
                    f'Demasiadas peticiones. Intente de nuevo en {retry_after} segundos.',
                    status=429,
                    content_type='text/plain'
                )
                response['Retry-After'] = str(retry_after)
                return response

            # Registrar esta petición
            request_history.append(now)
            cache.set(cache_key, request_history, window)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class RateLimitMixin:
    """
    Mixin para aplicar rate limiting a Class-Based Views.

    Uso:
        class MiVista(RateLimitMixin, View):
            ratelimit_key = 'import'
            ratelimit_method = 'POST'  # Opcional, default 'ALL'
    """
    ratelimit_key = 'api'
    ratelimit_method = 'ALL'
    ratelimit_rate = None  # Tupla (requests, window) o None para usar default

    def dispatch(self, request, *args, **kwargs):
        # Verificar si aplicar límite según método
        if self.ratelimit_method != 'ALL' and request.method != self.ratelimit_method:
            return super().dispatch(request, *args, **kwargs)

        # Obtener configuración
        if self.ratelimit_rate:
            max_requests, window = self.ratelimit_rate
        else:
            limit_config = RATE_LIMITS.get(self.ratelimit_key, RATE_LIMITS['api'])
            max_requests = limit_config['requests']
            window = limit_config['window']

        # Generar clave única
        client_ip = get_client_ip(request)
        user_id = request.user.id if request.user.is_authenticated else 'anon'
        cache_key = f'ratelimit:{self.ratelimit_key}:{user_id}:{client_ip}'

        # Verificar historial
        request_history = cache.get(cache_key, [])
        now = time.time()
        request_history = [t for t in request_history if now - t < window]

        if len(request_history) >= max_requests:
            retry_after = int(window - (now - request_history[0]))
            response = HttpResponse(
                f'Demasiadas peticiones. Intente de nuevo en {retry_after} segundos.',
                status=429,
                content_type='text/plain'
            )
            response['Retry-After'] = str(retry_after)
            return response

        # Registrar petición
        request_history.append(now)
        cache.set(cache_key, request_history, window)

        return super().dispatch(request, *args, **kwargs)
