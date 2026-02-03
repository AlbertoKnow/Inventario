from django import forms
from django.contrib.auth.models import User
from .models import (
    Area, Campus, Sede, Pabellon, Ambiente, TipoItem, Item,
    EspecificacionesSistemas, Movimiento, MovimientoItem, PerfilUsuario, Mantenimiento,
    Gerencia, Colaborador, SoftwareEstandar, ActaEntrega, ActaItem, ActaFoto,
    MarcaEquipo, ModeloEquipo, ProcesadorEquipo
)
from .validators import validate_image


class ItemForm(forms.ModelForm):
    """Formulario para crear/editar ítems."""
    
    # Campos adicionales para selección en cascada de ubicación
    campus = forms.ModelChoiceField(
        queryset=Campus.objects.filter(activo=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_campus'})
    )
    sede = forms.ModelChoiceField(
        queryset=Sede.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_sede'})
    )
    pabellon = forms.ModelChoiceField(
        queryset=Pabellon.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_pabellon'})
    )
    
    class Meta:
        model = Item
        fields = [
            # Campos principales
            'codigo_utp', 'serie', 'nombre', 'descripcion', 'area', 'tipo_item', 'ambiente',
            'estado', 'colaborador_asignado', 'observaciones',
            # Garantía y Leasing
            'garantia_hasta', 'es_leasing', 'leasing_vencimiento',
        ]
        widgets = {
            'codigo_utp': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'UTP seguido de números (ej: UTP296375) o dejar PENDIENTE'
            }),
            'serie': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'area': forms.Select(attrs={'class': 'form-select', 'id': 'id_area'}),
            'tipo_item': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_item'}),
            'ambiente': forms.Select(attrs={'class': 'form-select', 'id': 'id_ambiente'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'colaborador_asignado': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'garantia_hasta': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'es_leasing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'leasing_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Solo áreas activas
        self.fields['area'].queryset = Area.objects.filter(activo=True)
        self.fields['tipo_item'].queryset = TipoItem.objects.filter(activo=True)
        self.fields['ambiente'].queryset = Ambiente.objects.filter(activo=True)
        
        # Si estamos editando, precargar los valores de la ubicación
        if self.instance and self.instance.pk and self.instance.ambiente:
            ambiente = self.instance.ambiente
            pabellon = ambiente.pabellon
            sede = pabellon.sede
            campus = sede.campus
            
            self.fields['campus'].initial = campus
            self.fields['sede'].queryset = Sede.objects.filter(campus=campus, activo=True)
            self.fields['sede'].initial = sede
            self.fields['pabellon'].queryset = Pabellon.objects.filter(sede=sede, activo=True)
            self.fields['pabellon'].initial = pabellon
            self.fields['ambiente'].queryset = Ambiente.objects.filter(pabellon=pabellon, activo=True)
        
        # Colaboradores para asignación: activos (incluye genéricos como DOCENTE, ALUMNO)
        self.fields['colaborador_asignado'].queryset = Colaborador.objects.filter(activo=True)
        self.fields['colaborador_asignado'].required = False
        self.fields['colaborador_asignado'].empty_label = "SIN ASIGNAR"
        
        # Campos opcionales
        self.fields['descripcion'].required = False
        self.fields['observaciones'].required = False
        self.fields['garantia_hasta'].required = False
        self.fields['leasing_vencimiento'].required = False
        self.fields['ambiente'].required = False

        # codigo_utp no es requerido en el form (se auto-completa con PENDIENTE)
        self.fields['codigo_utp'].required = False
        
        # Si el usuario tiene área asignada, pre-seleccionar
        if self.user and hasattr(self.user, 'perfil'):
            perfil = self.user.perfil
            if perfil.area and perfil.rol != 'admin':
                self.fields['area'].initial = perfil.area
                self.fields['tipo_item'].queryset = TipoItem.objects.filter(
                    area=perfil.area, activo=True
                )
        
        # Si hay datos POST, cargar los querysets correspondientes para cascada
        if 'campus' in self.data:
            try:
                campus_id = int(self.data.get('campus'))
                self.fields['sede'].queryset = Sede.objects.filter(campus_id=campus_id, activo=True)
            except (ValueError, TypeError):
                pass
        
        if 'sede' in self.data:
            try:
                sede_id = int(self.data.get('sede'))
                self.fields['pabellon'].queryset = Pabellon.objects.filter(sede_id=sede_id, activo=True)
            except (ValueError, TypeError):
                pass
        
        if 'pabellon' in self.data:
            try:
                pabellon_id = int(self.data.get('pabellon'))
                self.fields['ambiente'].queryset = Ambiente.objects.filter(pabellon_id=pabellon_id, activo=True)
            except (ValueError, TypeError):
                pass

    def clean_codigo_utp(self):
        """Si el código UTP está vacío, auto-completar con PENDIENTE."""
        codigo = self.cleaned_data.get('codigo_utp', '').strip()
        if not codigo:
            return 'PENDIENTE'
        return codigo.upper()


class ItemSistemasForm(ItemForm):
    """Formulario extendido para ítems de Sistemas con especificaciones técnicas."""

    # Opciones predefinidas para dropdowns
    GENERACIONES_PROCESADOR = [
        ('', '---------'),
        ('8va Gen', '8va Gen'),
        ('9na Gen', '9na Gen'),
        ('10ma Gen', '10ma Gen'),
        ('11va Gen', '11va Gen'),
        ('12va Gen', '12va Gen'),
        ('13va Gen', '13va Gen'),
        ('14va Gen', '14va Gen'),
    ]

    RAM_GB_CHOICES = [
        ('', '---------'),
        (4, '4 GB'),
        (8, '8 GB'),
        (16, '16 GB'),
        (32, '32 GB'),
        (64, '64 GB'),
    ]

    RAM_CONFIG_CHOICES = [
        ('', '---------'),
        ('1x4GB', '1x4GB'),
        ('1x8GB', '1x8GB'),
        ('2x4GB', '2x4GB'),
        ('1x16GB', '1x16GB'),
        ('2x8GB', '2x8GB'),
        ('2x16GB', '2x16GB'),
        ('4x8GB', '4x8GB'),
        ('2x32GB', '2x32GB'),
        ('4x16GB', '4x16GB'),
    ]

    ALMACENAMIENTO_GB_CHOICES = [
        ('', '---------'),
        (128, '128 GB'),
        (256, '256 GB'),
        (512, '512 GB'),
        (1024, '1 TB'),
        (2048, '2 TB'),
    ]

    SISTEMAS_OPERATIVOS = [
        ('', '---------'),
        ('Windows 10 Pro', 'Windows 10 Pro'),
        ('Windows 11 Pro', 'Windows 11 Pro'),
        ('Windows 10 Home', 'Windows 10 Home'),
        ('Windows 11 Home', 'Windows 11 Home'),
        ('Linux Ubuntu', 'Linux Ubuntu'),
        ('macOS', 'macOS'),
        ('Sin SO', 'Sin SO'),
    ]

    # Campos con catálogos controlados - Marca, Modelo, Procesador
    marca_equipo = forms.ModelChoiceField(
        queryset=MarcaEquipo.objects.filter(activo=True),
        required=False,
        empty_label="---------",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_marca_equipo'})
    )
    modelo_equipo = forms.ModelChoiceField(
        queryset=ModeloEquipo.objects.none(),  # Se carga dinámicamente según marca
        required=False,
        empty_label="---------",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_modelo_equipo'})
    )
    procesador_equipo = forms.ModelChoiceField(
        queryset=ProcesadorEquipo.objects.filter(activo=True),
        required=False,
        empty_label="---------",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Campos con dropdown fijo
    generacion_procesador = forms.ChoiceField(
        choices=GENERACIONES_PROCESADOR,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    ram_total_gb = forms.TypedChoiceField(
        choices=RAM_GB_CHOICES,
        required=False,
        coerce=lambda x: int(x) if x else None,
        empty_value=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    ram_configuracion = forms.ChoiceField(
        choices=RAM_CONFIG_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    ram_tipo = forms.ChoiceField(
        choices=[('', '---------')] + list(EspecificacionesSistemas.TIPOS_RAM),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    almacenamiento_gb = forms.TypedChoiceField(
        choices=ALMACENAMIENTO_GB_CHOICES,
        required=False,
        coerce=lambda x: int(x) if x else None,
        empty_value=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    almacenamiento_tipo = forms.ChoiceField(
        choices=[('', '---------')] + list(EspecificacionesSistemas.TIPOS_ALMACENAMIENTO),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sistema_operativo = forms.ChoiceField(
        choices=SISTEMAS_OPERATIVOS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si estamos editando y el item tiene especificaciones, cargarlas
        if self.instance and self.instance.pk:
            try:
                specs = self.instance.especificaciones_sistemas
                # Cargar valores de catálogo
                self.fields['marca_equipo'].initial = specs.marca_equipo
                self.fields['procesador_equipo'].initial = specs.procesador_equipo
                self.fields['generacion_procesador'].initial = specs.generacion_procesador
                self.fields['ram_total_gb'].initial = specs.ram_total_gb
                self.fields['ram_configuracion'].initial = specs.ram_configuracion
                self.fields['ram_tipo'].initial = specs.ram_tipo
                self.fields['almacenamiento_gb'].initial = specs.almacenamiento_gb
                self.fields['almacenamiento_tipo'].initial = specs.almacenamiento_tipo
                self.fields['sistema_operativo'].initial = specs.sistema_operativo

                # Cargar modelos de la marca seleccionada
                if specs.marca_equipo:
                    self.fields['modelo_equipo'].queryset = ModeloEquipo.objects.filter(
                        marca=specs.marca_equipo, activo=True
                    )
                    self.fields['modelo_equipo'].initial = specs.modelo_equipo
            except EspecificacionesSistemas.DoesNotExist:
                pass

        # Si hay datos POST, cargar modelos de la marca seleccionada
        if 'marca_equipo' in self.data:
            try:
                marca_id = int(self.data.get('marca_equipo'))
                self.fields['modelo_equipo'].queryset = ModeloEquipo.objects.filter(
                    marca_id=marca_id, activo=True
                )
            except (ValueError, TypeError):
                pass

    def save(self, commit=True):
        item = super().save(commit=commit)

        if commit and item.area.codigo == 'sistemas':
            # Crear o actualizar especificaciones
            specs, _ = EspecificacionesSistemas.objects.get_or_create(item=item)
            # Guardar referencias a catálogos
            specs.marca_equipo = self.cleaned_data.get('marca_equipo')
            specs.modelo_equipo = self.cleaned_data.get('modelo_equipo')
            specs.procesador_equipo = self.cleaned_data.get('procesador_equipo')
            specs.generacion_procesador = self.cleaned_data.get('generacion_procesador', '')
            specs.ram_total_gb = self.cleaned_data.get('ram_total_gb')
            specs.ram_configuracion = self.cleaned_data.get('ram_configuracion', '')
            specs.ram_tipo = self.cleaned_data.get('ram_tipo', '')
            specs.almacenamiento_gb = self.cleaned_data.get('almacenamiento_gb')
            specs.almacenamiento_tipo = self.cleaned_data.get('almacenamiento_tipo', '')
            specs.sistema_operativo = self.cleaned_data.get('sistema_operativo', '')
            specs.save()

        return item


class MovimientoForm(forms.ModelForm):
    """Formulario para crear movimientos con soporte para múltiples ítems."""

    # Campo para selección múltiple de ítems
    items = forms.ModelMultipleChoiceField(
        queryset=Item.objects.all(),
        required=True,
        label="Ítems",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'id': 'id_items',
            'size': '8'
        }),
        help_text="Seleccione uno o más ítems (Ctrl+clic para selección múltiple)"
    )

    # Campos adicionales para selección en cascada de ubicación destino
    campus_destino = forms.ModelChoiceField(
        queryset=Campus.objects.filter(activo=True),
        required=False,
        label="Campus",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_campus_destino'})
    )
    sede_destino = forms.ModelChoiceField(
        queryset=Sede.objects.none(),
        required=False,
        label="Sede",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_sede_destino'})
    )
    pabellon_destino = forms.ModelChoiceField(
        queryset=Pabellon.objects.none(),
        required=False,
        label="Pabellón",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_pabellon_destino'})
    )

    class Meta:
        model = Movimiento
        fields = [
            'tipo', 'ambiente_destino', 'estado_item_destino',
            'colaborador_nuevo', 'item_reemplazo', 'reemplazo_es_temporal',
            'fecha_devolucion_esperada', 'motivo', 'observaciones'
        ]
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo'}),
            'ambiente_destino': forms.Select(attrs={'class': 'form-select', 'id': 'id_ambiente_destino'}),
            'estado_item_destino': forms.Select(attrs={'class': 'form-select'}),
            'colaborador_nuevo': forms.Select(attrs={'class': 'form-select'}),
            'item_reemplazo': forms.Select(attrs={'class': 'form-select'}),
            'reemplazo_es_temporal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fecha_devolucion_esperada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.item_preseleccionado = kwargs.pop('item', None)
        super().__init__(*args, **kwargs)

        # Configurar campos opcionales
        self.fields['ambiente_destino'].required = False
        self.fields['estado_item_destino'].required = False
        self.fields['colaborador_nuevo'].required = False
        self.fields['item_reemplazo'].required = False
        self.fields['reemplazo_es_temporal'].required = False
        self.fields['fecha_devolucion_esperada'].required = False
        self.fields['observaciones'].required = False

        # Choices para estado del ítem destino
        self.fields['estado_item_destino'] = forms.ChoiceField(
            choices=[('', '---------')] + list(Item.ESTADOS),
            required=False,
            widget=forms.Select(attrs={'class': 'form-select'}),
            label="Estado final del ítem"
        )

        # Poblar querysets de campos en cascada si hay datos POST
        data = args[0] if args else self.data
        if data:
            try:
                campus_id = data.get('campus_destino')
                if campus_id:
                    self.fields['sede_destino'].queryset = Sede.objects.filter(
                        campus_id=campus_id, activo=True
                    )
            except (ValueError, TypeError):
                pass

            try:
                sede_id = data.get('sede_destino')
                if sede_id:
                    self.fields['pabellon_destino'].queryset = Pabellon.objects.filter(
                        sede_id=sede_id, activo=True
                    )
            except (ValueError, TypeError):
                pass

            try:
                pabellon_id = data.get('pabellon_destino')
                if pabellon_id:
                    self.fields['ambiente_destino'].queryset = Ambiente.objects.filter(
                        pabellon_id=pabellon_id, activo=True
                    )
            except (ValueError, TypeError):
                pass

        # Filtrar ítems por área del usuario
        if self.user and hasattr(self.user, 'perfil'):
            perfil = self.user.perfil
            if perfil.rol != 'admin' and perfil.area:
                self.fields['items'].queryset = Item.objects.filter(area=perfil.area)
                # También filtrar ítems de reemplazo por área
                self.fields['item_reemplazo'].queryset = Item.objects.filter(
                    area=perfil.area, estado__in=['backup', 'custodia']
                )
            else:
                self.fields['items'].queryset = Item.objects.all()
                self.fields['item_reemplazo'].queryset = Item.objects.filter(
                    estado__in=['backup', 'custodia']
                )
        else:
            self.fields['item_reemplazo'].queryset = Item.objects.filter(
                estado__in=['backup', 'custodia']
            )

        # Si hay ítem preseleccionado
        if self.item_preseleccionado:
            self.fields['items'].initial = [self.item_preseleccionado]

        # Si no hay datos POST, mantener todos los ambientes activos disponibles
        if not data:
            self.fields['ambiente_destino'].queryset = Ambiente.objects.filter(activo=True)

        # Colaboradores activos para asignación
        self.fields['colaborador_nuevo'].queryset = Colaborador.objects.filter(activo=True)

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        items = cleaned_data.get('items')
        colaborador_nuevo = cleaned_data.get('colaborador_nuevo')
        ambiente_destino = cleaned_data.get('ambiente_destino')

        # Validar que se haya seleccionado al menos un ítem
        if not items:
            raise forms.ValidationError('Debe seleccionar al menos un ítem.')

        # SEGURIDAD: Validar permisos sobre items seleccionados
        if self.user and hasattr(self.user, 'perfil'):
            perfil = self.user.perfil
            if perfil.rol != 'admin' and perfil.area:
                # Verificar que todos los items pertenecen al área del usuario
                items_no_permitidos = [
                    item for item in items if item.area != perfil.area
                ]
                if items_no_permitidos:
                    codigos = ', '.join([item.codigo_interno for item in items_no_permitidos[:3]])
                    raise forms.ValidationError(
                        f'No tienes permiso para mover los siguientes ítems: {codigos}'
                    )

            # Validar permisos de campus si es auxiliar
            if perfil.rol == 'auxiliar' and perfil.campus:
                campus_permitidos = perfil.get_campus_permitidos()
                for item in items:
                    if item.ambiente and item.ambiente.campus not in campus_permitidos:
                        raise forms.ValidationError(
                            f'No tienes permiso para mover ítems del campus {item.ambiente.campus.nombre}'
                        )

        # Validaciones según el tipo de movimiento
        if tipo == 'traslado':
            if not ambiente_destino:
                raise forms.ValidationError('Debe seleccionar una ubicación destino para el traslado.')

        if tipo == 'asignacion':
            if not colaborador_nuevo:
                raise forms.ValidationError('Debe seleccionar el colaborador al que se asigna el ítem.')
            # Ambiente es opcional si hay colaborador (equipo móvil)
            # Si no hay ambiente, el equipo "sigue" al colaborador

        if tipo == 'prestamo':
            if not cleaned_data.get('fecha_devolucion_esperada'):
                raise forms.ValidationError('Debe indicar la fecha de devolución del préstamo.')
            if not colaborador_nuevo:
                raise forms.ValidationError('Debe seleccionar el colaborador que recibe el préstamo.')
            # Ambiente es opcional si hay colaborador (equipo móvil)

        if tipo in ['mantenimiento', 'garantia', 'reemplazo', 'leasing']:
            # Estos tipos pueden tener ítem de reemplazo opcional
            pass

        return cleaned_data


class RechazoForm(forms.Form):
    """Formulario para rechazar un movimiento."""
    
    motivo_rechazo = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Motivo del rechazo'
    )


class TipoItemForm(forms.ModelForm):
    """Formulario para crear tipos de ítem (accesible a operadores)."""
    
    class Meta:
        model = TipoItem
        fields = ['nombre', 'area', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Osciloscopio, Proyector'}),
            'area': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción opcional'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Solo áreas activas
        self.fields['area'].queryset = Area.objects.filter(activo=True)
        self.fields['descripcion'].required = False
        
        # Si el usuario tiene área asignada, pre-seleccionar y bloquear
        if self.user and hasattr(self.user, 'perfil'):
            perfil = self.user.perfil
            if perfil.area and perfil.rol != 'admin':
                self.fields['area'].initial = perfil.area
                self.fields['area'].widget.attrs['disabled'] = True
    
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        area = self.cleaned_data.get('area') or (self.user.perfil.area if self.user and hasattr(self.user, 'perfil') else None)
        
        if nombre and area:
            # Buscar tipos similares (búsqueda fuzzy básica)
            nombre_lower = nombre.lower().strip()
            similares = TipoItem.objects.filter(
                area=area,
                nombre__iexact=nombre_lower
            )
            
            if similares.exists():
                raise forms.ValidationError(
                    f'Ya existe un tipo "{similares.first().nombre}" en esta área.'
                )
            
            # Buscar coincidencias parciales
            palabras = nombre_lower.split()
            for palabra in palabras:
                if len(palabra) > 3:  # Solo palabras significativas
                    posibles = TipoItem.objects.filter(
                        area=area,
                        nombre__icontains=palabra
                    )
                    if posibles.exists():
                        nombres_existentes = ", ".join([t.nombre for t in posibles[:3]])
                        # Advertencia en lugar de error
                        self.advertencia_similares = f'Tipos similares encontrados: {nombres_existentes}. ¿Estás seguro de que quieres crear uno nuevo?'
        
        return nombre
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Si el área estaba deshabilitada, usar la del perfil
        if self.user and hasattr(self.user, 'perfil'):
            perfil = self.user.perfil
            if perfil.area and perfil.rol != 'admin':
                cleaned_data['area'] = perfil.area
        
        return cleaned_data


class AmbienteForm(forms.ModelForm):
    """Formulario para crear/editar ambientes con selección en cascada."""

    # Campos adicionales para selección en cascada
    campus = forms.ModelChoiceField(
        queryset=Campus.objects.filter(activo=True),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_campus'})
    )
    sede = forms.ModelChoiceField(
        queryset=Sede.objects.none(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_sede'})
    )

    class Meta:
        model = Ambiente
        fields = ['pabellon', 'piso', 'numero', 'tipo', 'nombre', 'capacidad', 'descripcion']
        widgets = {
            'pabellon': forms.Select(attrs={'class': 'form-select', 'id': 'id_pabellon'}),
            'piso': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 1, 2, 15 o -1 para sótano'
            }),
            'numero': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '01-99',
                'min': 1,
                'max': 99
            }),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Lab. Química, Aula Magna'
            }),
            'capacidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        help_texts = {
            'piso': 'Piso 1 = planta baja. Use -1, -2 para sótanos.',
            'numero': 'Número del ambiente en el piso (01-99). El código se generará automáticamente.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['capacidad'].required = False
        self.fields['descripcion'].required = False
        self.fields['pabellon'].queryset = Pabellon.objects.none()

        # Si estamos editando, precargar los valores de la jerarquía
        if self.instance and self.instance.pk:
            pabellon = self.instance.pabellon
            sede = pabellon.sede
            campus = sede.campus

            self.fields['campus'].initial = campus
            self.fields['sede'].queryset = Sede.objects.filter(campus=campus, activo=True)
            self.fields['sede'].initial = sede
            self.fields['pabellon'].queryset = Pabellon.objects.filter(sede=sede, activo=True)

        # Si hay datos POST, cargar los querysets correspondientes
        if 'campus' in self.data:
            try:
                campus_id = int(self.data.get('campus'))
                self.fields['sede'].queryset = Sede.objects.filter(campus_id=campus_id, activo=True)
            except (ValueError, TypeError):
                pass

        if 'sede' in self.data:
            try:
                sede_id = int(self.data.get('sede'))
                self.fields['pabellon'].queryset = Pabellon.objects.filter(sede_id=sede_id, activo=True)
            except (ValueError, TypeError):
                pass


# ============================================================================
# FORMULARIOS PARA GESTIÓN DE UBICACIÓN (Campus, Sede, Pabellón)
# ============================================================================

class CampusForm(forms.ModelForm):
    """Formulario para crear/editar campus."""
    
    class Meta:
        model = Campus
        fields = ['nombre', 'codigo', 'direccion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Campus Lima Norte'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: CLN', 'maxlength': 10}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dirección completa'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['direccion'].required = False


class SedeForm(forms.ModelForm):
    """Formulario para crear/editar sedes."""

    class Meta:
        model = Sede
        fields = ['campus', 'nombre', 'codigo', 'codigo_sede', 'activo']
        widgets = {
            'campus': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Sede La Chorrera'
            }),
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: SP, LC',
                'maxlength': 10
            }),
            'codigo_sede': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 77, 78, 1',
                'min': 1
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'codigo': 'Código interno para identificar la sede',
            'codigo_sede': 'Código numérico oficial UTP de la sede (único a nivel institucional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['campus'].queryset = Campus.objects.filter(activo=True)


class PabellonForm(forms.ModelForm):
    """Formulario para crear/editar pabellones."""

    # Campo adicional para selección en cascada
    campus = forms.ModelChoiceField(
        queryset=Campus.objects.filter(activo=True),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_campus'})
    )

    class Meta:
        model = Pabellon
        fields = ['sede', 'letra', 'nombre', 'pisos', 'sotanos', 'activo']
        widgets = {
            'sede': forms.Select(attrs={'class': 'form-select', 'id': 'id_sede'}),
            'letra': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: A, B, C',
                'maxlength': 1,
                'style': 'text-transform: uppercase;'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre descriptivo (opcional)'
            }),
            'pisos': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'sotanos': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'letra': 'Una sola letra mayúscula (A-Z)',
            'nombre': 'Nombre descriptivo opcional para el pabellón',
            'sotanos': 'Número de niveles de sótano',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sede'].queryset = Sede.objects.none()
        self.fields['nombre'].required = False

        # Si estamos editando, precargar valores
        if self.instance and self.instance.pk:
            sede = self.instance.sede
            campus = sede.campus
            self.fields['campus'].initial = campus
            self.fields['sede'].queryset = Sede.objects.filter(campus=campus, activo=True)

        # Si hay datos POST, cargar sedes del campus seleccionado
        if 'campus' in self.data:
            try:
                campus_id = int(self.data.get('campus'))
                self.fields['sede'].queryset = Sede.objects.filter(campus_id=campus_id, activo=True)
            except (ValueError, TypeError):
                pass


# ==============================================================================
# FORMULARIO DE MANTENIMIENTO
# ==============================================================================

class MantenimientoForm(forms.ModelForm):
    """Formulario para registro de mantenimiento"""
    
    class Meta:
        model = Mantenimiento
        fields = [
            'item', 'tipo', 'fecha_programada', 'descripcion_problema',
            'tecnico_asignado', 'proveedor_servicio', 'costo', 'observaciones',
            'proximo_mantenimiento'
        ]
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'fecha_programada': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'descripcion_problema': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describa el problema o motivo del mantenimiento'
            }),
            'tecnico_asignado': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del técnico responsable'
            }),
            'proveedor_servicio': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Proveedor del servicio (si aplica)'
            }),
            'costo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones adicionales'
            }),
            'proximo_mantenimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'item': 'Ítem',
            'tipo': 'Tipo de Mantenimiento',
            'fecha_programada': 'Fecha Programada',
            'descripcion_problema': 'Descripción del Problema',
            'tecnico_asignado': 'Técnico Asignado',
            'proveedor_servicio': 'Proveedor del Servicio',
            'costo': 'Costo Estimado',
            'observaciones': 'Observaciones',
            'proximo_mantenimiento': 'Próximo Mantenimiento (solo preventivos)'
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si hay usuario, filtrar items por su área
        if user and hasattr(user, 'perfil'):
            perfil = user.perfil
            if perfil.area and perfil.rol != 'admin':
                self.fields['item'].queryset = Item.objects.filter(area=perfil.area)
        
        # Marcar campos opcionales
        self.fields['tecnico_asignado'].required = False
        self.fields['proveedor_servicio'].required = False
        self.fields['costo'].required = False
        self.fields['observaciones'].required = False
        self.fields['proximo_mantenimiento'].required = False


