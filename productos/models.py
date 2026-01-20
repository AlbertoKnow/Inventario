from django.db import models
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
        sede = self.pabellon.sede
        campus = sede.campus
        return f"{campus.nombre} > {sede.nombre} > Pab. {self.pabellon.letra} > {self.piso_display} > {self.nombre}"

    @property
    def campus(self):
        return self.pabellon.sede.campus

    @property
    def sede(self):
        return self.pabellon.sede


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
        """Genera código automático LOT-YYYY-XXXX."""
        año = timezone.now().year
        ultimo = cls.objects.filter(
            codigo_interno__startswith=f"LOT-{año}-"
        ).order_by('-codigo_interno').first()
        
        if ultimo:
            try:
                ultimo_num = int(ultimo.codigo_interno.split('-')[-1])
                nuevo_num = ultimo_num + 1
            except ValueError:
                nuevo_num = 1
        else:
            nuevo_num = 1
        
        return f"LOT-{año}-{nuevo_num:04d}"
    
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
    """Perfil extendido del usuario con rol, área y campus asignados."""

    ROLES = [
        ('admin', 'Administrador'),
        ('supervisor', 'Supervisor'),
        ('operador', 'Operador'),
        ('externo', 'Externo'),  # Solo para asignación de ítems, sin acceso al sistema
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=20, choices=ROLES, default='operador')
    area = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Área asignada (NULL para administradores y externos)"
    )
    # Campus para operadores (un solo campus)
    campus = models.ForeignKey(
        Campus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operadores',
        help_text="Campus asignado para operadores"
    )
    # Campus para supervisores (pueden tener múltiples)
    campus_asignados = models.ManyToManyField(
        Campus,
        blank=True,
        related_name='supervisores',
        help_text="Campus asignados para supervisores (pueden supervisar varios)"
    )
    departamento = models.CharField(
        max_length=100,
        blank=True,
        help_text="Departamento para usuarios externos (Marketing, Tópico, etc.)"
    )
    telefono = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
    
    def __str__(self):
        nombre = self.usuario.get_full_name() or self.usuario.username
        if self.rol == 'externo' and self.departamento:
            return f"{nombre} - {self.departamento} (Externo)"
        return f"{nombre} - {self.get_rol_display()}"
    
    def save(self, *args, **kwargs):
        # Si es externo, desactivar el usuario para que no pueda loguearse
        if self.rol == 'externo':
            self.usuario.is_active = False
            self.usuario.save(update_fields=['is_active'])
        super().save(*args, **kwargs)

    def get_campus_permitidos(self):
        """
        Retorna los campus que el usuario puede ver según su rol.
        - Admin: todos los campus
        - Supervisor: sus campus_asignados
        - Operador: solo su campus
        """
        if self.rol == 'admin':
            return Campus.objects.filter(activo=True)
        elif self.rol == 'supervisor':
            return self.campus_asignados.filter(activo=True)
        elif self.rol == 'operador' and self.campus:
            return Campus.objects.filter(pk=self.campus.pk, activo=True)
        return Campus.objects.none()

    def puede_ver_campus(self, campus):
        """Verifica si el usuario puede ver un campus específico."""
        if self.rol == 'admin':
            return True
        elif self.rol == 'supervisor':
            return self.campus_asignados.filter(pk=campus.pk).exists()
        elif self.rol == 'operador':
            return self.campus and self.campus.pk == campus.pk
        return False

    @property
    def es_admin(self):
        return self.rol == 'admin'
    
    @property
    def es_supervisor(self):
        return self.rol == 'supervisor'
    
    @property
    def es_operador(self):
        return self.rol == 'operador'
    
    @property
    def es_externo(self):
        return self.rol == 'externo'


# ============================================================================
# MODELO PRINCIPAL: ITEM
# ============================================================================

