from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
import re

from .validators import validate_image, ALLOWED_IMAGE_EXTENSIONS


# ============================================================================
# MODELOS DE CONFIGURACIÓN
# ============================================================================

class Area(models.Model):
    """Áreas de gestión del inventario."""
    
    CODIGOS_AREA = [
        ('sistemas', 'Sistemas'),
        ('operaciones', 'Operaciones'),
        ('laboratorio', 'Laboratorio'),
    ]
    
    codigo = models.CharField(max_length=20, choices=CODIGOS_AREA, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


# ============================================================================
# MODELOS DE UBICACIÓN (Jerarquía normalizada)
# ============================================================================

class Campus(models.Model):
    """Campus universitario (nivel más alto de la jerarquía)."""
    
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=10, unique=True, help_text="Ej: CLN, CLS")
    direccion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Campus"
        verbose_name_plural = "Campus"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Sede(models.Model):
    """Sede dentro de un campus."""

    campus = models.ForeignKey(Campus, on_delete=models.PROTECT, related_name='sedes')
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=10, help_text="Código interno. Ej: SP, AN")
    codigo_sede = models.PositiveIntegerField(
        unique=True,
        help_text="Código numérico oficial UTP de la sede (Ej: 77, 78, 1)"
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Sede"
        verbose_name_plural = "Sedes"
        ordering = ['campus', 'nombre']
        unique_together = ['campus', 'codigo']

    def __str__(self):
        return f"{self.nombre} (Sede {self.codigo_sede})"


class Pabellon(models.Model):
    """Pabellón/Edificio dentro de una sede."""

    sede = models.ForeignKey(Sede, on_delete=models.PROTECT, related_name='pabellones')
    letra = models.CharField(
        max_length=1,
        help_text="Letra del pabellón (A-Z)"
    )
    nombre = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nombre descriptivo opcional (Ej: Pabellón Principal, Edificio de Ingenierías)"
    )
    pisos = models.IntegerField(default=1, help_text="Número total de pisos")
    sotanos = models.IntegerField(default=0, help_text="Número de sótanos")
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Pabellón"
        verbose_name_plural = "Pabellones"
        ordering = ['sede', 'letra']
        unique_together = ['sede', 'letra']

    def clean(self):
        """Validar que letra sea una sola letra mayúscula A-Z."""
        if self.letra:
            self.letra = self.letra.upper()
            if not self.letra.isalpha() or len(self.letra) != 1:
                raise ValidationError({
                    'letra': 'Debe ser una sola letra (A-Z)'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.nombre:
            return f"Pabellón {self.letra} - {self.nombre} ({self.sede})"
        return f"Pabellón {self.letra} ({self.sede})"

    @property
    def codigo_completo(self):
        """Retorna el prefijo del código: SEDE + LETRA"""
        return f"{self.sede.codigo_sede}{self.letra}"


class Ambiente(models.Model):
    """Ambiente específico (aula, laboratorio, oficina)."""

    TIPOS_AMBIENTE = [
        ('aula_teorica', 'Aula Teórica'),
        ('lab_computo', 'Laboratorio de Cómputo'),
        ('lab_especializado', 'Laboratorio Especializado'),
        ('administrativo', 'Administrativo'),
    ]

    pabellon = models.ForeignKey(Pabellon, on_delete=models.PROTECT, related_name='ambientes')
    piso = models.IntegerField(help_text="Número de piso (positivo) o sótano (negativo: -1, -2)")
    numero = models.PositiveIntegerField(
        help_text="Número de ambiente en el piso (01-99)"
    )
    tipo = models.CharField(max_length=30, choices=TIPOS_AMBIENTE)
    nombre = models.CharField(max_length=200, help_text="Nombre descriptivo. Ej: Lab. Química, Aula Magna")

    # Código único autogenerado en formato UTP: 77C201
    codigo = models.CharField(max_length=20, unique=True, blank=True, editable=False)

    # Metadata
    capacidad = models.IntegerField(null=True, blank=True, help_text="Capacidad del ambiente")
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ambiente"
        verbose_name_plural = "Ambientes"
        ordering = ['pabellon', 'piso', 'numero']
        unique_together = ['pabellon', 'piso', 'numero']

    def clean(self):
        """Validaciones del ambiente."""
        # Validar que piso no sea 0
        if self.piso == 0:
            raise ValidationError({
                'piso': 'No existe piso 0. Use 1 para planta baja o -1 para sótano 1'
            })
        # Validar número de ambiente (01-99)
        if self.numero and (self.numero < 1 or self.numero > 99):
            raise ValidationError({
                'numero': 'El número de ambiente debe estar entre 01 y 99'
            })

    def save(self, *args, **kwargs):
        self.full_clean()

        if not self.codigo:
            self.codigo = self.generar_codigo()

        super().save(*args, **kwargs)

    def generar_codigo(self):
        """
        Genera código en formato UTP: SEDE + PABELLON + PISO + AMBIENTE

        Ejemplos:
        - 77C201: Sede 77, Pabellón C, Piso 2, Ambiente 01
        - 77A1501: Sede 77, Pabellón A, Piso 15, Ambiente 01
        - 77AS102: Sede 77, Pabellón A, Sótano 1, Ambiente 02
        - 1A101: Sede 1, Pabellón A, Piso 1, Ambiente 01
        """
        sede_codigo = self.pabellon.sede.codigo_sede
        pabellon_letra = self.pabellon.letra

        # Formatear piso: S1, S2 para sótanos; 1, 2, 15 para pisos normales
        if self.piso < 0:
            piso_str = f"S{abs(self.piso)}"
        else:
            piso_str = str(self.piso)

        # Número de ambiente con 2 dígitos
        numero_str = f"{self.numero:02d}"

        return f"{sede_codigo}{pabellon_letra}{piso_str}{numero_str}"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def piso_display(self):
        """Retorna el piso en formato legible."""
        if self.piso < 0:
            return f"Sótano {abs(self.piso)}"
        return f"Piso {self.piso}"

    @property
    def ubicacion_completa(self):
        """Retorna la ubicación completa en formato legible."""
        if not self.pabellon:
            return self.nombre
        sede = self.pabellon.sede
        if not sede:
            return f"Pab. {self.pabellon.letra} > {self.piso_display} > {self.nombre}"
        campus = sede.campus
        if not campus:
            return f"{sede.nombre} > Pab. {self.pabellon.letra} > {self.piso_display} > {self.nombre}"
        return f"{campus.nombre} > {sede.nombre} > Pab. {self.pabellon.letra} > {self.piso_display} > {self.nombre}"

    @property
    def campus(self):
        if self.pabellon and self.pabellon.sede:
            return self.pabellon.sede.campus
        return None

    @property
    def sede(self):
        if self.pabellon:
            return self.pabellon.sede
        return None


class TipoItem(models.Model):
    """Tipo de ítem (Laptop, Silla, Microscopio, etc.)."""
    
    nombre = models.CharField(max_length=100)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='tipos_item')
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Tipo de Ítem"
        verbose_name_plural = "Tipos de Ítem"
        ordering = ['area', 'nombre']
        unique_together = ['nombre', 'area']
    
    def __str__(self):
        return f"{self.nombre} ({self.area.nombre})"


# ============================================================================
# PROVEEDORES Y CONTRATOS (Solo visible para supervisor/admin)
# ============================================================================

class Proveedor(models.Model):
    """Proveedor de bienes y servicios."""
    
    ruc = models.CharField(max_length=20, unique=True, help_text="RUC del proveedor")
    razon_social = models.CharField(max_length=200)
    nombre_comercial = models.CharField(max_length=200, blank=True)
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    contacto = models.CharField(max_length=100, blank=True, help_text="Nombre del contacto")
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['razon_social']
    
    def __str__(self):
        return self.razon_social


class Contrato(models.Model):
    """Contrato con proveedor (información restringida)."""
    
    ESTADOS = [
        ('vigente', 'Vigente'),
        ('vencido', 'Vencido'),
        ('anulado', 'Anulado'),
        ('en_proceso', 'En Proceso'),
    ]
    
    numero_contrato = models.CharField(max_length=50, unique=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='contratos')
    descripcion = models.TextField(blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    monto_total = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Monto total del contrato"
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='vigente')
    observaciones = models.TextField(blank=True)
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='contratos_creados')
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f"{self.numero_contrato} - {self.proveedor.razon_social}"
    
    @property
    def esta_vigente(self):
        if self.estado != 'vigente':
            return False
        if self.fecha_fin:
            return self.fecha_fin >= timezone.now().date()
        return True