class MantenimientoFinalizarForm(forms.Form):
    """Formulario para finalizar un mantenimiento"""
    
    resultado = forms.ChoiceField(
        choices=Mantenimiento.RESULTADO,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Resultado del Mantenimiento'
    )
    
    trabajo_realizado = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describa el trabajo realizado'
        }),
        label='Trabajo Realizado'
    )
    
    costo = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        }),
        label='Costo Final'
    )


class MantenimientoLoteForm(forms.Form):
    """Formulario para programar mantenimiento a múltiples ítems"""
    
    items = forms.ModelMultipleChoiceField(
        queryset=Item.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Seleccionar Ítems',
        help_text='Selecciona los ítems que recibirán mantenimiento'
    )
    
    tipo = forms.ChoiceField(
        choices=Mantenimiento.TIPO_MANTENIMIENTO,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Tipo de Mantenimiento'
    )
    
    fecha_programada = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Fecha Programada'
    )
    
    descripcion_problema = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describa el motivo del mantenimiento (aplicará a todos los ítems)'
        }),
        label='Descripción del Problema',
        required=False
    )
    
    tecnico_asignado = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre del técnico responsable'
        }),
        label='Técnico Asignado',
        required=False
    )
    
    proveedor_servicio = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Proveedor del servicio (si aplica)'
        }),
        label='Proveedor del Servicio',
        required=False
    )
    
    costo_estimado = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Costo por ítem (opcional)'
        }),
        label='Costo Estimado por Ítem'
    )
    
    proximo_mantenimiento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Próximo Mantenimiento (solo preventivos)'
    )
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Observaciones adicionales'
        }),
        label='Observaciones'
    )
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Si hay usuario, filtrar items por su área
        if user and hasattr(user, 'perfil'):
            perfil = user.perfil
            if perfil.area and perfil.rol != 'admin':
                self.fields['items'].queryset = Item.objects.filter(area=perfil.area)


