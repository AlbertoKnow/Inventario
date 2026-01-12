"""
Vistas para generación de reportes y exportación
Sistema de Inventario UTP
"""

from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, date

from ..models import Item, Area, TipoItem, Movimiento
from ..utils.export_utils import ExcelExporter, PDFExporter, format_currency, format_date, format_boolean


# ==============================================================================
# PÁGINA PRINCIPAL DE REPORTES
# ==============================================================================

class ReportesView(LoginRequiredMixin, TemplateView):
    """Vista principal para seleccionar y generar reportes"""
    template_name = 'productos/reportes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener perfil del usuario
        perfil = self.request.user.perfil

        # Filtrar items según área del usuario
        if perfil.area:
            items = Item.objects.filter(area=perfil.area)
        else:
            items = Item.objects.all()

        # Estadísticas básicas
        context['total_items'] = items.count()
        context['valor_total'] = items.aggregate(Sum('precio'))['precio__sum'] or 0
        context['items_operativos'] = items.filter(estado='operativo').count()
        context['items_mantenimiento'] = items.filter(estado='en_mantenimiento').count()

        # Áreas disponibles
        if perfil.area:
            context['areas'] = [perfil.area]
        else:
            context['areas'] = Area.objects.filter(activo=True)

        # Tipos de items
        context['tipos_item'] = TipoItem.objects.filter(activo=True)

        return context


# ==============================================================================
# EXPORTACIÓN A EXCEL
# ==============================================================================

class ExportarInventarioExcelView(LoginRequiredMixin, View):
    """Exporta el inventario completo a Excel"""

    def get(self, request, *args, **kwargs):
        # Obtener perfil del usuario
        perfil = request.user.perfil

        # Obtener parámetros de filtro
        area_id = request.GET.get('area')
        tipo_id = request.GET.get('tipo')
        estado = request.GET.get('estado')

        # Filtrar items
        if perfil.area:
            items = Item.objects.filter(area=perfil.area)
        else:
            items = Item.objects.all()

        # Aplicar filtros adicionales
        if area_id:
            items = items.filter(area_id=area_id)
        if tipo_id:
            items = items.filter(tipo_item_id=tipo_id)
        if estado:
            items = items.filter(estado=estado)

        # Crear exportador
        exporter = ExcelExporter(title="Inventario")

        # Título
        titulo = "INVENTARIO COMPLETO"
        subtitulo = f"Total de ítems: {items.count()}"
        if perfil.area:
            subtitulo += f" | Área: {perfil.area.nombre}"

        exporter.add_title(titulo, subtitulo)

        # Encabezados
        headers = [
            'Código Interno',
            'Código UTP',
            'Serie',
            'Nombre',
            'Área',
            'Tipo',
            'Estado',
            'Ubicación',
            'Usuario Asignado',
            'Precio',
            'Fecha Adquisición',
            'Garantía Hasta',
            'Leasing'
        ]
        exporter.add_headers(headers)

        # Datos
        for idx, item in enumerate(items.select_related('area', 'tipo_item', 'ambiente', 'usuario_asignado')):
            ubicacion = item.ambiente.codigo_completo if item.ambiente else 'Sin asignar'
            usuario = item.usuario_asignado.get_full_name() if item.usuario_asignado else 'Sin asignar'

            row = [
                item.codigo_interno,
                item.codigo_utp,
                item.serie,
                item.nombre,
                item.area.nombre,
                item.tipo_item.nombre,
                item.get_estado_display(),
                ubicacion,
                usuario,
                format_currency(item.precio),
                format_date(item.fecha_adquisicion),
                format_date(item.garantia_hasta),
                format_boolean(item.es_leasing)
            ]
            exporter.add_row(row, alternate=(idx % 2 == 0))

        # Resumen
        valor_total = items.aggregate(Sum('precio'))['precio__sum'] or 0
        summary = {
            'Total de ítems': items.count(),
            'Valor total': format_currency(valor_total),
            'Ítems operativos': items.filter(estado='operativo').count(),
            'Ítems en mantenimiento': items.filter(estado='en_mantenimiento').count(),
            'Ítems con código UTP pendiente': items.filter(codigo_utp='PENDIENTE').count(),
        }
        exporter.add_summary(summary)

        # Generar archivo
        fecha = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"inventario_{fecha}.xlsx"
        return exporter.get_response(filename)