class AnexoContrato(models.Model):
    """Anexo o modificación a un contrato."""
    
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='anexos')
    numero_anexo = models.CharField(max_length=50)
    fecha = models.DateField()
    descripcion = models.TextField()
    monto_modificacion = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=0,
        help_text="Monto que modifica al contrato (puede ser positivo o negativo)"
    )
    
    class Meta:
        verbose_name = "Anexo de Contrato"
        verbose_name_plural = "Anexos de Contrato"
        ordering = ['contrato', 'fecha']
        unique_together = ['contrato', 'numero_anexo']
    
    def __str__(self):
        return f"Anexo {self.numero_anexo} - {self.contrato.numero_contrato}"


class Lote(models.Model):
    """Lote de ítems adquiridos juntos."""
    
    codigo_lote = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Código asignado por la institución"
    )
    codigo_interno = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        help_text="Código autogenerado (LOT-YYYY-XXXX)"
    )
    contrato = models.ForeignKey(
        Contrato, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='lotes'
    )
    descripcion = models.CharField(max_length=200)
    fecha_adquisicion = models.DateField()
    observaciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='lotes_creados')
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        ordering = ['-fecha_adquisicion']
    
    def __str__(self):
        if self.codigo_lote:
            return f"{self.codigo_interno} ({self.codigo_lote})"
        return self.codigo_interno
    
    def save(self, *args, **kwargs):
        if not self.codigo_interno:
            self.codigo_interno = self.generar_codigo_interno()
        super().save(*args, **kwargs)
    
    @classmethod
    def generar_codigo_interno(cls):
        """
        Genera código automático LOT-YYYY-XXXX.
        Usa select_for_update() para evitar race conditions en concurrencia.
        """
        año = timezone.now().year
        prefijo = f"LOT-{año}-"

        with transaction.atomic():
            ultimo = cls.objects.filter(
                codigo_interno__startswith=prefijo
            ).select_for_update().order_by('-codigo_interno').first()

            if ultimo:
                try:
                    ultimo_num = int(ultimo.codigo_interno.split('-')[-1])
                    nuevo_num = ultimo_num + 1
                except ValueError:
                    nuevo_num = 1
            else:
                nuevo_num = 1

            return f"{prefijo}{nuevo_num:04d}"
    
    @property
    def cantidad_items(self):
        return self.items.count()
    
    @property
    def items_por_garantia(self):
        """Agrupa items por fecha de garantía para alertas inteligentes."""
        from django.db.models import Count
        return self.items.filter(
            garantia_hasta__isnull=False
        ).values('garantia_hasta').annotate(
            cantidad=Count('id')
        ).order_by('garantia_hasta')


# ============================================================================
# PERFIL DE USUARIO
# ============================================================================

class PerfilUsuario(models.Model):
    """
    Perfil extendido del usuario con rol, área y campus asignados.

    NOTA: Los colaboradores (personas que reciben equipos) se manejan
    con el modelo Colaborador separado. Este modelo es SOLO para
    usuarios que acceden al sistema.
    """

    ROLES = [
        ('admin', 'Administrador'),
        ('gerente', 'Gerente'),
        ('supervisor', 'Supervisor'),
        ('auxiliar', 'Auxiliar de TI'),
        ('almacen', 'Encargado de Almacén'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=20, choices=ROLES, default='auxiliar')
    area = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Área asignada (Gerentes ven todo su área en todos los campus)"
    )
    # Campus para auxiliares (un solo campus)
    campus = models.ForeignKey(
        Campus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auxiliares',
        help_text="Campus asignado para auxiliares de TI"
    )
    # Campus para supervisores (pueden tener múltiples)
    campus_asignados = models.ManyToManyField(
        Campus,
        blank=True,
        related_name='supervisores',
        help_text="Campus asignados para supervisores (pueden supervisar varios)"
    )
    telefono = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        nombre = self.usuario.get_full_name() or self.usuario.username
        return f"{nombre} - {self.get_rol_display()}"

    def get_campus_permitidos(self):
        """
        Retorna los campus que el usuario puede ver según su rol.
        - Admin: todos los campus
        - Gerente: todos los campus (filtrado por área se hace en las vistas)
        - Supervisor: sus campus_asignados
        - Auxiliar: solo su campus
        - Almacén: todos (opera desde almacén central)
        """
        if self.rol in ['admin', 'gerente', 'almacen']:
            return Campus.objects.filter(activo=True)
        elif self.rol == 'supervisor':
            return self.campus_asignados.filter(activo=True)
        elif self.rol == 'auxiliar' and self.campus:
            return Campus.objects.filter(pk=self.campus.pk, activo=True)
        return Campus.objects.none()

    def puede_ver_campus(self, campus):
        """Verifica si el usuario puede ver un campus específico."""
        if self.rol in ['admin', 'gerente', 'almacen']:
            return True
        elif self.rol == 'supervisor':
            return self.campus_asignados.filter(pk=campus.pk).exists()
        elif self.rol == 'auxiliar':
            return self.campus and self.campus.pk == campus.pk
        return False

    def puede_crear_items(self):
        """Solo admin y encargado de almacén pueden crear/editar items."""
        return self.rol in ['admin', 'almacen']

    def puede_aprobar_movimientos(self):
        """Admin, gerente y supervisor pueden aprobar movimientos."""
        return self.rol in ['admin', 'gerente', 'supervisor']

    @property
    def es_admin(self):
        return self.rol == 'admin'

    @property
    def es_gerente(self):
        return self.rol == 'gerente'

    @property
    def es_supervisor(self):
        return self.rol == 'supervisor'

    @property
    def es_auxiliar(self):
        return self.rol == 'auxiliar'

    @property
    def es_almacen(self):
        return self.rol == 'almacen'


# ============================================================================
# MODELO PRINCIPAL: ITEM
# ============================================================================

