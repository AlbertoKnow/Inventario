"""
Formularios relacionados con Items y TipoItem.
"""
from django import forms

from productos.models import (
    Area, Campus, Sede, Pabellon, Ambiente, TipoItem, Item,
    EspecificacionesSistemas, Colaborador, MarcaEquipo, ModeloEquipo, ProcesadorEquipo
)


class ItemForm(forms.ModelForm):
    """Formulario para crear/editar items."""

    # Campos adicionales para seleccion en cascada de ubicacion
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
            # Garantia y Leasing
            'garantia_hasta', 'es_leasing', 'leasing_vencimiento',
        ]
        widgets = {
            'codigo_utp': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'UTP seguido de numeros (ej: UTP296375) o dejar PENDIENTE'
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

        # Solo areas activas
        self.fields['area'].queryset = Area.objects.filter(activo=True)
        self.fields['tipo_item'].queryset = TipoItem.objects.filter(activo=True)
        self.fields['ambiente'].queryset = Ambiente.objects.filter(activo=True)

        # Si estamos editando, precargar los valores de la ubicacion
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

        # Colaboradores para asignacion: activos (incluye genericos como DOCENTE, ALUMNO)
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

        # Si el usuario tiene area asignada, pre-seleccionar
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
        """Si el codigo UTP esta vacio, auto-completar con PENDIENTE."""
        codigo = self.cleaned_data.get('codigo_utp', '').strip()
        if not codigo:
            return 'PENDIENTE'
        return codigo.upper()


class ItemSistemasForm(ItemForm):
    """Formulario extendido para items de Sistemas con especificaciones tecnicas."""

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

    # Campos con catalogos controlados - Marca, Modelo, Procesador
    marca_equipo = forms.ModelChoiceField(
        queryset=MarcaEquipo.objects.filter(activo=True),
        required=False,
        empty_label="---------",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_marca_equipo'})
    )
    modelo_equipo = forms.ModelChoiceField(
        queryset=ModeloEquipo.objects.none(),  # Se carga dinamicamente segun marca
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
                # Cargar valores de catalogo
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
            # Guardar referencias a catalogos
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


class TipoItemForm(forms.ModelForm):
    """Formulario para crear tipos de item (accesible a operadores)."""

    class Meta:
        model = TipoItem
        fields = ['nombre', 'area', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Osciloscopio, Proyector'}),
            'area': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripcion opcional'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Solo areas activas
        self.fields['area'].queryset = Area.objects.filter(activo=True)
        self.fields['descripcion'].required = False

        # Si el usuario tiene area asignada, pre-seleccionar y bloquear
        if self.user and hasattr(self.user, 'perfil'):
            perfil = self.user.perfil
            if perfil.area and perfil.rol != 'admin':
                self.fields['area'].initial = perfil.area
                self.fields['area'].widget.attrs['disabled'] = True

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        area = self.cleaned_data.get('area') or (self.user.perfil.area if hasattr(self.user, 'perfil') else None)

        if nombre and area:
            # Buscar tipos similares (busqueda fuzzy basica)
            nombre_lower = nombre.lower().strip()
            similares = TipoItem.objects.filter(
                area=area,
                nombre__iexact=nombre_lower
            )

            if similares.exists():
                raise forms.ValidationError(
                    f'Ya existe un tipo "{similares.first().nombre}" en esta area.'
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
                        self.advertencia_similares = f'Tipos similares encontrados: {nombres_existentes}. Estas seguro de que quieres crear uno nuevo?'

        return nombre

    def clean(self):
        cleaned_data = super().clean()
        # Si el campo area esta disabled, forzar el valor del perfil del usuario
        if self.user and hasattr(self.user, 'perfil'):
            perfil = self.user.perfil
            if perfil.area and perfil.rol != 'admin':
                cleaned_data['area'] = perfil.area
        return cleaned_data