class ExportarReportePorAreaExcelView(LoginRequiredMixin, View):
    """Exporta reporte de ítems agrupados por área"""

    def get(self, request, *args, **kwargs):
        perfil = request.user.perfil

        # Filtrar áreas
        if perfil.area:
            areas = Area.objects.filter(id=perfil.area.id, activo=True)
        else:
            areas = Area.objects.filter(activo=True)

        # Crear exportador
        exporter = ExcelExporter(title="Reporte por Área")
        exporter.add_title("REPORTE DE INVENTARIO POR ÁREA", "Distribución de ítems y valores")

        # Encabezados
        headers = ['Área', 'Cantidad de Ítems', 'Valor Total', '% del Total', 'Operativos', 'En Mantenimiento', 'Dañados']
        exporter.add_headers(headers)

        # Calcular totales
        total_items = Item.objects.count()
        total_valor = Item.objects.aggregate(Sum('precio'))['precio__sum'] or 0

        # Datos por área
        for idx, area in enumerate(areas):
            items_area = Item.objects.filter(area=area)
            cantidad = items_area.count()
            valor = items_area.aggregate(Sum('precio'))['precio__sum'] or 0
            porcentaje = (valor / total_valor * 100) if total_valor > 0 else 0

            operativos = items_area.filter(estado='operativo').count()
            mantenimiento = items_area.filter(estado='en_mantenimiento').count()
            danados = items_area.filter(estado='danado').count()

            row = [
                area.nombre,
                cantidad,
                format_currency(valor),
                f"{porcentaje:.2f}%",
                operativos,
                mantenimiento,
                danados
            ]
            exporter.add_row(row, alternate=(idx % 2 == 0))

        # Resumen
        summary = {
            'Total general de ítems': total_items,
            'Valor total general': format_currency(total_valor),
        }
        exporter.add_summary(summary)

        fecha = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reporte_por_area_{fecha}.xlsx"
        return exporter.get_response(filename)


class ExportarGarantiasVencenExcelView(LoginRequiredMixin, View):
    """Exporta reporte de garantías próximas a vencer"""

    def get(self, request, *args, **kwargs):
        perfil = request.user.perfil
        dias = int(request.GET.get('dias', 30))  # Por defecto 30 días

        # Filtrar items con garantía próxima a vencer
        hoy = date.today()
        fecha_limite = hoy + timedelta(days=dias)

        if perfil.area:
            items = Item.objects.filter(
                area=perfil.area,
                garantia_hasta__gte=hoy,
                garantia_hasta__lte=fecha_limite
            )
        else:
            items = Item.objects.filter(
                garantia_hasta__gte=hoy,
                garantia_hasta__lte=fecha_limite
            )

        # Crear exportador
        exporter = ExcelExporter(title="Garantías")
        exporter.add_title(
            f"GARANTÍAS QUE VENCEN EN {dias} DÍAS",
            f"Del {hoy.strftime('%d/%m/%Y')} al {fecha_limite.strftime('%d/%m/%Y')}"
        )

        # Encabezados
        headers = [
            'Código Interno',
            'Serie',
            'Nombre',
            'Área',
            'Fecha Adquisición',
            'Garantía Hasta',
            'Días Restantes',
            'Precio',
            'Proveedor/Lote'
        ]
        exporter.add_headers(headers)

        # Datos
        for idx, item in enumerate(items.select_related('area', 'lote')):
            dias_restantes = (item.garantia_hasta - hoy).days
            proveedor = item.lote.contrato.proveedor.nombre if (item.lote and item.lote.contrato) else 'N/A'

            row = [
                item.codigo_interno,
                item.serie,
                item.nombre,
                item.area.nombre,
                format_date(item.fecha_adquisicion),
                format_date(item.garantia_hasta),
                f"{dias_restantes} días",
                format_currency(item.precio),
                proveedor
            ]
            exporter.add_row(row, alternate=(idx % 2 == 0))

        # Resumen
        valor_total = items.aggregate(Sum('precio'))['precio__sum'] or 0
        summary = {
            'Total de ítems': items.count(),
            'Valor total en riesgo': format_currency(valor_total),
        }
        exporter.add_summary(summary)

        fecha = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"garantias_vencen_{dias}dias_{fecha}.xlsx"
        return exporter.get_response(filename)


