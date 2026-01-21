"""
Pruebas automatizadas para el Sistema de Inventario UTP
========================================================
Ejecutar con: python manage.py test productos
"""

from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch
from django.contrib.auth.models import User

from .models import (
    Area, Campus, Sede, Pabellon, Ambiente, TipoItem, Item,
    Movimiento, PerfilUsuario, Mantenimiento
)


# ============================================================================
# PRUEBAS DE URLs
# ============================================================================

class URLConfigurationTests(TestCase):
    """Pruebas para verificar que las URLs están correctamente configuradas"""
    
    def test_home_url_resolves(self):
        """La URL de inicio debe resolver correctamente"""
        try:
            url = reverse('home')
            self.assertIsNotNone(url)
        except NoReverseMatch:
            self.fail("La URL 'home' no está configurada")
    
    def test_dashboard_url_resolves(self):
        """La URL del dashboard debe resolver correctamente"""
        try:
            url = reverse('productos:dashboard')
            self.assertEqual(url, '/productos/dashboard/')
        except NoReverseMatch:
            self.fail("La URL 'productos:dashboard' no está configurada")
    
    def test_item_list_url_resolves(self):
        """La URL de lista de items debe resolver"""
        try:
            url = reverse('productos:item-list')
            self.assertEqual(url, '/productos/')
        except NoReverseMatch:
            self.fail("La URL 'productos:item-list' no está configurada")


# ============================================================================
# PRUEBAS DE MODELOS
# ============================================================================

class AreaModelTests(TestCase):
    """Pruebas para el modelo Area"""
    
    def test_crear_area(self):
        """Se puede crear un área correctamente"""
        area = Area.objects.create(
            codigo='test',
            nombre='Area de Prueba',
            descripcion='Descripcion de prueba'
        )
        self.assertEqual(str(area), 'Area de Prueba')
        self.assertTrue(area.activo)


class CampusSedeModelTests(TestCase):
    """Pruebas para Campus, Sede, Pabellon, Ambiente"""
    
    @classmethod
    def setUpTestData(cls):
        cls.campus = Campus.objects.create(
            codigo='TEST',
            nombre='Campus Test',
            direccion='Direccion Test'
        )
        cls.sede = Sede.objects.create(
            campus=cls.campus,
            codigo='ST',
            nombre='Sede Test'
        )
        cls.pabellon = Pabellon.objects.create(
            sede=cls.sede,
            nombre='A',
            pisos=3
        )
        cls.ambiente = Ambiente.objects.create(
            pabellon=cls.pabellon,
            nombre='Aula 101',
            piso=1,
            tipo='aula_teorica'
        )
    
    def test_campus_str(self):
        """El campus muestra su nombre"""
        self.assertEqual(str(self.campus), 'Campus Test')
    
    def test_sede_str(self):
        """La sede muestra campus y nombre"""
        self.assertIn('Sede Test', str(self.sede))
    
    def test_ambiente_ubicacion_completa(self):
        """El ambiente muestra la ubicacion completa"""
        ub = self.ambiente.ubicacion_completa
        self.assertIn('Campus Test', ub)
        self.assertIn('Sede Test', ub)
        self.assertIn('A', ub)


class ItemModelTests(TestCase):
    """Pruebas para el modelo Item"""
    
    @classmethod
    def setUpTestData(cls):
        cls.area = Area.objects.create(
            codigo='sistemas',
            nombre='Sistemas'
        )
        cls.tipo_item = TipoItem.objects.create(
            nombre='Laptop',
            area=cls.area
        )
        cls.campus = Campus.objects.create(codigo='C1', nombre='Campus 1')
        cls.sede = Sede.objects.create(campus=cls.campus, codigo='S1', nombre='Sede 1')
        cls.pabellon = Pabellon.objects.create(sede=cls.sede, nombre='A', pisos=3)
        cls.ambiente = Ambiente.objects.create(
            pabellon=cls.pabellon, nombre='Lab 101', piso=1, tipo='lab_computo'
        )
    
    def test_crear_item(self):
        """Se puede crear un item correctamente"""
        from datetime import date
        from decimal import Decimal
        item = Item.objects.create(
            codigo_utp='SIS-2026-0001',
            area=self.area,
            tipo_item=self.tipo_item,
            nombre='Laptop HP',
            ambiente=self.ambiente,
            estado='nuevo',
            fecha_adquisicion=date.today(),
            precio=Decimal('2500.00')
        )
        self.assertEqual(item.estado, 'nuevo')
        self.assertIn('SIS-2026-0001', str(item))
    
    def test_generar_codigo_utp(self):
        """El metodo generar_codigo_utp genera codigos correctamente"""
        codigo = Item.generar_codigo_utp('sistemas')
        self.assertIsNotNone(codigo)
        self.assertTrue(codigo.startswith('SIS-'))
        # Debe tener formato: SIS-AÑO-XXXX
        partes = codigo.split('-')
        self.assertEqual(len(partes), 3)
        self.assertEqual(len(partes[2]), 4)  # 4 digitos