class Item(models.Model):
    """Modelo principal para todos los ítems del inventario."""

    ESTADOS = [
        ('backup', 'Backup'),
        ('custodia', 'En Custodia'),
        ('instalado', 'Instalado'),
        ('garantia', 'En Garantía'),
        ('mantenimiento', 'En Mantenimiento'),
        ('transito', 'En Tránsito'),
        ('baja', 'Baja'),
    ]

    # Máquina de estados: define transiciones permitidas
    # Formato: estado_actual -> [estados_destino_permitidos]
    TRANSICIONES_PERMITIDAS = {
        'backup': ['instalado', 'custodia', 'mantenimiento', 'garantia', 'transito'],
        'custodia': ['instalado', 'backup', 'mantenimiento', 'garantia', 'transito', 'baja'],
        'instalado': ['backup', 'custodia', 'mantenimiento', 'garantia', 'transito'],
        'garantia': ['instalado', 'backup', 'custodia', 'baja'],  # Regresa reparado o dado de baja
        'mantenimiento': ['instalado', 'backup', 'custodia', 'baja'],  # Regresa reparado o dado de baja
        'transito': ['instalado', 'backup', 'custodia'],  # Llega a destino
        'baja': [],  # Estado final - no puede cambiar
    }

    # Identificación (únicos e inmutables)
    codigo_interno = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text="Código interno autogenerado (ej: SIS-2026-0001)"
    )
    codigo_utp = models.CharField(
        max_length=20,
        default="PENDIENTE",
        help_text="Código de etiqueta física de logística (ej: UTP296375) o PENDIENTE si aún no tiene"
    )
    serie = models.CharField(
        max_length=100,
        unique=True,
        help_text="Número de serie del fabricante"
    )
    
    # Información básica
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    
    # Clasificación
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='items')
    tipo_item = models.ForeignKey(TipoItem, on_delete=models.PROTECT, related_name='items')
    ambiente = models.ForeignKey(
        Ambiente, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='items',
        verbose_name="Ubicación"
    )
    
    # Lote y Contrato (trazabilidad de adquisición)
    lote = models.ForeignKey(
        Lote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
        help_text="Lote al que pertenece el ítem"
    )
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items_directos',
        help_text="Contrato directo (si no pertenece a un lote)"
    )
    
    # Estado y asignación
    estado = models.CharField(max_length=20, choices=ESTADOS, default='custodia')
    usuario_asignado = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items_asignados',
        help_text="[DEPRECADO] Usuario que actualmente tiene asignado el ítem"
    )
    colaborador_asignado = models.ForeignKey(
        'Colaborador',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items_asignados',
        help_text="Colaborador que tiene asignado el ítem actualmente"
    )
    observaciones = models.TextField(blank=True)
    
    # Información económica (opcional - campos de logística)
    fecha_adquisicion = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de adquisición del ítem"
    )
    precio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
        help_text="Precio de adquisición (opcional)"
    )
    
    # Garantía
    garantia_hasta = models.DateField(
        null=True, 
        blank=True,
        help_text="Fecha de vencimiento de garantía"
    )
    
    # Leasing
    es_leasing = models.BooleanField(default=False)
    leasing_empresa = models.CharField(max_length=200, blank=True)
    leasing_contrato = models.CharField(max_length=100, blank=True)
    leasing_vencimiento = models.DateField(null=True, blank=True)
    
    # Auditoría
    creado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='items_creados'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='items_modificados'
    )
    modificado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Ítem"
        verbose_name_plural = "Ítems"
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['codigo_interno']),
            models.Index(fields=['codigo_utp']),
            models.Index(fields=['serie']),
            models.Index(fields=['area', 'estado']),
            models.Index(fields=['ambiente']),
            # Índices compuestos para queries frecuentes
            models.Index(fields=['colaborador_asignado', 'estado']),
            models.Index(fields=['garantia_hasta', 'estado']),
            models.Index(fields=['tipo_item', 'area']),
            models.Index(fields=['estado', '-creado_en']),
            models.Index(fields=['es_leasing', 'leasing_vencimiento']),
        ]
        constraints = [
            # Unicidad de codigo_utp solo cuando no es PENDIENTE
            models.UniqueConstraint(
                fields=['codigo_utp'],
                condition=~models.Q(codigo_utp='PENDIENTE'),
                name='unique_codigo_utp_when_assigned'
            ),
        ]

    def __str__(self):
        return f"{self.codigo_interno} - {self.nombre}"

    def clean(self):
        """Validaciones del modelo."""
        super().clean()

        # Validar formato de codigo_utp si no es PENDIENTE
        if self.codigo_utp and self.codigo_utp != "PENDIENTE":
            # Debe empezar con UTP seguido de números
            if not re.match(r'^UTP\d+$', self.codigo_utp):
                raise ValidationError({
                    'codigo_utp': 'El código UTP debe tener el formato UTPxxxxxxxxx (UTP seguido de números)'
                })

            # Verificar unicidad de códigos UTP reales (excluyendo PENDIENTE)
            if self.pk:
                # Al editar, excluir el ítem actual de la búsqueda
                duplicado = Item.objects.filter(
                    codigo_utp=self.codigo_utp
                ).exclude(pk=self.pk).exists()
            else:
                # Al crear, buscar cualquier duplicado
                duplicado = Item.objects.filter(codigo_utp=self.codigo_utp).exists()

            if duplicado:
                raise ValidationError({
                    'codigo_utp': f'El código UTP {self.codigo_utp} ya existe en el sistema'
                })

    def save(self, *args, **kwargs):
        # Generar codigo_interno si no existe
        if not self.codigo_interno:
            self.codigo_interno = self.generar_codigo_interno(self.area.codigo)

        # Ejecutar validaciones
        self.full_clean()

        super().save(*args, **kwargs)
    
    @property
    def en_garantia(self):
        """Indica si el ítem está actualmente en garantía."""
        if self.garantia_hasta:
            return self.garantia_hasta >= timezone.now().date()
        return False
    
    @property
    def dias_garantia_restantes(self):
        """Retorna los días restantes de garantía, o None si no tiene."""
        if self.garantia_hasta:
            delta = self.garantia_hasta - timezone.now().date()
            return delta.days
        return None
    
    @property
    def leasing_vigente(self):
        """Indica si el leasing está vigente."""
        if self.es_leasing and self.leasing_vencimiento:
            return self.leasing_vencimiento >= timezone.now().date()
        return False

    @property
    def codigo_utp_pendiente(self):
        """Indica si el ítem está esperando código UTP de logística."""
        return self.codigo_utp == "PENDIENTE"

    def puede_cambiar_estado(self, nuevo_estado):
        """
        Verifica si la transición de estado es válida según la máquina de estados.

        Args:
            nuevo_estado: El estado destino propuesto

        Returns:
            bool: True si la transición es válida, False si no
        """
        if self.estado == nuevo_estado:
            return True  # No hay cambio

        estados_permitidos = self.TRANSICIONES_PERMITIDAS.get(self.estado, [])
        return nuevo_estado in estados_permitidos

    def cambiar_estado(self, nuevo_estado, forzar=False):
        """
        Cambia el estado del ítem validando la transición.

        Args:
            nuevo_estado: El estado destino
            forzar: Si True, permite transiciones no válidas (solo admin)

        Returns:
            tuple: (exito: bool, mensaje: str)

        Raises:
            ValidationError: Si la transición no es válida y forzar=False
        """
        if self.estado == nuevo_estado:
            return True, "Estado sin cambios"

        if not forzar and not self.puede_cambiar_estado(nuevo_estado):
            estados_permitidos = self.TRANSICIONES_PERMITIDAS.get(self.estado, [])
            raise ValidationError(
                f"No se puede cambiar de '{self.get_estado_display()}' a "
                f"'{dict(self.ESTADOS).get(nuevo_estado, nuevo_estado)}'. "
                f"Transiciones permitidas: {', '.join(estados_permitidos) or 'ninguna'}"
            )

        estado_anterior = self.estado
        self.estado = nuevo_estado
        self.save(update_fields=['estado', 'modificado_en'])

        return True, f"Estado cambiado de {estado_anterior} a {nuevo_estado}"

    def get_estados_posibles(self):
        """
        Retorna los estados a los que puede transicionar este ítem.

        Returns:
            list: Lista de tuplas (codigo, nombre) de estados permitidos
        """
        estados_permitidos = self.TRANSICIONES_PERMITIDAS.get(self.estado, [])
        return [(e, dict(self.ESTADOS).get(e, e)) for e in estados_permitidos]

    @classmethod
    def generar_codigo_interno(cls, area_codigo):
        """
        Genera automáticamente el próximo código interno para un área.
        Usa select_for_update() para evitar race conditions en concurrencia.
        """
        prefijos = {
            'sistemas': 'SIS',
            'operaciones': 'OPE',
            'laboratorio': 'LAB',
        }
        prefijo = prefijos.get(area_codigo, 'INV')
        año = timezone.now().year
        prefijo_completo = f"{prefijo}-{año}-"

        with transaction.atomic():
            # Buscar el último código del área y año con lock
            ultimo = cls.objects.filter(
                codigo_interno__startswith=prefijo_completo
            ).select_for_update().order_by('-codigo_interno').first()

            if ultimo:
                try:
                    ultimo_num = int(ultimo.codigo_interno.split('-')[-1])
                    nuevo_num = ultimo_num + 1
                except ValueError:
                    nuevo_num = 1
            else:
                nuevo_num = 1

            return f"{prefijo_completo}{nuevo_num:04d}"