# ==============================================================================
# FORMULARIOS PARA SISTEMA DE ACTAS
# ==============================================================================

class GerenciaForm(forms.ModelForm):
    """Formulario para crear/editar gerencias."""

    class Meta:
        model = Gerencia
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Marketing, Vida Universitaria, Activos'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Descripción opcional'
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descripcion'].required = False


class ColaboradorForm(forms.ModelForm):
    """Formulario para crear/editar colaboradores."""

    class Meta:
        model = Colaborador
        fields = ['dni', 'nombre_completo', 'cargo', 'gerencia', 'sede', 'anexo', 'correo', 'activo']
        widgets = {
            'dni': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'DNI del colaborador',
                'maxlength': 15
            }),
            'nombre_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del colaborador'
            }),
            'cargo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Coordinador Académico, Enfermero'
            }),
            'gerencia': forms.Select(attrs={'class': 'form-select'}),
            'sede': forms.Select(attrs={'class': 'form-select'}),
            'anexo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Anexo o RPE (teléfono corporativo)'
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@utp.edu.pe'
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gerencia'].queryset = Gerencia.objects.filter(activo=True)
        self.fields['sede'].queryset = Sede.objects.filter(activo=True)
        self.fields['anexo'].required = False


class SoftwareEstandarForm(forms.ModelForm):
    """Formulario para crear/editar software estándar."""

    class Meta:
        model = SoftwareEstandar
        fields = ['nombre', 'es_basico', 'activo', 'orden']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Windows 11 Pro, Office 365'
            }),
            'es_basico': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'orden': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
        }


