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
    Movimiento, PerfilUsuario
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
        self.assertIsNotNone(movimiento.fecha_respuesta)