# ============================================================================
# CATÁLOGOS PARA ESPECIFICACIONES TÉCNICAS
# ============================================================================

class MarcaEquipo(models.Model):
    """Catálogo de marcas de equipos."""
    nombre = models.CharField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Marca de Equipo"
        verbose_name_plural = "Marcas de Equipos"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ModeloEquipo(models.Model):
    """Catálogo de modelos de equipos (relacionado con marca)."""
    marca = models.ForeignKey(MarcaEquipo, on_delete=models.CASCADE, related_name='modelos')
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Modelo de Equipo"
        verbose_name_plural = "Modelos de Equipos"
        ordering = ['marca__nombre', 'nombre']
        unique_together = ['marca', 'nombre']

    def __str__(self):
        return f"{self.marca.nombre} {self.nombre}"


class ProcesadorEquipo(models.Model):
    """Catálogo de procesadores."""
    nombre = models.CharField(max_length=200, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Procesador"
        verbose_name_plural = "Procesadores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# ============================================================================
# ESPECIFICACIONES TÉCNICAS (Solo para Sistemas)
# ============================================================================

class EspecificacionesSistemas(models.Model):
    """Especificaciones técnicas para ítems del área de Sistemas."""
    
    TIPOS_RAM = [
        ('DDR3', 'DDR3'),
        ('DDR4', 'DDR4'),
        ('DDR5', 'DDR5'),
    ]
    
    TIPOS_ALMACENAMIENTO = [
        ('HDD', 'HDD (Disco Duro)'),
        ('SSD', 'SSD SATA'),
        ('NVMe', 'SSD NVMe'),
        ('eMMC', 'eMMC'),
    ]
    
    item = models.OneToOneField(
        Item, 
        on_delete=models.CASCADE, 
        related_name='especificaciones_sistemas'
    )
    
    # Identificación (usando catálogos)
    marca_equipo = models.ForeignKey(
        MarcaEquipo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='especificaciones', verbose_name="Marca"
    )
    modelo_equipo = models.ForeignKey(
        ModeloEquipo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='especificaciones', verbose_name="Modelo"
    )

    # Procesador (usando catálogo)
    procesador_equipo = models.ForeignKey(
        ProcesadorEquipo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='especificaciones', verbose_name="Procesador"
    )
    generacion_procesador = models.CharField(max_length=50, blank=True, help_text="Ej: 13va Generación")

    # Campos legacy (se eliminarán después de migrar datos)
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    procesador = models.CharField(max_length=200, blank=True, help_text="Legacy - usar procesador_equipo")
    
    # RAM
    ram_total_gb = models.IntegerField(null=True, blank=True, help_text="Total en GB")
    ram_configuracion = models.CharField(max_length=50, blank=True, help_text="Ej: 2x8GB, 1x16GB")
    ram_tipo = models.CharField(max_length=10, choices=TIPOS_RAM, blank=True)
    
    # Almacenamiento
    almacenamiento_gb = models.IntegerField(null=True, blank=True, help_text="Capacidad en GB")
    almacenamiento_tipo = models.CharField(max_length=10, choices=TIPOS_ALMACENAMIENTO, blank=True)
    
    # Software
    sistema_operativo = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = "Especificaciones de Sistemas"
        verbose_name_plural = "Especificaciones de Sistemas"
    
    def __str__(self):
        if self.item:
            return f"Specs: {self.item.codigo_utp}"
        return "Specs: Sin item"

    @property
    def ram_display(self):
        """Muestra la RAM en formato legible."""
        if self.ram_total_gb and self.ram_configuracion:
            tipo = f" {self.ram_tipo}" if self.ram_tipo else ""
            return f"{self.ram_total_gb}GB ({self.ram_configuracion}){tipo}"
        elif self.ram_total_gb:
            return f"{self.ram_total_gb}GB"
        return "-"
    
    @property
    def almacenamiento_display(self):
        """Muestra el almacenamiento en formato legible."""
        if self.almacenamiento_gb and self.almacenamiento_tipo:
            return f"{self.almacenamiento_gb}GB {self.almacenamiento_tipo}"
        elif self.almacenamiento_gb:
            return f"{self.almacenamiento_gb}GB"
        return "-"


# ============================================================================
# MOVIMIENTOS
# ============================================================================

class Movimiento(models.Model):
    """
    Registro de movimientos de ítems.

    Flujo de estados:
    PENDIENTE → APROBADO → EN_EJECUCION → EN_TRANSITO (si aplica) → EJECUTADO
                  ↓
              RECHAZADO

    Para movimientos entre campus diferentes:
    - El auxiliar de ORIGEN marca "En Ejecución" (retira el equipo)
    - El auxiliar de ORIGEN marca "En Tránsito" (el equipo sale)
    - El auxiliar de DESTINO marca "Ejecutado" (confirma recepción)
    """

    TIPOS_MOVIMIENTO = [
        ('traslado', 'Traslado'),
        ('asignacion', 'Asignación'),
        ('prestamo', 'Préstamo'),
        ('mantenimiento', 'Mantenimiento'),
        ('garantia', 'Garantía'),
        ('reemplazo', 'Reemplazo'),
        ('leasing', 'Devolución Leasing'),
    ]

    ESTADOS_MOVIMIENTO = [
        ('pendiente', 'Pendiente de Aprobación'),
        ('aprobado', 'Aprobado'),
        ('en_ejecucion', 'En Ejecución'),
        ('en_transito', 'En Tránsito'),
        ('ejecutado', 'Ejecutado'),
        ('rechazado', 'Rechazado'),
        ('cancelado', 'Cancelado'),
    ]

    # Item principal del movimiento
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='movimientos',
        help_text="Ítem que se mueve/sale"
    )
    tipo = models.CharField(max_length=20, choices=TIPOS_MOVIMIENTO)
    estado = models.CharField(max_length=25, choices=ESTADOS_MOVIMIENTO, default='pendiente')

    # Item de reemplazo (para mantenimiento, garantía, reemplazo, leasing)
    item_reemplazo = models.ForeignKey(
        Item,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_como_reemplazo',
        help_text="Ítem que entra como reemplazo (temporal o definitivo)"
    )
    reemplazo_es_temporal = models.BooleanField(
        default=False,
        help_text="Si es True, el reemplazo es temporal (mantenimiento/garantía)"
    )

    # Ubicaciones
    ambiente_origen = models.ForeignKey(
        Ambiente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_salida',
        verbose_name="Ubicación origen"
    )
    ambiente_destino = models.ForeignKey(
        Ambiente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_entrada',
        verbose_name="Ubicación destino"
    )

    # Estado del item al finalizar (para saber cómo queda: backup, instalado, baja, etc.)
    estado_item_destino = models.CharField(
        max_length=20,
        blank=True,
        help_text="Estado final del ítem al ejecutar (instalado, backup, baja, etc.)"
    )

    # Asignación a colaborador
    colaborador_anterior = models.ForeignKey(
        'Colaborador',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_anterior'
    )
    colaborador_nuevo = models.ForeignKey(
        'Colaborador',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_nuevo'
    )

    # Para préstamos
    fecha_devolucion_esperada = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha esperada de devolución (para préstamos)"
    )
    fecha_devolucion_real = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha real de devolución"
    )

    # Justificación
    motivo = models.TextField(help_text="Razón del movimiento")
    observaciones = models.TextField(blank=True)
    motivo_rechazo = models.TextField(blank=True)

    # Flujo de trabajo - Quién hace qué
    solicitado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='movimientos_solicitados'
    )
    aprobado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_aprobados'
    )
    ejecutado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_ejecutados',
        help_text="Usuario que confirmó la ejecución/recepción"
    )

    # Timestamps del flujo
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_en_ejecucion = models.DateTimeField(null=True, blank=True)
    fecha_en_transito = models.DateTimeField(null=True, blank=True)
    fecha_ejecucion = models.DateTimeField(null=True, blank=True)

    # Evidencia
    foto_evidencia = models.ImageField(
        upload_to='movimientos/%Y/%m/',
        null=True,
        blank=True,
        validators=[validate_image],
        help_text=f'Formatos permitidos: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}. Máximo 5MB.'
    )
    notas_evidencia = models.TextField(blank=True)

    class Meta:
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"
        ordering = ['-fecha_solicitud']
        indexes = [
            models.Index(fields=['item', 'fecha_solicitud']),
            models.Index(fields=['estado', 'fecha_solicitud']),
            models.Index(fields=['tipo', 'estado']),
            models.Index(fields=['aprobado_por', 'estado']),
        ]

    def __str__(self):
        if self.item:
            item_info = self.item.codigo_interno
        elif self.items_movimiento.exists():
            item_info = f"{self.items_movimiento.count()} items"
        else:
            item_info = "Sin items"
        return f"{self.get_tipo_display()} - {item_info} ({self.get_estado_display()})"

    @property
    def es_entre_campus(self):
        """Determina si el movimiento es entre campus diferentes."""
        if self.ambiente_origen and self.ambiente_destino:
            return self.ambiente_origen.campus != self.ambiente_destino.campus
        return False

    @property
    def es_entre_sedes(self):
        """Determina si el movimiento es entre sedes diferentes."""
        if self.ambiente_origen and self.ambiente_destino:
            sede_origen = self.ambiente_origen.pabellon.sede if self.ambiente_origen.pabellon else None
            sede_destino = self.ambiente_destino.pabellon.sede if self.ambiente_destino.pabellon else None
            return sede_origen and sede_destino and sede_origen != sede_destino
        return False

    @property
    def requiere_formato_traslado(self):
        """Indica si el movimiento requiere formato de traslado (entre sedes o campus)."""
        return self.es_entre_sedes or self.es_entre_campus

    @property
    def campus_origen(self):
        """Retorna el campus de origen."""
        if self.ambiente_origen:
            return self.ambiente_origen.campus
        return None

    @property
    def campus_destino(self):
        """Retorna el campus de destino."""
        if self.ambiente_destino:
            return self.ambiente_destino.campus
        return None

    @property
    def requiere_item_reemplazo(self):
        """Indica si este tipo de movimiento puede necesitar un ítem de reemplazo."""
        return self.tipo in ['mantenimiento', 'garantia', 'reemplazo', 'leasing']

    def aprobar(self, usuario):
        """Aprueba el movimiento."""
        if self.estado != 'pendiente':
            return False
        self.estado = 'aprobado'
        self.aprobado_por = usuario
        self.fecha_aprobacion = timezone.now()
        self.save()
        return True

    def rechazar(self, usuario, motivo):
        """Rechaza el movimiento."""
        if self.estado != 'pendiente':
            return False
        self.estado = 'rechazado'
        self.aprobado_por = usuario
        self.motivo_rechazo = motivo
        self.fecha_aprobacion = timezone.now()
        self.save()
        return True

    def marcar_en_ejecucion(self, usuario):
        """
        Marca el movimiento como en ejecución (el auxiliar retiró el equipo).
        El ítem aún no cambia de ubicación.
        """
        if self.estado != 'aprobado':
            return False
        self.estado = 'en_ejecucion'
        self.fecha_en_ejecucion = timezone.now()
        self.save()
        return True

    def marcar_en_transito(self, usuario):
        """
        Marca el movimiento como en tránsito (el equipo salió físicamente).
        El ítem cambia su estado a "En Tránsito".
        Solo aplica para movimientos entre campus.
        """
        if self.estado != 'en_ejecucion':
            return False
        if not self.es_entre_campus:
            return False

        with transaction.atomic():
            self.estado = 'en_transito'
            self.fecha_en_transito = timezone.now()
            self.save()

            # Cambiar estado de los ítems a "En Tránsito"
            for item in self.get_items():
                if item and item.puede_cambiar_estado('transito'):
                    item.estado = 'transito'
                    item.save()

        return True

    # Mapeo de tipo de movimiento -> estado destino por defecto
    ESTADOS_DESTINO_POR_TIPO = {
        'asignacion': 'instalado',
        'prestamo': 'instalado',
        'mantenimiento': 'mantenimiento',
        'garantia': 'garantia',
        'leasing': 'baja',
        'reemplazo': 'instalado',
        # 'traslado' tiene lógica especial
    }

    def _obtener_items_a_procesar(self):
        """Obtiene la lista de items a procesar en el movimiento."""
        items_movimiento = self.items_movimiento.all()

        if items_movimiento.exists():
            return [(mov_item.item, mov_item.estado_item_destino) for mov_item in items_movimiento]
        elif self.item:
            return [(self.item, None)]
        return []

    def _determinar_nuevo_estado(self, item, estado_especifico):
        """
        Determina el nuevo estado del ítem según prioridad.

        Prioridad:
        1. Estado específico del MovimientoItem
        2. Estado definido en el movimiento (estado_item_destino)
        3. Estado por defecto según tipo de movimiento
        """
        if estado_especifico:
            return estado_especifico

        if self.estado_item_destino:
            return self.estado_item_destino

        # Caso especial: traslado
        if self.tipo == 'traslado':
            return 'custodia' if item.estado == 'transito' else None

        return self.ESTADOS_DESTINO_POR_TIPO.get(self.tipo)

    def _actualizar_colaborador_item(self, item):
        """Actualiza la asignación de colaborador según el tipo de movimiento."""
        if self.tipo in ['asignacion', 'prestamo', 'reemplazo']:
            item.colaborador_asignado = self.colaborador_nuevo
        elif self.tipo == 'leasing':
            item.colaborador_asignado = None

    def _procesar_item(self, item, estado_especifico):
        """Procesa un ítem individual durante la ejecución del movimiento."""
        # 1. Actualizar ubicación
        if self.ambiente_destino:
            item.ambiente = self.ambiente_destino

        # 2. Determinar y aplicar nuevo estado
        nuevo_estado = self._determinar_nuevo_estado(item, estado_especifico)
        if nuevo_estado and item.puede_cambiar_estado(nuevo_estado):
            item.estado = nuevo_estado

        # 3. Actualizar colaborador
        self._actualizar_colaborador_item(item)

        item.save()

    def _procesar_item_reemplazo(self):
        """Procesa el ítem de reemplazo si existe."""
        if self.item_reemplazo and self.ambiente_origen:
            self.item_reemplazo.ambiente = self.ambiente_origen
            if self.item_reemplazo.puede_cambiar_estado('instalado'):
                self.item_reemplazo.estado = 'instalado'
            if self.colaborador_anterior:
                self.item_reemplazo.colaborador_asignado = self.colaborador_anterior
            self.item_reemplazo.save()

    def ejecutar(self, usuario):
        """
        Ejecuta el movimiento (confirma recepción/instalación).
        Actualiza la ubicación y estado de todos los ítems según el tipo de movimiento.
        Soporta tanto el modelo antiguo (campo item) como el nuevo (MovimientoItem).

        Args:
            usuario: Usuario que ejecuta el movimiento

        Returns:
            bool: True si se ejecutó correctamente, False si no
        """
        estados_validos = ['aprobado', 'en_ejecucion', 'en_transito']
        if self.estado not in estados_validos:
            return False

        with transaction.atomic():
            # Procesar cada ítem
            for item, estado_especifico in self._obtener_items_a_procesar():
                self._procesar_item(item, estado_especifico)

            # Procesar ítem de reemplazo si existe
            self._procesar_item_reemplazo()

            # Finalizar el movimiento
            self.estado = 'ejecutado'
            self.ejecutado_por = usuario
            self.fecha_ejecucion = timezone.now()
            self.save()

        return True

    def get_items(self):
        """
        Retorna todos los ítems del movimiento (compatible con ambos modelos).
        """
        items_movimiento = self.items_movimiento.all()
        if items_movimiento.exists():
            return [mi.item for mi in items_movimiento]
        elif self.item:
            return [self.item]
        return []

    @property
    def cantidad_items(self):
        """Retorna la cantidad de ítems en el movimiento."""
        count = self.items_movimiento.count()
        if count > 0:
            return count
        return 1 if self.item else 0

    def cancelar(self, usuario, motivo=''):
        """Cancela el movimiento si aún no está ejecutado."""
        if self.estado in ['ejecutado', 'cancelado']:
            return False
        self.estado = 'cancelado'
        if motivo:
            self.observaciones += f"\nCancelado por {usuario}: {motivo}"
        self.save()
        return True