# ============================================================================
# PRUEBAS DE VISTAS
# ============================================================================

class ViewsAuthTests(TestCase):
    """Pruebas de autenticacion en vistas"""
    
    def test_dashboard_requiere_login(self):
        """El dashboard requiere autenticacion"""
        response = self.client.get(reverse('productos:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect a login
    
    def test_item_list_requiere_login(self):
        """La lista de items requiere autenticacion"""
        response = self.client.get(reverse('productos:item-list'))
        self.assertEqual(response.status_code, 302)


class ViewsWithAuthTests(TestCase):
    """Pruebas de vistas con usuario autenticado"""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        cls.area = Area.objects.create(codigo='test', nombre='Test')
        cls.perfil = PerfilUsuario.objects.create(
            usuario=cls.user,
            rol='admin',
            area=cls.area,
            activo=True
        )
    
    def setUp(self):
        self.client.login(username='testuser', password='testpass123')
    
    def test_dashboard_con_login(self):
        """El dashboard es accesible con login"""
        response = self.client.get(reverse('productos:dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_item_list_con_login(self):
        """La lista de items es accesible con login"""
        response = self.client.get(reverse('productos:item-list'))
        self.assertEqual(response.status_code, 200)
    
    def test_movimiento_list_con_login(self):
        """La lista de movimientos es accesible con login"""
        response = self.client.get(reverse('productos:movimiento-list'))
        self.assertEqual(response.status_code, 200)


# ============================================================================
# PRUEBAS DE MOVIMIENTOS
# ============================================================================

class MovimientoTests(TestCase):
    """Pruebas para el flujo de movimientos"""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('testuser', password='test123')
        cls.area = Area.objects.create(codigo='sistemas', nombre='Sistemas')
        cls.perfil = PerfilUsuario.objects.create(
            usuario=cls.user, rol='admin', area=cls.area, activo=True
        )
        cls.tipo = TipoItem.objects.create(nombre='Laptop', area=cls.area)
        cls.campus = Campus.objects.create(codigo='C1', nombre='Campus 1')
        cls.sede = Sede.objects.create(campus=cls.campus, codigo='S1', nombre='Sede 1')
        cls.pabellon = Pabellon.objects.create(sede=cls.sede, nombre='A', pisos=3)
        cls.ambiente = Ambiente.objects.create(
            pabellon=cls.pabellon, nombre='Lab', piso=1, tipo='lab_computo'
        )
        cls.ambiente2 = Ambiente.objects.create(
            pabellon=cls.pabellon, nombre='Oficina', piso=2, tipo='administrativo'
        )
        from datetime import date
        from decimal import Decimal
        cls.item = Item.objects.create(
            area=cls.area, tipo_item=cls.tipo, nombre='Laptop Test',
            ambiente=cls.ambiente, estado='nuevo',
            fecha_adquisicion=date.today(),
            precio=Decimal('2000.00')
        )
    
    def test_crear_movimiento_traslado(self):
        """Se puede crear un movimiento de traslado"""
        movimiento = Movimiento.objects.create(
            item=self.item,
            tipo='traslado',
            solicitado_por=self.user,
            ambiente_origen=self.ambiente,
            ambiente_destino=self.ambiente2,
            motivo='Cambio de ubicacion'
        )
        self.assertEqual(movimiento.estado, 'pendiente')
        self.assertEqual(movimiento.ambiente_origen, self.ambiente)
        self.assertEqual(movimiento.ambiente_destino, self.ambiente2)
    
    def test_aprobar_movimiento(self):
        """Se puede aprobar un movimiento"""
        movimiento = Movimiento.objects.create(
            item=self.item,
            tipo='traslado',
            solicitado_por=self.user,
            ambiente_destino=self.ambiente2,
            motivo='Test'
        )
        movimiento.aprobar(self.user)
        self.assertEqual(movimiento.estado, 'aprobado')
        self.assertIsNotNone(movimiento.fecha_aprobacion)


# ============================================================================
# PRUEBAS DE VALIDACIÓN DE ARCHIVOS
# ============================================================================

class ValidadorImagenTests(TestCase):
    """Pruebas para el validador de imágenes"""

    def test_extension_valida(self):
        """Extensiones válidas no lanzan error"""
        from .validators import ImageValidator
        from django.core.files.uploadedfile import SimpleUploadedFile
        from io import BytesIO
        from PIL import Image

        # Crear imagen de prueba
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        archivo = SimpleUploadedFile(
            name='test.jpg',
            content=img_bytes.read(),
            content_type='image/jpeg'
        )

        validator = ImageValidator()
        # No debe lanzar excepción
        try:
            validator(archivo)
        except Exception as e:
            self.fail(f"Validador lanzó excepción inesperada: {e}")

    def test_extension_invalida(self):
        """Extensiones inválidas lanzan ValidationError"""
        from .validators import ImageValidator
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.exceptions import ValidationError

        archivo = SimpleUploadedFile(
            name='test.exe',
            content=b'contenido malicioso',
            content_type='application/octet-stream'
        )

        validator = ImageValidator()
        with self.assertRaises(ValidationError):
            validator(archivo)

    def test_tamaño_excedido(self):
        """Archivos muy grandes lanzan ValidationError"""
        from .validators import ImageValidator
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.exceptions import ValidationError

        # Crear archivo que simula ser muy grande
        archivo = SimpleUploadedFile(
            name='test.jpg',
            content=b'x' * (6 * 1024 * 1024),  # 6MB
            content_type='image/jpeg'
        )

        validator = ImageValidator(max_size=5 * 1024 * 1024)
        with self.assertRaises(ValidationError):
            validator(archivo)


# ============================================================================
# PRUEBAS DE RATE LIMITING
# ============================================================================

class RateLimitTests(TestCase):
    """Pruebas para el sistema de rate limiting"""

    def test_get_client_ip_direct(self):
        """Obtiene IP directa correctamente"""
        from .ratelimit import get_client_ip
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')

    def test_get_client_ip_proxied(self):
        """Obtiene IP real detrás de proxy"""
        from .ratelimit import get_client_ip
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 192.168.1.1'
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        ip = get_client_ip(request)
        self.assertEqual(ip, '10.0.0.1')


# ============================================================================
# PRUEBAS DE PERMISOS
# ============================================================================

class PermisosTests(TestCase):
    """Pruebas para el sistema de permisos"""

    @classmethod
    def setUpTestData(cls):
        cls.area = Area.objects.create(codigo='test', nombre='Test')

        # Usuarios con diferentes roles
        cls.operador = User.objects.create_user('operador', password='test123')
        cls.supervisor = User.objects.create_user('supervisor', password='test123')
        cls.admin = User.objects.create_user('admin', password='test123')

        PerfilUsuario.objects.create(
            usuario=cls.operador, rol='operador', area=cls.area, activo=True
        )
        PerfilUsuario.objects.create(
            usuario=cls.supervisor, rol='supervisor', area=cls.area, activo=True
        )
        PerfilUsuario.objects.create(
            usuario=cls.admin, rol='admin', area=cls.area, activo=True
        )

    def test_operador_no_accede_crear_item(self):
        """Operadores no pueden acceder a crear items (solo supervisores+)"""
        self.client.login(username='operador', password='test123')
        response = self.client.get(reverse('productos:item-create'))
        # Debe redirigir (403 o redirect a login)
        self.assertIn(response.status_code, [302, 403])

    def test_supervisor_accede_crear_item(self):
        """Supervisores pueden acceder a crear items"""
        self.client.login(username='supervisor', password='test123')
        response = self.client.get(reverse('productos:item-create'))
        self.assertEqual(response.status_code, 200)

    def test_admin_accede_crear_item(self):
        """Admins pueden acceder a crear items"""
        self.client.login(username='admin', password='test123')
        response = self.client.get(reverse('productos:item-create'))
        self.assertEqual(response.status_code, 200)


# ============================================================================
# PRUEBAS DE MANTENIMIENTO
# ============================================================================

class MantenimientoTests(TestCase):
    """Pruebas para el sistema de mantenimiento"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('testuser', password='test123')
        cls.area = Area.objects.create(codigo='sistemas', nombre='Sistemas')
        cls.perfil = PerfilUsuario.objects.create(
            usuario=cls.user, rol='admin', area=cls.area, activo=True
        )
        cls.tipo = TipoItem.objects.create(nombre='Laptop', area=cls.area)
        cls.campus = Campus.objects.create(codigo='C1', nombre='Campus 1')
        cls.sede = Sede.objects.create(campus=cls.campus, codigo='S1', nombre='Sede 1')
        cls.pabellon = Pabellon.objects.create(sede=cls.sede, nombre='A', pisos=3)
        cls.ambiente = Ambiente.objects.create(
            pabellon=cls.pabellon, nombre='Lab', piso=1, tipo='lab_computo'
        )
        from datetime import date
        from decimal import Decimal
        cls.item = Item.objects.create(
            area=cls.area, tipo_item=cls.tipo, nombre='Laptop Test',
            ambiente=cls.ambiente, estado='nuevo',
            fecha_adquisicion=date.today(),
            precio=Decimal('2000.00')
        )

    def test_crear_mantenimiento_preventivo(self):
        """Se puede crear un mantenimiento preventivo"""
        from .models import Mantenimiento
        from datetime import date

        mantenimiento = Mantenimiento.objects.create(
            item=self.item,
            tipo='preventivo',
            descripcion='Limpieza general',
            fecha_programada=date.today(),
            solicitado_por=self.user
        )
        self.assertEqual(mantenimiento.estado, 'programado')
        self.assertEqual(mantenimiento.tipo, 'preventivo')

    def test_crear_mantenimiento_correctivo(self):
        """Se puede crear un mantenimiento correctivo"""
        from .models import Mantenimiento
        from datetime import date

        mantenimiento = Mantenimiento.objects.create(
            item=self.item,
            tipo='correctivo',
            descripcion='Reparación de pantalla',
            fecha_programada=date.today(),
            solicitado_por=self.user
        )
        self.assertEqual(mantenimiento.estado, 'programado')
        self.assertEqual(mantenimiento.tipo, 'correctivo')


# ============================================================================
# PRUEBAS DE API
# ============================================================================

class APITests(TestCase):
    """Pruebas para los endpoints de API"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('testuser', password='test123')
        cls.area = Area.objects.create(codigo='sistemas', nombre='Sistemas')
        cls.perfil = PerfilUsuario.objects.create(
            usuario=cls.user, rol='admin', area=cls.area, activo=True
        )
        cls.campus = Campus.objects.create(codigo='C1', nombre='Campus 1')
        cls.sede = Sede.objects.create(campus=cls.campus, codigo='S1', nombre='Sede 1')
        cls.pabellon = Pabellon.objects.create(sede=cls.sede, nombre='A', pisos=3)

    def setUp(self):
        self.client.login(username='testuser', password='test123')

    def test_api_sedes_por_campus(self):
        """El endpoint de sedes por campus retorna JSON"""
        response = self.client.get(
            reverse('productos:api-sedes'),
            {'campus_id': self.campus.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_api_pabellones_por_sede(self):
        """El endpoint de pabellones por sede retorna JSON"""
        response = self.client.get(
            reverse('productos:api-pabellones'),
            {'sede_id': self.sede.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_api_buscar_items(self):
        """El endpoint de búsqueda de items funciona"""
        response = self.client.get(
            reverse('productos:api-items-buscar'),
            {'q': 'laptop'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