class Item(models.Model):
    """Modelo principal para todos los ítems del inventario."""
    
    ESTADOS = [
        ('nuevo', 'Nuevo'),
        ('instalado', 'Instalado'),
        ('dañado', 'Dañado'),
        ('obsoleto', 'Obsoleto'),
    ]
    
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
    estado = models.CharField(max_length=20, choices=ESTADOS, default='nuevo')
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

    @classmethod
    def generar_codigo_interno(cls, area_codigo):
        """Genera automáticamente el próximo código interno para un área."""
        prefijos = {
            'sistemas': 'SIS',
            'operaciones': 'OPE',
            'laboratorio': 'LAB',
        }
        prefijo = prefijos.get(area_codigo, 'INV')
        año = timezone.now().year

        # Buscar el último código del área y año
        ultimo = cls.objects.filter(
            codigo_interno__startswith=f"{prefijo}-{año}-"
        ).order_by('-codigo_interno').first()

        if ultimo:
            try:
                ultimo_num = int(ultimo.codigo_interno.split('-')[-1])
                nuevo_num = ultimo_num + 1
            except ValueError:
                nuevo_num = 1
        else:
            nuevo_num = 1

        return f"{prefijo}-{año}-{nuevo_num:04d}"


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
    
    # Identificación
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    
    # Procesador
    procesador = models.CharField(max_length=200, blank=True, help_text="Ej: Intel Core i7-1365U")
    generacion_procesador = models.CharField(max_length=50, blank=True, help_text="Ej: 13va Generación")
    
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
        return f"Specs: {self.item.codigo_utp}"
    
    @property
    def ram_display(self):
        """Muestra la RAM en formato legible."""
        if self.ram_total_gb and self.ram_configuracion:
            return f"{self.ram_total_gb}GB ({self.ram_configuracion}) {self.ram_tipo}"
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
    """Registro de movimientos y cambios en los ítems."""
    
    TIPOS_MOVIMIENTO = [
        ('traslado', 'Traslado'),
        ('cambio_estado', 'Cambio de Estado'),
        ('asignacion', 'Asignación de Usuario'),
        ('entrada', 'Entrada al Inventario'),
        ('baja', 'Baja del Inventario'),
        ('mantenimiento', 'Mantenimiento'),
    ]
    
    ESTADOS_MOVIMIENTO = [
        ('pendiente', 'Pendiente de Aprobación'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('ejecutado', 'Ejecutado'),
        ('ejecutado_emergencia', 'Ejecutado (Emergencia)'),
        ('revertido', 'Revertido'),
    ]
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=TIPOS_MOVIMIENTO)
    estado = models.CharField(max_length=25, choices=ESTADOS_MOVIMIENTO, default='pendiente')
    es_emergencia = models.BooleanField(default=False)
    
    # Cambios de ubicación (ahora referencia a Ambiente)
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
    
    # Cambios de estado
    estado_item_anterior = models.CharField(max_length=20, blank=True)
    estado_item_nuevo = models.CharField(max_length=20, blank=True)
    
    # Cambios de asignación
    usuario_anterior = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='movimientos_usuario_anterior'
    )
    usuario_nuevo = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='movimientos_usuario_nuevo'
    )
    
    # Justificación
    motivo = models.TextField(help_text="Razón del movimiento")
    observaciones = models.TextField(blank=True)
    
    # Autorización
    solicitado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='movimientos_solicitados'
    )
    autorizado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='movimientos_autorizados',
        help_text="Supervisor que debe aprobar"
    )
    
    # Fechas
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    fecha_ejecucion = models.DateTimeField(null=True, blank=True)
    
    # Rechazo
    motivo_rechazo = models.TextField(blank=True)
    
    # Evidencia
    foto_evidencia = models.ImageField(
        upload_to='movimientos/%Y/%m/',
        null=True,
        blank=True,
        validators=[validate_image],
        help_text=f'Formatos permitidos: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}. Máximo 5MB.'
    )
    notas_evidencia = models.TextField(blank=True)
    
    # Escalamiento
    escalado = models.BooleanField(default=False)
    fecha_escalamiento = models.DateTimeField(null=True, blank=True)
    escalado_a = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='movimientos_escalados'
    )
    
    class Meta:
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"
        ordering = ['-fecha_solicitud']
        indexes = [
            models.Index(fields=['item', 'fecha_solicitud']),
            models.Index(fields=['estado', 'fecha_solicitud']),
            models.Index(fields=['autorizado_por', 'estado']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.item.codigo_utp} ({self.get_estado_display()})"
    
    def aprobar(self, usuario):
        """Aprueba el movimiento."""
        self.estado = 'aprobado'
        self.fecha_respuesta = timezone.now()
        self.save()
    
    def rechazar(self, usuario, motivo):
        """Rechaza el movimiento."""
        self.estado = 'rechazado'
        self.motivo_rechazo = motivo
        self.fecha_respuesta = timezone.now()
        self.save()
    
    def ejecutar(self):
        """Ejecuta el movimiento aprobado, actualizando el ítem."""
        if self.estado not in ['aprobado', 'ejecutado_emergencia']:
            return False
        
        item = self.item
        
        # Aplicar cambios según el tipo
        if self.tipo == 'traslado' and self.ambiente_destino:
            item.ambiente = self.ambiente_destino
        
        if self.tipo == 'cambio_estado' and self.estado_item_nuevo:
            item.estado = self.estado_item_nuevo
        
        if self.tipo == 'asignacion':
            item.usuario_asignado = self.usuario_nuevo
        
        item.save()
        
        self.estado = 'ejecutado'
        self.fecha_ejecucion = timezone.now()
        self.save()
        
        return True


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
        return f"{self.numero_acta} - {self.colaborador.nombre_completo}"

    def save(self, *args, **kwargs):
        if not self.numero_acta:
            self.numero_acta = self.generar_numero_acta()
        super().save(*args, **kwargs)

    @classmethod
    def generar_numero_acta(cls):
        """Genera número de acta: TIPO-AÑO-SECUENCIAL"""
        from django.utils import timezone
        año = timezone.now().year

        # Buscar último número del año
        ultimo = cls.objects.filter(
            numero_acta__contains=f"-{año}-"
        ).order_by('-numero_acta').first()

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
        return f"{self.acta.numero_acta} - {self.item.codigo_utp}"

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