# ============================================================================
# ITEMS DE MOVIMIENTO (Modelo intermedio para múltiples ítems)
# ============================================================================

class MovimientoItem(models.Model):
    """
    Modelo intermedio para relacionar Movimiento con múltiples Items.
    Permite almacenar información específica de cada ítem en el movimiento.
    """

    movimiento = models.ForeignKey(
        Movimiento,
        on_delete=models.CASCADE,
        related_name='items_movimiento'
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='movimientos_item'
    )

    # Estado específico del ítem al finalizar (puede variar por ítem)
    estado_item_destino = models.CharField(
        max_length=20,
        choices=Item.ESTADOS,
        blank=True,
        help_text="Estado final del ítem al ejecutar (si difiere del movimiento)"
    )

    # Observaciones específicas de este ítem
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones específicas para este ítem"
    )

    # Auditoría
    agregado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ítem del Movimiento"
        verbose_name_plural = "Ítems del Movimiento"
        unique_together = ['movimiento', 'item']
        ordering = ['agregado_en']

    def __str__(self):
        return f"{self.movimiento} - {self.item.codigo_interno}"

    @property
    def estado_final(self):
        """Retorna el estado final que tendrá el ítem."""
        if self.estado_item_destino:
            return self.estado_item_destino
        if self.movimiento.estado_item_destino:
            return self.movimiento.estado_item_destino
        if self.movimiento.tipo == 'asignacion':
            return 'instalado'
        return self.item.estado


