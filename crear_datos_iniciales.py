# -*- coding: utf-8 -*-
"""
Script para crear datos iniciales del sistema de inventario.
Usa la estructura normalizada: Campus > Sede > Pabellon > Ambiente
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from productos.models import Area, TipoItem, Campus, Sede, Pabellon, Ambiente, PerfilUsuario, Item
from django.contrib.auth.models import User
from datetime import date, timedelta
from decimal import Decimal
import random


def crear_datos():
    print("=" * 50)
    print("CREANDO DATOS INICIALES")
    print("=" * 50)
    
    # ========== CREAR AREAS ==========
    areas_data = [
        ('sistemas', 'Sistemas', 'Area de tecnologia, equipos de computo y redes', '#3B82F6'),
        ('operaciones', 'Operaciones', 'Area de equipos de mantenimiento y mobiliario', '#10B981'),
        ('laboratorio', 'Laboratorio', 'Area de equipos cientificos y de investigacion', '#8B5CF6'),
    ]
    for codigo, nombre, desc, color in areas_data:
        Area.objects.get_or_create(codigo=codigo, defaults={
            'nombre': nombre, 
            'descripcion': desc,
            'color': color
        })
    print(f'Areas creadas: {Area.objects.count()}')

    # ========== CREAR TIPOS DE ITEMS ==========
    tipos_data = [
        ('Laptop', 'sistemas'),
        ('Desktop', 'sistemas'),
        ('Monitor', 'sistemas'),
        ('Impresora', 'sistemas'),
        ('Router', 'sistemas'),
        ('Switch de Red', 'sistemas'),
        ('Servidor', 'sistemas'),
        ('Proyector', 'sistemas'),
        ('Escritorio', 'operaciones'),
        ('Silla', 'operaciones'),
        ('Mesa', 'operaciones'),
        ('Pizarra', 'operaciones'),
        ('Estante', 'operaciones'),
        ('Armario', 'operaciones'),
        ('Ventilador', 'operaciones'),
        ('Aire Acondicionado', 'operaciones'),
        ('Microscopio', 'laboratorio'),
        ('Osciloscopio', 'laboratorio'),
        ('Multimetro', 'laboratorio'),
        ('Fuente de Poder', 'laboratorio'),
        ('Generador de Senales', 'laboratorio'),
        ('Protoboard', 'laboratorio'),
    ]
    for nombre, area_cod in tipos_data:
        area = Area.objects.get(codigo=area_cod)
        TipoItem.objects.get_or_create(nombre=nombre, defaults={'area': area})
    print(f'Tipos de item creados: {TipoItem.objects.count()}')

    # ========== CREAR CAMPUS ==========
    campus_ln, _ = Campus.objects.get_or_create(
        codigo='CLN',
        defaults={'nombre': 'Campus Lima Norte', 'direccion': 'Av. Alfredo Mendiola 6232'}
    )
    campus_ls, _ = Campus.objects.get_or_create(
        codigo='CLS',
        defaults={'nombre': 'Campus Lima Sur', 'direccion': 'Av. Pedro Miotta 530'}
    )
    print(f'Campus creados: {Campus.objects.count()}')

    # ========== CREAR SEDES ==========
    sede_principal_ln, _ = Sede.objects.get_or_create(
        campus=campus_ln, codigo='SP',
        defaults={'nombre': 'Sede Principal'}
    )
    sede_anexo_ln, _ = Sede.objects.get_or_create(
        campus=campus_ln, codigo='SA',
        defaults={'nombre': 'Sede Anexo'}
    )
    sede_principal_ls, _ = Sede.objects.get_or_create(
        campus=campus_ls, codigo='SP',
        defaults={'nombre': 'Sede Principal'}
    )
    print(f'Sedes creadas: {Sede.objects.count()}')

    # ========== CREAR PABELLONES ==========
    sedes = [sede_principal_ln, sede_anexo_ln, sede_principal_ls]
    for sede in sedes:
        for letra in ['A', 'B', 'C', 'D']:
            Pabellon.objects.get_or_create(
                sede=sede, nombre=letra,
                defaults={'pisos': 5}
            )
    print(f'Pabellones creados: {Pabellon.objects.count()}')

    # ========== CREAR AMBIENTES ==========
    pab_a_ln = Pabellon.objects.get(sede=sede_principal_ln, nombre='A')
    pab_b_ln = Pabellon.objects.get(sede=sede_principal_ln, nombre='B')
    pab_a_ls = Pabellon.objects.get(sede=sede_principal_ls, nombre='A')
    
    ambientes_data = [
        (pab_a_ln, 1, 'lab_computo', 'Laboratorio de Computo 101'),
        (pab_a_ln, 1, 'lab_computo', 'Laboratorio de Computo 102'),
        (pab_a_ln, 2, 'lab_especializado', 'Laboratorio de Electronica'),
        (pab_a_ln, 3, 'lab_especializado', 'Laboratorio de Redes'),
        (pab_b_ln, 1, 'aula_teorica', 'Aula Teorica 201'),
        (pab_b_ln, 2, 'aula_teorica', 'Aula Teorica 301'),
        (pab_b_ln, 3, 'administrativo', 'Oficina de Sistemas'),
        (pab_b_ln, 3, 'almacen', 'Almacen General'),
        (pab_a_ls, 1, 'lab_computo', 'Laboratorio de Computo'),
        (pab_a_ls, 2, 'aula_teorica', 'Aula Teorica'),
    ]
    for pabellon, piso, tipo, nombre in ambientes_data:
        Ambiente.objects.get_or_create(
            pabellon=pabellon, nombre=nombre,
            defaults={'piso': piso, 'tipo': tipo, 'capacidad': 30}
        )
    print(f'Ambientes creados: {Ambiente.objects.count()}')

    # ========== CREAR PERFIL ADMIN ==========
    try:
        admin_user = User.objects.get(username='admin')
        perfil, created = PerfilUsuario.objects.get_or_create(
            usuario=admin_user, 
            defaults={'rol': 'admin', 'activo': True}
        )
        if not created and perfil.rol != 'admin':
            perfil.rol = 'admin'
            perfil.save()
            print('Perfil admin actualizado a rol admin')
        else:
            print(f'Perfil admin {"creado" if created else "ya existia"}')
    except User.DoesNotExist:
        print('Usuario admin no existe - ejecuta: python manage.py createsuperuser')

    # ========== CREAR ITEMS DE PRUEBA ==========
    crear_items_prueba()

    print("=" * 50)
    print("DATOS INICIALES COMPLETADOS!")
    print("=" * 50)


def crear_items_prueba():
    """Crea items de prueba para el sistema."""
    print("\n" + "=" * 50)
    print("CREANDO ITEMS DE PRUEBA")
    print("=" * 50)
    
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        print("No existe usuario admin, no se crean items")
        return
    
    # Obtener areas y tipos
    area_sistemas = Area.objects.get(codigo='sistemas')
    area_operaciones = Area.objects.get(codigo='operaciones')
    area_lab = Area.objects.get(codigo='laboratorio')
    
    # Obtener algunos ambientes
    ambientes = list(Ambiente.objects.all()[:8])
    if not ambientes:
        print("No hay ambientes, no se pueden crear items")
        return
    
    # Definir items de prueba
    items_sistemas = [
        ('Laptop HP ProBook 450 G8', 'Laptop', 'ABC123456', Decimal('3500.00'), 'nuevo'),
        ('Laptop Dell Latitude 5520', 'Laptop', 'DEF789012', Decimal('4200.00'), 'bueno'),
        ('Laptop Lenovo ThinkPad E14', 'Laptop', 'GHI345678', Decimal('3800.00'), 'nuevo'),
        ('Desktop HP EliteDesk 800', 'Desktop', 'JKL901234', Decimal('2800.00'), 'bueno'),
        ('Desktop Dell OptiPlex 7090', 'Desktop', 'MNO567890', Decimal('3200.00'), 'nuevo'),
        ('Monitor LG 24" IPS', 'Monitor', 'PQR123456', Decimal('850.00'), 'bueno'),
        ('Monitor Samsung 27" Curvo', 'Monitor', 'STU789012', Decimal('1200.00'), 'nuevo'),
        ('Monitor Dell 24" UltraSharp', 'Monitor', 'VWX345678', Decimal('1100.00'), 'regular'),
        ('Impresora HP LaserJet Pro', 'Impresora', 'YZA901234', Decimal('1500.00'), 'bueno'),
        ('Impresora Epson EcoTank L3250', 'Impresora', 'BCD567890', Decimal('900.00'), 'nuevo'),
        ('Router Cisco RV340', 'Router', 'EFG123456', Decimal('2500.00'), 'bueno'),
        ('Switch TP-Link 24 puertos', 'Switch de Red', 'HIJ789012', Decimal('800.00'), 'nuevo'),
        ('Servidor Dell PowerEdge T40', 'Servidor', 'KLM345678', Decimal('15000.00'), 'nuevo'),
        ('Proyector Epson PowerLite', 'Proyector', 'NOP901234', Decimal('2200.00'), 'bueno'),
    ]
    
    items_operaciones = [
        ('Escritorio ejecutivo madera', 'Escritorio', 'OPE001001', Decimal('1200.00'), 'bueno'),
        ('Escritorio operativo metal', 'Escritorio', 'OPE001002', Decimal('600.00'), 'nuevo'),
        ('Silla ergonomica gerencial', 'Silla', 'OPE002001', Decimal('800.00'), 'nuevo'),
        ('Silla operativa giratoria', 'Silla', 'OPE002002', Decimal('350.00'), 'bueno'),
        ('Silla operativa giratoria', 'Silla', 'OPE002003', Decimal('350.00'), 'regular'),
        ('Mesa de reuniones 8 personas', 'Mesa', 'OPE003001', Decimal('1500.00'), 'bueno'),
        ('Estante metalico 5 niveles', 'Estante', 'OPE004001', Decimal('400.00'), 'nuevo'),
        ('Armario archivador 4 gavetas', 'Armario', 'OPE005001', Decimal('650.00'), 'bueno'),
    ]
    
    items_lab = [
        ('Microscopio binocular Olympus', 'Microscopio', 'LAB001001', Decimal('5500.00'), 'nuevo'),
        ('Microscopio trinocular Zeiss', 'Microscopio', 'LAB001002', Decimal('12000.00'), 'bueno'),
        ('Balanza analitica Mettler', 'Balanza de Precision', 'LAB002001', Decimal('8000.00'), 'nuevo'),
        ('Centrifuga Eppendorf 5424', 'Centrifuga', 'LAB003001', Decimal('15000.00'), 'bueno'),
        ('Osciloscopio Tektronix TBS1104', 'Osciloscopio', 'LAB004001', Decimal('4500.00'), 'nuevo'),
        ('Multimetro Fluke 117', 'Multimetro', 'LAB005001', Decimal('850.00'), 'bueno'),
    ]
    
    items_creados = 0
    
    # Crear items de sistemas
    for i, (nombre, tipo_nombre, serie, precio, estado) in enumerate(items_sistemas):
        tipo = TipoItem.objects.filter(nombre=tipo_nombre, area=area_sistemas).first()
        if not tipo:
            continue
        ambiente = ambientes[i % len(ambientes)]
        codigo = Item.generar_codigo_utp('sistemas')
        _, created = Item.objects.get_or_create(
            serie=serie,
            defaults={
                'codigo_utp': codigo,
                'nombre': nombre,
                'area': area_sistemas,
                'tipo_item': tipo,
                'ambiente': ambiente,
                'estado': estado,
                'fecha_adquisicion': date.today() - timedelta(days=random.randint(30, 365)),
                'precio': precio,
                'creado_por': admin_user,
            }
        )
        if created:
            items_creados += 1
    
    # Crear items de operaciones
    for i, (nombre, tipo_nombre, serie, precio, estado) in enumerate(items_operaciones):
        tipo = TipoItem.objects.filter(nombre=tipo_nombre, area=area_operaciones).first()
        if not tipo:
            continue
        ambiente = ambientes[(i + 3) % len(ambientes)]
        codigo = Item.generar_codigo_utp('operaciones')
        _, created = Item.objects.get_or_create(
            serie=serie,
            defaults={
                'codigo_utp': codigo,
                'nombre': nombre,
                'area': area_operaciones,
                'tipo_item': tipo,
                'ambiente': ambiente,
                'estado': estado,
                'fecha_adquisicion': date.today() - timedelta(days=random.randint(30, 365)),
                'precio': precio,
                'creado_por': admin_user,
            }
        )
        if created:
            items_creados += 1
    
    # Crear items de laboratorio
    for i, (nombre, tipo_nombre, serie, precio, estado) in enumerate(items_lab):
        tipo = TipoItem.objects.filter(nombre=tipo_nombre, area=area_lab).first()
        if not tipo:
            continue
        ambiente = ambientes[(i + 5) % len(ambientes)]
        codigo = Item.generar_codigo_utp('laboratorio')
        _, created = Item.objects.get_or_create(
            serie=serie,
            defaults={
                'codigo_utp': codigo,
                'nombre': nombre,
                'area': area_lab,
                'tipo_item': tipo,
                'ambiente': ambiente,
                'estado': estado,
                'fecha_adquisicion': date.today() - timedelta(days=random.randint(30, 365)),
                'precio': precio,
                'creado_por': admin_user,
            }
        )
        if created:
            items_creados += 1
    
    print(f'Items creados: {items_creados}')
    print(f'Total items en sistema: {Item.objects.count()}')


if __name__ == '__main__':
    crear_datos()
