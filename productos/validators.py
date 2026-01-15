"""
Validadores personalizados para el sistema de inventario.

Este módulo contiene validadores de seguridad para archivos subidos,
incluyendo validación de extensiones, tipos MIME y tamaño.
"""

import magic
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.deconstruct import deconstructible


# Extensiones permitidas para imágenes
ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']

# Tipos MIME permitidos para imágenes
ALLOWED_IMAGE_MIME_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
]

# Tamaño máximo de imagen: 5MB
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB en bytes


@deconstructible
class ImageValidator:
    """
    Validador completo para imágenes que verifica:
    - Extensión del archivo
    - Tipo MIME real (usando python-magic)
    - Tamaño máximo del archivo
    """

    def __init__(
        self,
        allowed_extensions=None,
        allowed_mime_types=None,
        max_size=None
    ):
        self.allowed_extensions = allowed_extensions or ALLOWED_IMAGE_EXTENSIONS
        self.allowed_mime_types = allowed_mime_types or ALLOWED_IMAGE_MIME_TYPES
        self.max_size = max_size or MAX_IMAGE_SIZE

    def __call__(self, value):
        """Valida el archivo subido."""
        if not value:
            return

        # 1. Validar extensión
        self._validate_extension(value)

        # 2. Validar tamaño
        self._validate_size(value)

        # 3. Validar tipo MIME real
        self._validate_mime_type(value)

    def _validate_extension(self, value):
        """Valida que la extensión del archivo sea permitida."""
        ext = value.name.split('.')[-1].lower() if '.' in value.name else ''
        if ext not in self.allowed_extensions:
            raise ValidationError(
                f'Extensión de archivo no permitida: .{ext}. '
                f'Extensiones válidas: {", ".join(self.allowed_extensions)}'
            )

    def _validate_size(self, value):
        """Valida que el archivo no exceda el tamaño máximo."""
        if value.size > self.max_size:
            max_mb = self.max_size / (1024 * 1024)
            file_mb = value.size / (1024 * 1024)
            raise ValidationError(
                f'El archivo es demasiado grande ({file_mb:.1f}MB). '
                f'Tamaño máximo permitido: {max_mb:.0f}MB'
            )

    def _validate_mime_type(self, value):
        """
        Valida el tipo MIME real del archivo usando python-magic.
        Esto previene que usuarios renombren archivos maliciosos.
        """
        try:
            # Leer los primeros bytes para detectar el tipo real
            file_content = value.read(2048)
            value.seek(0)  # Rebobinar el archivo

            mime = magic.from_buffer(file_content, mime=True)

            if mime not in self.allowed_mime_types:
                raise ValidationError(
                    f'Tipo de archivo no permitido: {mime}. '
                    f'Solo se permiten imágenes ({", ".join(self.allowed_extensions)})'
                )
        except Exception as e:
            # Si python-magic no está disponible, solo validar extensión
            if 'magic' in str(e).lower():
                pass  # Continuar sin validación MIME si magic no está instalado
            else:
                raise ValidationError(f'Error al validar el archivo: {str(e)}')

    def __eq__(self, other):
        return (
            isinstance(other, ImageValidator) and
            self.allowed_extensions == other.allowed_extensions and
            self.allowed_mime_types == other.allowed_mime_types and
            self.max_size == other.max_size
        )


# Validador por defecto para imágenes de evidencia
validate_image = ImageValidator()

# Validador de extensiones simple (fallback si magic no está disponible)
validate_image_extension = FileExtensionValidator(
    allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
    message='Extensión de archivo no permitida. Use: %(allowed_extensions)s'
)


def validate_file_size(value, max_size=MAX_IMAGE_SIZE):
    """
    Validador simple de tamaño de archivo.
    Uso: validators=[lambda f: validate_file_size(f, max_size=5*1024*1024)]
    """
    if value.size > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = value.size / (1024 * 1024)
        raise ValidationError(
            f'Archivo demasiado grande ({file_mb:.1f}MB). Máximo: {max_mb:.0f}MB'
        )