# ============================================================================
# HISTORIAL DE CAMBIOS
# ============================================================================

class HistorialCambio(models.Model):
    """Registro de cambios en los campos de un ítem."""
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='historial_cambios')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    campo = models.CharField(max_length=100)
    valor_anterior = models.TextField(blank=True)
    valor_nuevo = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Historial de Cambio"
        verbose_name_plural = "Historial de Cambios"
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.item.codigo_utp} - {self.campo} ({self.fecha.strftime('%Y-%m-%d %H:%M')})"


# ============================================================================
# NOTIFICACIONES
# ============================================================================

class Notificacion(models.Model):
    """Notificaciones para usuarios del sistema."""
    
    TIPOS_NOTIFICACION = [
        ('solicitud', 'Nueva Solicitud'),
        ('emergencia', 'Movimiento de Emergencia'),
        ('aprobado', 'Solicitud Aprobada'),
        ('rechazado', 'Solicitud Rechazada'),
        ('recordatorio', 'Recordatorio'),
        ('escalamiento', 'Escalamiento'),
        ('garantia', 'Alerta de Garantía'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPOS_NOTIFICACION)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    url = models.CharField(max_length=500, blank=True, help_text="URL de destino")
    movimiento = models.ForeignKey(
        Movimiento, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notificaciones'
    )
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)
    urgente = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['usuario', 'leida']),
        ]
    
    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"
    
    def marcar_leida(self):
        """Marca la notificación como leída."""
        self.leida = True
        self.save()


# ==============================================================================
# MANTENIMIENTO
# ==============================================================================

