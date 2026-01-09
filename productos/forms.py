from django import forms
from django.contrib.auth.models import User
from .models import (
    Area, Campus, Sede, Pabellon, Ambiente, TipoItem, Item, 
    EspecificacionesSistemas, Movimiento, PerfilUsuario, Lote
)


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
            'serie', 'nombre', 'descripcion', 'area', 'tipo_item', 'ambiente',
            'estado', 'usuario_asignado', 'observaciones', 'fecha_adquisicion',
            'precio', 'garantia_hasta', 'es_leasing', 'leasing_empresa',
            'leasing_contrato', 'leasing_vencimiento', 'lote'
        ]
        widgets = {
            'serie': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'area': forms.Select(attrs={'class': 'form-select', 'id': 'id_area'}),
            'tipo_item': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_item'}),
            'ambiente': forms.Select(attrs={'class': 'form-select', 'id': 'id_ambiente'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'usuario_asignado': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fecha_adquisicion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'garantia_hasta': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'es_leasing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'leasing_empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'leasing_contrato': forms.TextInput(attrs={'class': 'form-control'}),
            'leasing_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'lote': forms.Select(attrs={'class': 'form-select'}),
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
        
        # Usuarios para asignación: activos + externos (is_active=False pero rol=externo)
        usuarios_activos = User.objects.filter(is_active=True)
        usuarios_externos = User.objects.filter(
            is_active=False,
            perfil__rol='externo'
        )
        self.fields['usuario_asignado'].queryset = usuarios_activos | usuarios_externos
        self.fields['usuario_asignado'].required = False
        
        # Campos opcionales
        self.fields['descripcion'].required = False
        self.fields['observaciones'].required = False
        self.fields['garantia_hasta'].required = False
        self.fields['leasing_empresa'].required = False
        self.fields['leasing_contrato'].required = False
        self.fields['leasing_vencimiento'].required = False
        self.fields['ambiente'].required = False
        self.fields['lote'].required = False
        self.fields['lote'].queryset = Lote.objects.filter(activo=True)
        
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


class ItemSistemasForm(ItemForm):
    """Formulario extendido para ítems de Sistemas con especificaciones técnicas."""
    
    # Campos adicionales de especificaciones
    marca = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    modelo = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    procesador = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    generacion_procesador = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    ram_total_gb = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    ram_configuracion = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 2x8GB'}))
    ram_tipo = forms.ChoiceField(choices=[('', '---------')] + list(EspecificacionesSistemas.TIPOS_RAM), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    almacenamiento_gb = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    almacenamiento_tipo = forms.ChoiceField(choices=[('', '---------')] + list(EspecificacionesSistemas.TIPOS_ALMACENAMIENTO), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    sistema_operativo = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    def save(self, commit=True):
        item = super().save(commit=commit)
        
        if commit and item.area.codigo == 'sistemas':
            # Crear o actualizar especificaciones
            specs, created = EspecificacionesSistemas.objects.get_or_create(item=item)
            specs.marca = self.cleaned_data.get('marca', '')
            specs.modelo = self.cleaned_data.get('modelo', '')
            specs.procesador = self.cleaned_data.get('procesador', '')
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
    """Formulario para crear movimientos."""
    
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
            'item', 'tipo', 'es_emergencia', 'ambiente_destino',
            'estado_item_nuevo', 'usuario_nuevo', 'motivo', 'observaciones',
            'autorizado_por', 'foto_evidencia', 'notas_evidencia'
        ]
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo'}),
            'es_emergencia': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ambiente_destino': forms.Select(attrs={'class': 'form-select', 'id': 'id_ambiente_destino'}),
            'estado_item_nuevo': forms.Select(attrs={'class': 'form-select'}),
            'usuario_nuevo': forms.Select(attrs={'class': 'form-select'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'autorizado_por': forms.Select(attrs={'class': 'form-select', 'id': 'id_autorizado_por'}),
            'foto_evidencia': forms.FileInput(attrs={'class': 'form-control'}),
            'notas_evidencia': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.item_preseleccionado = kwargs.pop('item', None)
        super().__init__(*args, **kwargs)
        
        # Configurar campos opcionales
        self.fields['ambiente_destino'].required = False
        self.fields['estado_item_nuevo'].required = False
        self.fields['usuario_nuevo'].required = False
        self.fields['observaciones'].required = False
        self.fields['foto_evidencia'].required = False
        self.fields['notas_evidencia'].required = False
        
        # Choices para estado del ítem
        self.fields['estado_item_nuevo'] = forms.ChoiceField(
            choices=[('', '---------')] + list(Item.ESTADOS),
            required=False,
            widget=forms.Select(attrs={'class': 'form-select'})
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
                self.fields['item'].queryset = Item.objects.filter(area=perfil.area)
            else:
                self.fields['item'].queryset = Item.objects.all()
        
        # Si hay ítem preseleccionado
        if self.item_preseleccionado:
            self.fields['item'].initial = self.item_preseleccionado
            self.fields['item'].widget = forms.HiddenInput()
            
            # Filtrar autorizadores por área del ítem
            area = self.item_preseleccionado.area
            supervisores = User.objects.filter(
                perfil__area=area,
                perfil__rol='supervisor',
                perfil__activo=True,
                is_active=True
            ) | User.objects.filter(
                perfil__rol='admin',
                perfil__activo=True,
                is_active=True
            )
            self.fields['autorizado_por'].queryset = supervisores.distinct()
        else:
            # Todos los supervisores y admins
            self.fields['autorizado_por'].queryset = User.objects.filter(
                perfil__rol__in=['supervisor', 'admin'],
                perfil__activo=True,
                is_active=True
            )
        
        # Si no hay datos POST, mantener todos los ambientes activos disponibles
        if not data:
            self.fields['ambiente_destino'].queryset = Ambiente.objects.filter(activo=True)
        
        # Usuarios activos
        self.fields['usuario_nuevo'].queryset = User.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        
        # Validaciones según el tipo de movimiento
        if tipo == 'traslado':
            if not cleaned_data.get('ambiente_destino'):
                raise forms.ValidationError('Debe seleccionar una ubicación destino para el traslado.')
        
        if tipo == 'cambio_estado':
            if not cleaned_data.get('estado_item_nuevo'):
                raise forms.ValidationError('Debe seleccionar el nuevo estado del ítem.')
        
        if tipo == 'asignacion':
            if not cleaned_data.get('usuario_nuevo'):
                raise forms.ValidationError('Debe seleccionar el usuario al que se asigna el ítem.')
        
        # Validar que no se auto-autorice
        if cleaned_data.get('autorizado_por') == self.user:
            # Solo permitir si es admin
            if not (hasattr(self.user, 'perfil') and self.user.perfil.rol == 'admin'):
                raise forms.ValidationError('No puedes seleccionarte a ti mismo como autorizador.')
        
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
        area = self.cleaned_data.get('area') or (self.user.perfil.area if hasattr(self.user, 'perfil') else None)
        
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
        fields = ['pabellon', 'piso', 'tipo', 'nombre', 'capacidad', 'descripcion']
        widgets = {
            'pabellon': forms.Select(attrs={'class': 'form-select', 'id': 'id_pabellon'}),
            'piso': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '-1 para sótano'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Lab. Química, Aula 101'}),
            'capacidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
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
        fields = ['campus', 'nombre', 'codigo', 'activo']
        widgets = {
            'campus': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Sede Principal'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: SP', 'maxlength': 10}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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
        fields = ['sede', 'nombre', 'pisos', 'tiene_sotano', 'activo']
        widgets = {
            'sede': forms.Select(attrs={'class': 'form-select', 'id': 'id_sede'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: A, B, Principal'}),
            'pisos': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'tiene_sotano': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sede'].queryset = Sede.objects.none()
        
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