class ActaEntregaForm(forms.ModelForm):
    """Formulario base para crear actas de entrega/devolución."""

    # Campo para buscar colaborador por DNI
    buscar_dni = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por DNI...',
            'id': 'buscar_dni'
        })
    )

    class Meta:
        model = ActaEntrega
        fields = ['tipo', 'colaborador', 'ticket', 'observaciones']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_acta'}),
            'colaborador': forms.Select(attrs={'class': 'form-select', 'id': 'id_colaborador'}),
            'ticket': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de ticket de Mesa de Ayuda (opcional)'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['colaborador'].queryset = Colaborador.objects.filter(activo=True)
        self.fields['ticket'].required = False
        self.fields['observaciones'].required = False


class ActaItemForm(forms.ModelForm):
    """Formulario para los accesorios de cada ítem en el acta."""

    class Meta:
        model = ActaItem
        fields = [
            'item', 'acc_cargador', 'acc_cable_seguridad', 'acc_bateria',
            'acc_maletin', 'acc_cable_red', 'acc_teclado_mouse'
        ]
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'acc_cargador': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'acc_cable_seguridad': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'acc_bateria': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'acc_maletin': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'acc_cable_red': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'acc_teclado_mouse': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# FormSet para múltiples ítems en un acta
ActaItemFormSet = forms.inlineformset_factory(
    ActaEntrega,
    ActaItem,
    form=ActaItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class ActaFotoForm(forms.ModelForm):
    """Formulario para fotos adjuntas al acta."""

    class Meta:
        model = ActaFoto
        fields = ['foto', 'descripcion']
        widgets = {
            'foto': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción de la foto (opcional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descripcion'].required = False


# FormSet para múltiples fotos en un acta
ActaFotoFormSet = forms.inlineformset_factory(
    ActaEntrega,
    ActaFoto,
    form=ActaFotoForm,
    extra=3,
    can_delete=True,
    max_num=10
)


class FirmaForm(forms.Form):
    """Formulario para capturar las firmas digitales."""

    firma_receptor = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'firma_receptor_data'}),
        required=True
    )
    firma_emisor = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'firma_emisor_data'}),
        required=True
    )