class Mantenimiento(models.Model):
    """Registro de mantenimientos preventivos y correctivos"""
    
    TIPO_MANTENIMIENTO = [
        ('preventivo', 'Preventivo'),
        ('correctivo', 'Correctivo'),
    ]
    
    ESTADO_MANTENIMIENTO = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]
    
    RESULTADO = [
        ('reparado', 'Reparado'),
        ('reemplazado', 'Reemplazado'),
        ('no_reparable', 'No Reparable'),
        ('enviado_servicio_externo', 'Enviado a Servicio Externo'),
    ]
    
    # Relaciones
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='mantenimientos',
        help_text="Ítem al que se le realizará el mantenimiento"
    )
    
    # Tipo y estado
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_MANTENIMIENTO,
        help_text="Tipo de mantenimiento"
    )
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_MANTENIMIENTO,
        default='pendiente',
        help_text="Estado actual del mantenimiento"
    )
    
    # Fechas
    fecha_programada = models.DateField(
        help_text="Fecha en que se programa el mantenimiento"
    )
    
    fecha_inicio = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora en que inició el mantenimiento"
    )
    
    fecha_finalizacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora en que finalizó el mantenimiento"
    )
    
    # Descripción
    descripcion_problema = models.TextField(
        blank=True,
        help_text="Descripción del problema o motivo del mantenimiento"
    )
    
    trabajo_realizado = models.TextField(
        blank=True,
        help_text="Descripción del trabajo realizado"
    )
    
    # Personal
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mantenimientos_responsable',
        help_text="Usuario responsable del mantenimiento"
    )
    
    tecnico_asignado = models.CharField(
        max_length=150,
        blank=True,
        help_text="Nombre del técnico que realizó el mantenimiento (puede ser externo)"
    )
    
    # Costos
    costo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Costo del mantenimiento"
    )
    
    proveedor_servicio = models.CharField(
        max_length=200,
        blank=True,
        help_text="Proveedor del servicio de mantenimiento"
    )
    
    # Resultado
    resultado = models.CharField(
        max_length=30,
        choices=RESULTADO,
        blank=True,
        help_text="Resultado del mantenimiento"
    )
    
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones adicionales"
    )
    
    # Próximo mantenimiento (solo para preventivos)
    proximo_mantenimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha programada para el próximo mantenimiento preventivo"
    )
    
    # Auditoría
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mantenimientos_creados'
    )
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_programada']
        verbose_name = 'Mantenimiento'
        verbose_name_plural = 'Mantenimientos'
        indexes = [
            models.Index(fields=['item', 'estado']),
            models.Index(fields=['fecha_programada']),
            models.Index(fields=['tipo', 'estado']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.item.codigo_interno} - {self.fecha_programada}"
    
    @property
    def esta_vencido(self):
        """Verifica si el mantenimiento está vencido"""
        from datetime import date
        if self.estado in ['completado', 'cancelado']:
            return False
        return self.fecha_programada < date.today()
    
    @property
    def dias_para_vencer(self):
        """Calcula días restantes para el mantenimiento"""
        from datetime import date
        if self.estado in ['completado', 'cancelado']:
            return None
        delta = self.fecha_programada - date.today()
        return delta.days
    
    @property
    def duracion(self):
        """Calcula la duración del mantenimiento"""
        if self.fecha_inicio and self.fecha_finalizacion:
            delta = self.fecha_finalizacion - self.fecha_inicio
            horas = delta.total_seconds() / 3600
            return round(horas, 2)
        return None
    
    def iniciar(self, usuario=None):
        """Marca el mantenimiento como en proceso"""
        from django.utils import timezone
        self.estado = 'en_proceso'
        self.fecha_inicio = timezone.now()
        if usuario:
            self.responsable = usuario
        self.save()
    
    def finalizar(self, resultado, trabajo_realizado, costo=None):
        """Finaliza el mantenimiento"""
        from django.utils import timezone
        self.estado = 'completado'
        self.fecha_finalizacion = timezone.now()
        self.resultado = resultado
        self.trabajo_realizado = trabajo_realizado
        if costo:
            self.costo = costo
        self.save()
        
        # Si el ítem estaba en mantenimiento, cambiarlo a operativo
        if self.item.estado == 'en_mantenimiento':
            if resultado in ['reparado', 'reemplazado']:
                self.item.estado = 'operativo'
            elif resultado == 'no_reparable':
                self.item.estado = 'danado'
            self.item.save()
    
    def cancelar(self, motivo=''):
        """Cancela el mantenimiento"""
        self.estado = 'cancelado'
        if motivo:
            self.observaciones += f"\nCancelado: {motivo}"
        self.save()


# ==============================================================================
# REGISTRO DE GARANTÍAS
# ==============================================================================

class GarantiaRegistro(models.Model):
    """Registro de envíos a garantía de equipos."""

    ESTADO_GARANTIA = [
        ('pendiente', 'Pendiente de Envío'),
        ('enviado', 'Enviado al Proveedor'),
        ('en_revision', 'En Revisión'),
        ('reparado', 'Reparado'),
        ('reemplazado', 'Reemplazado'),
        ('rechazado', 'Garantía Rechazada'),
        ('devuelto', 'Devuelto'),
        ('cancelado', 'Cancelado'),
    ]

    TIPO_PROBLEMA = [
        ('hardware', 'Falla de Hardware'),
        ('software', 'Falla de Software'),
        ('pantalla', 'Problema de Pantalla'),
        ('bateria', 'Problema de Batería'),
        ('teclado', 'Problema de Teclado'),
        ('disco', 'Problema de Disco'),
        ('memoria', 'Problema de Memoria'),
        ('otro', 'Otro'),
    ]

    # Relación con el ítem
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='garantias_registro',
        help_text="Ítem enviado a garantía"
    )

    # Estado del registro
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_GARANTIA,
        default='pendiente',
        help_text="Estado actual del proceso de garantía"
    )

    # Tipo de problema
    tipo_problema = models.CharField(
        max_length=20,
        choices=TIPO_PROBLEMA,
        help_text="Tipo de problema reportado"
    )

    # Descripción del problema
    descripcion_problema = models.TextField(
        help_text="Descripción detallada del problema"
    )

    # Datos del proveedor
    proveedor = models.ForeignKey(
        'Proveedor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='garantias_atendidas',
        help_text="Proveedor que atiende la garantía"
    )

    numero_caso = models.CharField(
        max_length=100,
        blank=True,
        help_text="Número de caso o ticket del proveedor"
    )

    contacto_proveedor = models.CharField(
        max_length=200,
        blank=True,
        help_text="Nombre del contacto en el proveedor"
    )

    # Fechas
    fecha_reporte = models.DateField(
        auto_now_add=True,
        help_text="Fecha en que se reportó el problema"
    )

    fecha_envio = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de envío al proveedor"
    )

    fecha_recepcion = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de recepción del equipo reparado/reemplazado"
    )

    # Resultado
    diagnostico_proveedor = models.TextField(
        blank=True,
        help_text="Diagnóstico del proveedor"
    )

    solucion_aplicada = models.TextField(
        blank=True,
        help_text="Solución aplicada por el proveedor"
    )

    equipo_reemplazo = models.ForeignKey(
        Item,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='garantia_como_reemplazo',
        help_text="Si fue reemplazado, el nuevo equipo"
    )

    # Observaciones
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones adicionales"
    )

    # Auditoría
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='garantias_creadas'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Registro de Garantía'
        verbose_name_plural = 'Registros de Garantía'
        indexes = [
            models.Index(fields=['item', 'estado']),
            models.Index(fields=['fecha_reporte']),
            models.Index(fields=['estado', 'fecha_envio']),
        ]

    def __str__(self):
        return f"Garantía {self.item.codigo_interno} - {self.get_estado_display()}"

    def enviar(self, fecha_envio=None):
        """Marca el registro como enviado al proveedor."""
        self.estado = 'enviado'
        self.fecha_envio = fecha_envio or timezone.now().date()
        self.save()
        # Cambiar estado del ítem a garantía
        if self.item.puede_cambiar_estado('garantia'):
            self.item.estado = 'garantia'
            self.item.save()

    def recibir(self, diagnostico, solucion, resultado='reparado', fecha_recepcion=None):
        """Registra la recepción del equipo."""
        self.estado = resultado
        self.fecha_recepcion = fecha_recepcion or timezone.now().date()
        self.diagnostico_proveedor = diagnostico
        self.solucion_aplicada = solucion
        self.save()
        # Cambiar estado del ítem según resultado
        if resultado in ['reparado', 'devuelto']:
            if self.item.puede_cambiar_estado('instalado'):
                self.item.estado = 'instalado'
                self.item.save()
        elif resultado == 'reemplazado':
            if self.item.puede_cambiar_estado('baja'):
                self.item.estado = 'baja'
                self.item.save()

    def cancelar(self, motivo=''):
        """Cancela el registro de garantía."""
        self.estado = 'cancelado'
        if motivo:
            self.observaciones += f"\nCancelado: {motivo}"
        self.save()
        # Restaurar estado del ítem si estaba en garantía
        if self.item.estado == 'garantia':
            if self.item.puede_cambiar_estado('instalado'):
                self.item.estado = 'instalado'
                self.item.save()

    @property
    def dias_en_garantia(self):
        """Calcula los días que lleva el equipo en garantía."""
        if self.fecha_envio:
            fecha_fin = self.fecha_recepcion or timezone.now().date()
            return (fecha_fin - self.fecha_envio).days
        return None


# ==============================================================================
# SISTEMA DE ACTAS DE ENTREGA/DEVOLUCIÓN
# ==============================================================================

class Gerencia(models.Model):
    """Gerencias/Departamentos de la organización."""

    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Gerencia"
        verbose_name_plural = "Gerencias"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Colaborador(models.Model):
    """
    Colaboradores que pueden recibir equipos en asignación.
    Son independientes de los usuarios del sistema (no necesitan loguearse).
    """

    # Identificación
    dni = models.CharField(
        max_length=15,
        unique=True,
        help_text="DNI del colaborador (para búsqueda rápida)"
    )
    nombre_completo = models.CharField(max_length=200)

    # Datos laborales
    cargo = models.CharField(
        max_length=100,
        help_text="Ej: Coordinador Académico, Enfermero, Director"
    )
    gerencia = models.ForeignKey(
        Gerencia,
        on_delete=models.PROTECT,
        related_name='colaboradores',
        help_text="Gerencia/Departamento al que pertenece"
    )
    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        related_name='colaboradores',
        help_text="Sede donde trabaja el colaborador"
    )

    # Contacto
    anexo = models.CharField(
        max_length=20,
        blank=True,
        help_text="Anexo o RPE (teléfono corporativo)"
    )
    correo = models.EmailField(help_text="Correo para envío de actas")

    # Estado
    activo = models.BooleanField(default=True)

    # Auditoría
    creado_en = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='colaboradores_creados'
    )

    class Meta:
        verbose_name = "Colaborador"
        verbose_name_plural = "Colaboradores"
        ordering = ['nombre_completo']
        indexes = [
            models.Index(fields=['dni']),
            models.Index(fields=['nombre_completo']),
            models.Index(fields=['gerencia', 'activo']),
        ]

    def __str__(self):
        return f"{self.nombre_completo} - {self.cargo}"

    @property
    def items_asignados(self):
        """Retorna los ítems actualmente asignados a este colaborador."""
        return Item.objects.filter(colaborador_asignado=self)

    @property
    def cantidad_items_asignados(self):
        return self.items_asignados.count()


