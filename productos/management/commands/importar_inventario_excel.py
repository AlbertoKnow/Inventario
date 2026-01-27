"""
Comando para importar inventario desde archivo Excel.
Uso: python manage.py importar_inventario_excel /path/to/file.xlsx
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from openpyxl import load_workbook
from productos.models import (
    Campus, Sede, Pabellon, Ambiente, Area, TipoItem, Item,
    MarcaEquipo, ModeloEquipo, ProcesadorEquipo, EspecificacionesSistemas
)
import re


class Command(BaseCommand):
    help = 'Importa inventario desde archivo Excel'

    def add_arguments(self, parser):
        parser.add_argument('archivo', type=str, help='Ruta al archivo Excel')
        parser.add_argument('--hoja', type=str, default='INVENTARIO GENERAL SEDE PARRA', help='Nombre de la hoja')

    def handle(self, *args, **options):
        archivo = options['archivo']
        hoja = options['hoja']

        self.stdout.write(f'Leyendo archivo: {archivo}')
        self.stdout.write(f'Hoja: {hoja}')
        self.stdout.write('')

        try:
            wb = load_workbook(archivo, read_only=True)
            ws = wb[hoja]
        except Exception as e:
            self.stderr.write(f'Error al abrir archivo: {e}')
            return

        # Obtener usuario admin para auditoría
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                admin_user = User.objects.first()
            self.stdout.write(f'Usuario para auditoría: {admin_user.username}')
        except:
            self.stderr.write('ERROR: No se encontró usuario para auditoría')
            return

        # Obtener área de Sistemas
        try:
            area_sistemas = Area.objects.get(codigo='sistemas')
        except Area.DoesNotExist:
            self.stderr.write('ERROR: No existe el área "sistemas"')
            return

        # Obtener sede Parra 1
        try:
            sede_parra = Sede.objects.get(nombre__icontains='Parra 1')
        except Sede.DoesNotExist:
            self.stderr.write('ERROR: No existe la sede "Parra 1"')
            return

        self.stdout.write(f'Área: {area_sistemas.nombre}')
        self.stdout.write(f'Sede: {sede_parra.nombre}')
        self.stdout.write('')

        # Mapeo de columnas (índice 0-based)
        COL = {
            'equipo': 0, 'tipo': 1, 'so': 2, 'marca': 3, 'modelo': 4,
            'inventario': 5, 'serie': 6, 'procesador': 9, 'generacion': 10,
            'ram': 11, 'hdd': 12, 'ssd': 13, 'usuario': 14, 'cod_ambiente': 19,
            'ambiente': 20, 'pabellon': 21, 'piso': 23, 'estado': 25,
        }

        # Mapeo de tipos
        TIPO_MAP = {
            'MONITOR': 'Monitor', 'DESKTOP': 'DESKTOP', 'MINI': 'MINI',
            'PROYECTOR': 'PROYECTOR', 'LAPTOP': 'LAPTOP', 'ALL IN ONE': 'ALL IN ONE',
            'MULTIFUNCIONAL': 'MULTIFUNCIONAL', 'MINIX': 'MINI', 'HUB': 'HUB',
            'TABLET': 'TABLET', 'HUELLERO': 'HUELLERO', 'TOUCH': 'TOUCH', 'OPSCAN': 'OPSCAN',
        }

        ESTADO_MAP = {
            'INSTALADO': 'instalado', 'BACKUP': 'backup',
            'DAÑADO': 'baja', 'DANADO': 'baja',
        }

        stats = {
            'pabellones': 0, 'ambientes': 0, 'tipos': 0,
            'marcas': 0, 'modelos': 0, 'procesadores': 0,
            'items': 0, 'omitidos': 0, 'errores': 0,
        }

        # Cache
        cache_pab = {p.letra: p for p in Pabellon.objects.filter(sede=sede_parra)}
        cache_amb = {}  # key: "pab_piso_numero"
        cache_tipos = {t.nombre.upper(): t for t in TipoItem.objects.filter(area=area_sistemas)}
        cache_marcas = {m.nombre.upper(): m for m in MarcaEquipo.objects.all()}
        cache_modelos = {}
        cache_procs = {p.nombre.upper(): p for p in ProcesadorEquipo.objects.all()}
        cache_series = set(Item.objects.values_list('serie', flat=True))
        cache_utps = set(Item.objects.values_list('codigo_utp', flat=True))

        # Pre-cargar ambientes existentes
        for amb in Ambiente.objects.filter(pabellon__sede=sede_parra):
            key = f'{amb.pabellon.letra}_{amb.piso}_{amb.numero}'
            cache_amb[key] = amb

        rows = list(ws.iter_rows(min_row=2, values_only=True))
        total = len(rows)
        self.stdout.write(f'Total filas: {total}')
        self.stdout.write('')

        with transaction.atomic():
            for idx, row in enumerate(rows, start=2):
                try:
                    # Extraer datos
                    equipo = str(row[COL['equipo']] or '').strip()
                    tipo_str = str(row[COL['tipo']] or '').strip().upper()
                    so = str(row[COL['so']] or '').strip()
                    marca_str = str(row[COL['marca']] or '').strip().upper()
                    modelo_str = str(row[COL['modelo']] or '').strip()
                    codigo_utp = str(row[COL['inventario']] or '').strip()
                    serie = str(row[COL['serie']] or '').strip()
                    procesador_str = str(row[COL['procesador']] or '').strip().upper()
                    generacion = str(row[COL['generacion']] or '').strip()
                    ram = str(row[COL['ram']] or '').strip()
                    hdd = str(row[COL['hdd']] or '').strip()
                    ssd = str(row[COL['ssd']] or '').strip()
                    nombre_ambiente = str(row[COL['ambiente']] or '').strip()
                    pabellon_str = str(row[COL['pabellon']] or '').strip().upper()
                    piso = str(row[COL['piso']] or '').strip()
                    estado_str = str(row[COL['estado']] or '').strip().upper()

                    # Validar código UTP
                    if not codigo_utp or codigo_utp == 'None':
                        stats['omitidos'] += 1
                        continue

                    # Truncar código UTP si es muy largo
                    if len(codigo_utp) > 20:
                        codigo_utp = codigo_utp[:20]

                    # Verificar duplicado
                    if codigo_utp in cache_utps:
                        stats['omitidos'] += 1
                        continue

                    # Limpiar pabellón
                    if not pabellon_str or pabellon_str.startswith('=') or pabellon_str == '-' or len(pabellon_str) > 1:
                        pabellon_str = 'X'

                    # Obtener/crear pabellón
                    if pabellon_str not in cache_pab:
                        pab = Pabellon.objects.create(
                            sede=sede_parra,
                            letra=pabellon_str,
                            nombre=f'Pabellón {pabellon_str}',
                            pisos=5,
                            activo=True
                        )
                        cache_pab[pabellon_str] = pab
                        stats['pabellones'] += 1

                    pabellon = cache_pab[pabellon_str]

                    # Determinar piso y número
                    try:
                        piso_num = int(piso) if piso and piso.isdigit() else 1
                    except:
                        piso_num = 1

                    ambiente_num = 1
                    match = re.search(r'(\d+)$', nombre_ambiente)
                    if match:
                        num_str = match.group(1)
                        ambiente_num = int(num_str[-2:]) if len(num_str) >= 2 else int(num_str)

                    # Obtener/crear ambiente
                    amb_key = f'{pabellon_str}_{piso_num}_{ambiente_num}'
                    if amb_key not in cache_amb:
                        amb = Ambiente.objects.create(
                            pabellon=pabellon,
                            piso=piso_num,
                            numero=ambiente_num,
                            tipo='lab_computo',
                            nombre=nombre_ambiente or f'Ambiente {piso_num}{ambiente_num:02d}',
                            activo=True
                        )
                        cache_amb[amb_key] = amb
                        stats['ambientes'] += 1

                    ambiente = cache_amb[amb_key]

                    # Obtener/crear tipo
                    tipo_nombre = TIPO_MAP.get(tipo_str, tipo_str) or 'OTROS'
                    if tipo_nombre.upper() not in cache_tipos:
                        tipo_obj = TipoItem.objects.create(
                            nombre=tipo_nombre,
                            area=area_sistemas,
                            descripcion=f'Tipo: {tipo_nombre}',
                            activo=True
                        )
                        cache_tipos[tipo_nombre.upper()] = tipo_obj
                        stats['tipos'] += 1

                    tipo_item = cache_tipos[tipo_nombre.upper()]

                    # Obtener/crear marca
                    marca = None
                    if marca_str and marca_str not in ['NO APLICA', '-', 'None']:
                        if marca_str not in cache_marcas:
                            marca = MarcaEquipo.objects.create(nombre=marca_str)
                            cache_marcas[marca_str] = marca
                            stats['marcas'] += 1
                        marca = cache_marcas[marca_str]

                    # Obtener/crear modelo
                    modelo = None
                    if modelo_str and modelo_str not in ['NO APLICA', '-', 'None'] and marca:
                        modelo_key = f'{marca_str}_{modelo_str}'
                        if modelo_key not in cache_modelos:
                            modelo = ModeloEquipo.objects.create(nombre=modelo_str, marca=marca)
                            cache_modelos[modelo_key] = modelo
                            stats['modelos'] += 1
                        modelo = cache_modelos[modelo_key]

                    # Obtener/crear procesador
                    procesador = None
                    if procesador_str and procesador_str not in ['NO APLICA', '-', 'None']:
                        if procesador_str not in cache_procs:
                            procesador = ProcesadorEquipo.objects.create(nombre=procesador_str)
                            cache_procs[procesador_str] = procesador
                            stats['procesadores'] += 1
                        procesador = cache_procs[procesador_str]

                    # Validar serie única
                    serie_final = serie if serie and serie != 'None' else f'SIN-SERIE-{codigo_utp}'
                    contador = 1
                    while serie_final in cache_series:
                        serie_final = f'{serie}-DUP{contador}'
                        contador += 1

                    # Estado
                    estado = ESTADO_MAP.get(estado_str, 'instalado')

                    # Crear item
                    item = Item(
                        codigo_utp=codigo_utp,
                        serie=serie_final,
                        nombre=equipo or tipo_nombre,
                        area=area_sistemas,
                        tipo_item=tipo_item,
                        ambiente=ambiente,
                        estado=estado,
                        creado_por=admin_user,
                        modificado_por=admin_user,
                    )
                    item.save()

                    # Registrar en cache
                    cache_utps.add(codigo_utp)
                    cache_series.add(serie_final)

                    # Crear especificaciones
                    if marca or modelo or procesador or (ram and ram != 'NO APLICA'):
                        ram_gb = None
                        if ram and ram != 'NO APLICA':
                            m = re.search(r'(\d+)', str(ram))
                            if m:
                                ram_gb = int(m.group(1))

                        hdd_val = ssd_val = ''
                        if hdd and hdd not in ['NO APLICA', '-']:
                            m = re.search(r'(\d+)', str(hdd))
                            if m:
                                hdd_val = f'{m.group(1)} GB'
                        if ssd and ssd not in ['NO APLICA', '-']:
                            m = re.search(r'(\d+)', str(ssd))
                            if m:
                                ssd_val = f'{m.group(1)} GB'

                        EspecificacionesSistemas.objects.create(
                            item=item,
                            marca_equipo=marca,
                            modelo_equipo=modelo,
                            procesador_equipo=procesador,
                            generacion_procesador=generacion if generacion != 'NO APLICA' else '',
                            ram_gb=ram_gb,
                            almacenamiento_principal=ssd_val or hdd_val or '',
                            almacenamiento_secundario=hdd_val if ssd_val else '',
                            sistema_operativo=so if so != 'NO APLICA' else '',
                        )

                    stats['items'] += 1

                    if idx % 100 == 0:
                        self.stdout.write(f'  {idx}/{total}...')

                except Exception as e:
                    self.stderr.write(f'  ERROR fila {idx}: {e}')
                    stats['errores'] += 1

        wb.close()

        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write('RESUMEN')
        self.stdout.write('=' * 50)
        for k, v in stats.items():
            self.stdout.write(f'{k}: {v}')
        self.stdout.write('=' * 50)