class SeleccionarItemsActaForm(forms.Form):
    """Formulario para seleccionar múltiples ítems para el acta."""

    items = forms.ModelMultipleChoiceField(
        queryset=Item.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Seleccionar Ítems'
    )

    def __init__(self, *args, tipo_acta='entrega', colaborador=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if tipo_acta == 'entrega':
            # Para entrega: mostrar ítems disponibles (sin colaborador asignado)
            queryset = Item.objects.filter(colaborador_asignado__isnull=True)
        else:
            # Para devolución: mostrar ítems asignados al colaborador
            if colaborador:
                queryset = Item.objects.filter(colaborador_asignado=colaborador)
            else:
                queryset = Item.objects.none()

        # Filtrar por área del usuario si no es admin
        if user and hasattr(user, 'perfil'):
            perfil = user.perfil
            if perfil.rol != 'admin' and perfil.area:
                queryset = queryset.filter(area=perfil.area)

        self.fields['items'].queryset = queryset


class SeleccionarSoftwareForm(forms.Form):
    """Formulario para seleccionar software a incluir en el acta."""

    software = forms.ModelMultipleChoiceField(
        queryset=SoftwareEstandar.objects.filter(activo=True),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Software Instalado',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-seleccionar el software básico
        self.fields['software'].initial = SoftwareEstandar.objects.filter(
            activo=True, es_basico=True
        )