class SoftwareEstandar(models.Model):
    """Lista de software que puede incluirse en las actas."""

    nombre = models.CharField(max_length=100, unique=True)
    es_basico = models.BooleanField(
        default=False,
        help_text="Si es True, aparece seleccionado por defecto en todas las actas"
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(
        default=0,
        help_text="Orden de aparición en el acta"
    )

    class Meta:
        verbose_name = "Software Estándar"
        verbose_name_plural = "Software Estándar"
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class ActaEntrega(models.Model):
    """
    Acta de entrega o devolución de equipos.
    Puede contener múltiples ítems.
    """

    TIPOS_ACTA = [
        ('entrega', 'Entrega'),
        ('devolucion', 'Devolución'),
    ]

    # Identificación
    numero_acta = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        help_text="Número autogenerado (ENTREGA-2026-0001)"
    )
    tipo = models.CharField(max_length=15, choices=TIPOS_ACTA)

    # Receptor/Entregador
    colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.PROTECT,
        related_name='actas',
        help_text="Colaborador que recibe o devuelve los equipos"
    )

    # Referencia opcional
    ticket = models.CharField(
        max_length=50,
        blank=True,
        help_text="Número de ticket de Mesa de Ayuda (opcional)"
    )

    # Vinculación con movimiento (para asignaciones/préstamos)
    movimiento = models.OneToOneField(
        'Movimiento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acta_entrega',
        help_text="Movimiento de asignación/préstamo que generó esta acta"
    )

    # Fechas
    fecha = models.DateTimeField(auto_now_add=True)

    # Firmas (guardadas como imágenes PNG)
    firma_receptor = models.ImageField(
        upload_to='actas/firmas/%Y/%m/',
        help_text="Firma del colaborador que recibe/devuelve"
    )
    firma_emisor = models.ImageField(
        upload_to='actas/firmas/%Y/%m/',
        help_text="Firma del usuario que genera el acta"
    )

    # PDF generado
    pdf_archivo = models.FileField(
        upload_to='actas/pdf/%Y/%m/',
        blank=True,
        help_text="PDF del acta generada"
    )

    # Envío de correo
    correo_enviado = models.BooleanField(default=False)
    fecha_envio_correo = models.DateTimeField(null=True, blank=True)

    # Observaciones
    observaciones = models.TextField(blank=True)

    # Auditoría
    creado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='actas_creadas',
        help_text="Usuario que generó el acta"
    )

    class Meta:
        verbose_name = "Acta de Entrega"
        verbose_name_plural = "Actas de Entrega"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['numero_acta']),
            models.Index(fields=['tipo', 'fecha']),
            models.Index(fields=['colaborador', 'fecha']),
        ]

    def __str__(self):
        nombre = self.colaborador.nombre_completo if self.colaborador else 'Sin colaborador'
        return f"{self.numero_acta} - {nombre}"

    def save(self, *args, **kwargs):
        if not self.numero_acta:
            self.numero_acta = self.generar_numero_acta()

        # Determinar si es una creación nueva con movimiento vinculado
        es_nueva = self._state.adding
        super().save(*args, **kwargs)

        # Si es acta nueva vinculada a un movimiento, ejecutarlo automáticamente
        if es_nueva and self.movimiento:
            self._ejecutar_movimiento_vinculado()

    def _ejecutar_movimiento_vinculado(self):
        """
        Ejecuta automáticamente el movimiento vinculado al crear el acta.
        Solo aplica para movimientos de asignación o préstamo.
        """
        movimiento = self.movimiento
        if movimiento and movimiento.tipo in ['asignacion', 'prestamo']:
            # Solo ejecutar si está en estado válido
            estados_validos = ['aprobado', 'en_ejecucion', 'en_transito']
            if movimiento.estado in estados_validos:
                try:
                    movimiento.ejecutar(self.creado_por)
                except Exception:
                    # Registrar el error pero no fallar la creación del acta
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error al ejecutar movimiento {movimiento.pk} desde acta {self.numero_acta}")

    @classmethod
    def generar_numero_acta(cls):
        """
        Genera número de acta: ACTA-AÑO-SECUENCIAL.
        Usa select_for_update() para evitar race conditions en concurrencia.
        """
        año = timezone.now().year
        patron = f"-{año}-"

        with transaction.atomic():
            # Buscar último número del año con lock
            ultimo = cls.objects.filter(
                numero_acta__contains=patron
            ).select_for_update().order_by('-numero_acta').first()

            if ultimo:
                try:
                    ultimo_num = int(ultimo.numero_acta.split('-')[-1])
                    nuevo_num = ultimo_num + 1
                except ValueError:
                    nuevo_num = 1
            else:
                nuevo_num = 1

            return f"ACTA-{año}-{nuevo_num:04d}"

    @property
    def cantidad_items(self):
        return self.items.count()

    @property
    def nombre_emisor(self):
        """Nombre completo del usuario que generó el acta."""
        return self.creado_por.get_full_name() or self.creado_por.username


class ActaItem(models.Model):
    """
    Relación entre Acta e Item.
    Guarda los accesorios entregados/devueltos para cada ítem.
    """

    acta = models.ForeignKey(
        ActaEntrega,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='actas_items'
    )

    # Accesorios incluidos
    acc_cargador = models.BooleanField(default=False, verbose_name="Cargador/Cables")
    acc_cable_seguridad = models.BooleanField(default=False, verbose_name="Cable de seguridad")
    acc_bateria = models.BooleanField(default=False, verbose_name="Batería")
    acc_maletin = models.BooleanField(default=False, verbose_name="Maletín")
    acc_cable_red = models.BooleanField(default=False, verbose_name="Cable de red")
    acc_teclado_mouse = models.BooleanField(default=False, verbose_name="Teclado y Mouse")

    class Meta:
        verbose_name = "Ítem del Acta"
        verbose_name_plural = "Ítems del Acta"
        unique_together = ['acta', 'item']

    def __str__(self):
        acta_num = self.acta.numero_acta if self.acta else 'Sin acta'
        item_cod = self.item.codigo_utp if self.item else 'Sin item'
        return f"{acta_num} - {item_cod}"

    @property
    def accesorios_lista(self):
        """Retorna lista de accesorios marcados."""
        accesorios = []
        if self.acc_cargador:
            accesorios.append("Cargador/Cables")
        if self.acc_cable_seguridad:
            accesorios.append("Cable de seguridad")
        if self.acc_bateria:
            accesorios.append("Batería")
        if self.acc_maletin:
            accesorios.append("Maletín")
        if self.acc_cable_red:
            accesorios.append("Cable de red")
        if self.acc_teclado_mouse:
            accesorios.append("Teclado y Mouse")
        return accesorios


class ActaFoto(models.Model):
    """Fotos adjuntas al acta (evidencia del estado del equipo)."""

    acta = models.ForeignKey(
        ActaEntrega,
        on_delete=models.CASCADE,
        related_name='fotos'
    )
    foto = models.ImageField(
        upload_to='actas/fotos/%Y/%m/',
        help_text="Foto del equipo (se convierte a WebP)"
    )
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        help_text="Descripción opcional de la foto"
    )

    class Meta:
        verbose_name = "Foto del Acta"
        verbose_name_plural = "Fotos del Acta"

    def __str__(self):
        return f"Foto - {self.acta.numero_acta}"


class ActaSoftware(models.Model):
    """Software incluido en el acta."""

    acta = models.ForeignKey(
        ActaEntrega,
        on_delete=models.CASCADE,
        related_name='software'
    )
    software = models.ForeignKey(
        SoftwareEstandar,
        on_delete=models.PROTECT,
        related_name='actas'
    )

    class Meta:
        verbose_name = "Software del Acta"
        verbose_name_plural = "Software del Acta"
        unique_together = ['acta', 'software']

    def __str__(self):
        return f"{self.acta.numero_acta} - {self.software.nombre}"