# ==============================================================================
# EXPORTACIÓN A PDF
# ==============================================================================

class ExportarInventarioPDFView(LoginRequiredMixin, View):
    """Exporta el inventario completo a PDF"""

    def get(self, request, *args, **kwargs):
        # Obtener perfil del usuario
        perfil = request.user.perfil

        # Obtener parámetros de filtro
        area_id = request.GET.get('area')
        tipo_id = request.GET.get('tipo')
        estado = request.GET.get('estado')

        # Filtrar items
        if perfil.area:
            items = Item.objects.filter(area=perfil.area)
        else:
            items = Item.objects.all()

        # Aplicar filtros adicionales
        if area_id:
            items = items.filter(area_id=area_id)
        if tipo_id:
            items = items.filter(tipo_item_id=tipo_id)
        if estado:
            items = items.filter(estado=estado)

        # Crear exportador PDF
        exporter = PDFExporter(title="Inventario", orientation="landscape")

        # Título
        titulo = "INVENTARIO COMPLETO"
        subtitulo = f"Total de ítems: {items.count()}"
        if perfil.area:
            subtitulo += f" | Área: {perfil.area.nombre}"

        exporter.add_title(titulo, subtitulo)

        # Encabezados y datos
        headers = ['Código', 'Serie', 'Nombre', 'Área', 'Tipo', 'Estado', 'Precio']
        data = []

        for item in items.select_related('area', 'tipo_item')[:100]:  # Limitar a 100 para PDF
            data.append([
                item.codigo_interno,
                item.serie[:15],
                item.nombre[:25],
                item.area.codigo,
                item.tipo_item.nombre[:15],
                item.get_estado_display()[:10],
                format_currency(item.precio)
            ])

        exporter.add_table(headers, data)

        # Resumen
        valor_total = items.aggregate(Sum('precio'))['precio__sum'] or 0
        summary = {
            'Total de ítems': items.count(),
            'Valor total': format_currency(valor_total),
            'Ítems operativos': items.filter(estado='operativo').count(),
            'Ítems en mantenimiento': items.filter(estado='en_mantenimiento').count(),
        }
        exporter.add_summary_section(summary)

        # Generar archivo
        fecha = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"inventario_{fecha}.pdf"
        return exporter.get_response(filename)


class ExportarReportePorAreaPDFView(LoginRequiredMixin, View):
    """Exporta reporte de ítems agrupados por área a PDF"""

    def get(self, request, *args, **kwargs):
        perfil = request.user.perfil

        # Filtrar áreas
        if perfil.area:
            areas = Area.objects.filter(id=perfil.area.id, activo=True)
        else:
            areas = Area.objects.filter(activo=True)

        # Crear exportador PDF
        exporter = PDFExporter(title="Reporte por Área")
        exporter.add_title("REPORTE DE INVENTARIO POR ÁREA", "Distribución de ítems y valores")

        # Calcular totales
        total_items = Item.objects.count()
        total_valor = Item.objects.aggregate(Sum('precio'))['precio__sum'] or 0

        # Encabezados y datos
        headers = ['Área', 'Cantidad', 'Valor Total', '% Total', 'Operativos', 'Mant.', 'Dañados']
        data = []

        for area in areas:
            items_area = Item.objects.filter(area=area)
            cantidad = items_area.count()
            valor = items_area.aggregate(Sum('precio'))['precio__sum'] or 0
            porcentaje = (valor / total_valor * 100) if total_valor > 0 else 0

            data.append([
                area.nombre[:20],
                str(cantidad),
                format_currency(valor),
                f"{porcentaje:.1f}%",
                str(items_area.filter(estado='operativo').count()),
                str(items_area.filter(estado='en_mantenimiento').count()),
                str(items_area.filter(estado='danado').count())
            ])

        exporter.add_table(headers, data)

        # Resumen
        summary = {
            'Total general de ítems': total_items,
            'Valor total general': format_currency(total_valor),
        }
        exporter.add_summary_section(summary)

        fecha = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reporte_por_area_{fecha}.pdf"
        return exporter.get_response(filename)
