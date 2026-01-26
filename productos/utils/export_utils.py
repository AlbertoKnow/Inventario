"""
Utilidades para exportación de datos a Excel y PDF
Sistema de Inventario UTP
"""

from datetime import datetime
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone

# Excel
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class ExcelExporter:
    """Clase para exportar datos a Excel con estilos personalizados"""

    # Colores UTP
    COLOR_HEADER = 'C8102E'  # Rojo UTP
    COLOR_HEADER_TEXT = 'FFFFFF'  # Blanco
    COLOR_SUBHEADER = 'F0F0F0'  # Gris claro
    COLOR_ROW_ALTERNATE = 'F9F9F9'  # Gris muy claro

    def __init__(self, title="Reporte"):
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = title[:31]  # Excel limita a 31 caracteres
        self.current_row = 1

    def add_title(self, title, subtitle=None):
        """Agrega título principal al reporte"""
        # Título
        self.ws.cell(row=self.current_row, column=1, value=title)
        title_cell = self.ws.cell(row=self.current_row, column=1)
        title_cell.font = Font(size=16, bold=True, color=self.COLOR_HEADER)
        self.current_row += 1

        # Subtítulo
        if subtitle:
            self.ws.cell(row=self.current_row, column=1, value=subtitle)
            subtitle_cell = self.ws.cell(row=self.current_row, column=1)
            subtitle_cell.font = Font(size=12, color='666666')
            self.current_row += 1

        # Fecha de generación
        fecha_generacion = f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
        self.ws.cell(row=self.current_row, column=1, value=fecha_generacion)
        fecha_cell = self.ws.cell(row=self.current_row, column=1)
        fecha_cell.font = Font(size=10, italic=True, color='999999')
        self.current_row += 2

    def add_headers(self, headers):
        """Agrega fila de encabezados con estilo"""
        for col_num, header in enumerate(headers, 1):
            cell = self.ws.cell(row=self.current_row, column=col_num, value=header)
            cell.font = Font(bold=True, color=self.COLOR_HEADER_TEXT)
            cell.fill = PatternFill(start_color=self.COLOR_HEADER, end_color=self.COLOR_HEADER, fill_type='solid')
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
        self.current_row += 1

    def add_row(self, values, alternate=False):
        """Agrega una fila de datos"""
        for col_num, value in enumerate(values, 1):
            cell = self.ws.cell(row=self.current_row, column=col_num, value=value)
            cell.alignment = Alignment(horizontal='left', vertical='center')
            cell.border = Border(
                left=Side(style='thin', color='CCCCCC'),
                right=Side(style='thin', color='CCCCCC'),
                top=Side(style='thin', color='CCCCCC'),
                bottom=Side(style='thin', color='CCCCCC')
            )
            if alternate:
                cell.fill = PatternFill(start_color=self.COLOR_ROW_ALTERNATE,
                                       end_color=self.COLOR_ROW_ALTERNATE,
                                       fill_type='solid')
        self.current_row += 1

    def add_summary(self, summary_data):
        """Agrega sección de resumen al final"""
        self.current_row += 1
        for label, value in summary_data.items():
            self.ws.cell(row=self.current_row, column=1, value=label)
            label_cell = self.ws.cell(row=self.current_row, column=1)
            label_cell.font = Font(bold=True)

            self.ws.cell(row=self.current_row, column=2, value=value)
            value_cell = self.ws.cell(row=self.current_row, column=2)
            value_cell.font = Font(color=self.COLOR_HEADER)

            self.current_row += 1

    def auto_adjust_columns(self):
        """Ajusta automáticamente el ancho de las columnas"""
        for column_cells in self.ws.columns:
            length = max(len(str(cell.value or '')) for cell in column_cells)
            self.ws.column_dimensions[get_column_letter(column_cells[0].column)].width = min(length + 2, 50)

    def get_response(self, filename="reporte.xlsx"):
        """Genera HttpResponse con el archivo Excel"""
        self.auto_adjust_columns()

        output = BytesIO()
        self.wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class PDFExporter:
    """Clase para exportar datos a PDF con estilos personalizados"""

    def __init__(self, title="Reporte", orientation="portrait"):
        self.title = title
        self.orientation = orientation
        self.elements = []
        self.styles = getSampleStyleSheet()

        # Crear estilos personalizados
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#C8102E'),
            spaceAfter=12,
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.grey,
            spaceAfter=6,
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))

    def add_title(self, title, subtitle=None):
        """Agrega título al PDF"""
        self.elements.append(Paragraph(title, self.styles['CustomTitle']))
        if subtitle:
            self.elements.append(Paragraph(subtitle, self.styles['CustomSubtitle']))

        # Fecha de generación
        fecha = timezone.now().strftime('%d/%m/%Y %H:%M')
        self.elements.append(Paragraph(f"Generado: {fecha}", self.styles['Footer']))
        self.elements.append(Spacer(1, 0.3*inch))

    def add_table(self, headers, data, column_widths=None):
        """Agrega una tabla al PDF"""
        # Preparar datos de la tabla
        table_data = [headers] + data

        # Crear tabla
        if column_widths:
            table = Table(table_data, colWidths=column_widths)
        else:
            table = Table(table_data)

        # Estilo de la tabla
        table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C8102E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Contenido
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),

            # Filas alternadas
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')])
        ]))

        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))

    def add_summary_section(self, summary_data):
        """Agrega sección de resumen"""
        self.elements.append(Spacer(1, 0.2*inch))
        self.elements.append(Paragraph("<b>RESUMEN</b>", self.styles['Heading2']))
        self.elements.append(Spacer(1, 0.1*inch))

        summary_table_data = [[k, str(v)] for k, v in summary_data.items()]
        summary_table = Table(summary_table_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        self.elements.append(summary_table)

    def add_page_break(self):
        """Agrega salto de página"""
        self.elements.append(PageBreak())

    def get_response(self, filename="reporte.pdf"):
        """Genera HttpResponse con el archivo PDF"""
        buffer = BytesIO()

        # Configurar página
        if self.orientation == "landscape":
            pagesize = landscape(A4)
        else:
            pagesize = A4

        # Crear documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=pagesize,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        # Generar PDF
        doc.build(self.elements)
        buffer.seek(0)

        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


# Funciones auxiliares para formateo
def format_currency(value):
    """Formatea valor como moneda"""
    if value is None:
        return "$0.00"
    return f"${value:,.2f}"


def format_date(date):
    """Formatea fecha"""
    if date is None:
        return "N/A"
    return date.strftime('%d/%m/%Y')


def format_boolean(value):
    """Formatea booleano"""
    return "Sí" if value else "No"


def generar_formato_traslado(items_data, origen_data, destino_data, fecha=None):
    """
    Genera el formato de traslado en Excel.

    Args:
        items_data: Lista de diccionarios con {codigo_utp, descripcion, marca, modelo}
        origen_data: Dict con {sede, piso, ubicacion, usuario}
        destino_data: Dict con {sede, piso, ubicacion, usuario}
        fecha: Fecha del traslado (opcional, usa hoy si no se especifica)

    Returns:
        BytesIO con el archivo Excel
    """
    from openpyxl.styles import Border, Side, Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Formato Traslado"

    # Configurar anchos de columna
    ws.column_dimensions['A'].width = 3
    ws.column_dimensions['B'].width = 3
    ws.column_dimensions['C'].width = 5
    ws.column_dimensions['D'].width = 3
    ws.column_dimensions['E'].width = 15
    for col in range(6, 12):
        ws.column_dimensions[get_column_letter(col)].width = 5
    ws.column_dimensions['L'].width = 20
    for col in range(13, 22):
        ws.column_dimensions[get_column_letter(col)].width = 4
    ws.column_dimensions['V'].width = 12
    for col in range(23, 29):
        ws.column_dimensions[get_column_letter(col)].width = 4
    ws.column_dimensions['AC'].width = 15
    for col in range(30, 50):
        ws.column_dimensions[get_column_letter(col)].width = 4

    # Estilos
    titulo_font = Font(size=14, bold=True)
    header_font = Font(size=10, bold=True)
    normal_font = Font(size=9)
    small_font = Font(size=8)

    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    header_fill = PatternFill(start_color='D9D9D9', end_color='D9D9D9', fill_type='solid')

    # === ENCABEZADO ===
    ws.merge_cells('A1:AO1')
    ws['A1'] = 'FORMATO DE CONTROL DE ACTIVOS'
    ws['A1'].font = titulo_font
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:AO2')
    ws['A2'] = 'USUARIO - PERSONA QUE SOLICITA'
    ws['A2'].alignment = Alignment(horizontal='center')

    # Fecha
    ws.merge_cells('C3:E3')
    ws['C3'] = 'FECHA :'
    ws['C3'].font = header_font
    ws.merge_cells('F3:K3')
    if fecha:
        ws['F3'] = fecha.strftime('%d/%m/%Y') if hasattr(fecha, 'strftime') else str(fecha)
    else:
        ws['F3'] = datetime.now().strftime('%d/%m/%Y')

    # Campos para llenar manualmente (columna derecha)
    ws.merge_cells('AI3:AO3')
    ws['AI3'] = 'Para ser completado por el responsable'
    ws['AI3'].font = small_font

    # Campos del encabezado izquierdo
    campos_izq = [
        (5, 'NÚMERO DE TRANSFERENCIA:'),
        (6, 'ADM. LOGÍSTICO DE LA SEDE :'),
        (7, 'RESPONSABLE DE TRASLADO:'),
        (8, 'SOLICITANTE DE TRASLADO:'),
        (9, 'ÁREA SOLICITANTE DE TRASLADO:'),
    ]

    for row, texto in campos_izq:
        ws.merge_cells(f'C{row}:M{row}')
        ws[f'C{row}'] = texto
        ws[f'C{row}'].font = header_font
        # Campo para llenar
        ws.merge_cells(f'N{row}:Z{row}')
        for col in range(14, 27):
            ws.cell(row=row, column=col).border = Border(bottom=Side(style='thin'))

    # Opciones de tipo (columna derecha)
    tipos = [
        (5, 'ALTA'),
        (6, 'BAJA'),
        (7, 'TRANSFERENCIA'),
        (8, 'OTROS MOTIVOS'),
    ]

    for row, texto in tipos:
        ws.merge_cells(f'AI{row}:AO{row}')
        ws[f'AI{row}'] = f'(    ) {texto}'
        ws[f'AI{row}'].font = normal_font

    # Breve explicación
    ws.merge_cells('C11:W11')
    ws['C11'] = 'BREVE EXPLICACIÓN (según sea el motivo):'
    ws['C11'].font = header_font

    # Definitivo / Retorno
    ws['X11'] = '( X ) DEFINITIVO'
    ws['X11'].font = normal_font
    ws.merge_cells('AG11:AL11')
    ws['AG11'] = '(    ) RETORNO'
    ws['AG11'].font = normal_font
    ws.merge_cells('AM11:AO11')
    ws['AM11'] = 'FECHA DE RETORNO:'
    ws['AM11'].font = small_font

    # Título de la sección
    ws.merge_cells('C12:Z12')
    ws['C12'] = 'TRASLADO DE ACTIVOS'
    ws['C12'].font = header_font

    # === TABLA DE ITEMS ===
    # Encabezados de la tabla
    ws.merge_cells('C16:D16')
    ws['C16'] = 'ITEM'
    ws['C16'].font = header_font
    ws['C16'].fill = header_fill
    ws['C16'].alignment = Alignment(horizontal='center')
    ws['C16'].border = thin_border
    ws['D16'].border = thin_border

    ws.merge_cells('E16:K16')
    ws['E16'] = 'CÓDIGO DE BARRA'
    ws['E16'].font = header_font
    ws['E16'].fill = header_fill
    ws['E16'].alignment = Alignment(horizontal='center')
    for col in range(5, 12):
        ws.cell(row=16, column=col).border = thin_border

    ws.merge_cells('L16:U16')
    ws['L16'] = 'DESCRIPCIÓN GENERAL'
    ws['L16'].font = header_font
    ws['L16'].fill = header_fill
    ws['L16'].alignment = Alignment(horizontal='center')
    for col in range(12, 22):
        ws.cell(row=16, column=col).border = thin_border

    ws.merge_cells('V16:AB16')
    ws['V16'] = 'MARCA'
    ws['V16'].font = header_font
    ws['V16'].fill = header_fill
    ws['V16'].alignment = Alignment(horizontal='center')
    for col in range(22, 29):
        ws.cell(row=16, column=col).border = thin_border

    ws.merge_cells('AC16:AO16')
    ws['AC16'] = 'MODELO'
    ws['AC16'].font = header_font
    ws['AC16'].fill = header_fill
    ws['AC16'].alignment = Alignment(horizontal='center')
    for col in range(29, 42):
        ws.cell(row=16, column=col).border = thin_border

    # Filas de items (hasta 20)
    for i in range(20):
        row = 17 + i
        item_num = i + 1

        # Número de item
        ws.merge_cells(f'C{row}:D{row}')
        ws[f'C{row}'] = item_num
        ws[f'C{row}'].alignment = Alignment(horizontal='center')
        ws[f'C{row}'].border = thin_border
        ws[f'D{row}'].border = thin_border

        # Datos del item si existe
        if i < len(items_data):
            item = items_data[i]

            ws.merge_cells(f'E{row}:K{row}')
            ws[f'E{row}'] = item.get('codigo_utp', '')
            ws[f'E{row}'].font = normal_font

            ws.merge_cells(f'L{row}:U{row}')
            ws[f'L{row}'] = item.get('descripcion', '')
            ws[f'L{row}'].font = normal_font

            ws.merge_cells(f'V{row}:AB{row}')
            ws[f'V{row}'] = item.get('marca', '')
            ws[f'V{row}'].font = normal_font

            ws.merge_cells(f'AC{row}:AO{row}')
            ws[f'AC{row}'] = item.get('modelo', '')
            ws[f'AC{row}'].font = normal_font
        else:
            ws.merge_cells(f'E{row}:K{row}')
            ws.merge_cells(f'L{row}:U{row}')
            ws.merge_cells(f'V{row}:AB{row}')
            ws.merge_cells(f'AC{row}:AO{row}')

        # Bordes para todas las celdas
        for col in range(5, 42):
            ws.cell(row=row, column=col).border = thin_border

    # === SECCIÓN ORIGEN Y DESTINO ===
    row_base = 40

    # Títulos
    ws.merge_cells(f'B{row_base}:L{row_base}')
    ws[f'B{row_base}'] = 'DATOS DE ORIGEN'
    ws[f'B{row_base}'].font = header_font
    ws[f'B{row_base}'].fill = header_fill

    ws.merge_cells(f'AB{row_base}:AO{row_base}')
    ws[f'AB{row_base}'] = 'DATOS DE DESTINO'
    ws[f'AB{row_base}'].font = header_font
    ws[f'AB{row_base}'].fill = header_fill

    # Campos de origen
    campos_origen = [
        (row_base + 2, 'SEDE DE ORIGEN:', origen_data.get('sede', '')),
        (row_base + 3, 'PISO DE ORIGEN:', origen_data.get('piso', '')),
        (row_base + 4, 'UBICACIÓN DE ORIGEN:', origen_data.get('ubicacion', '')),
        (row_base + 5, 'USUARIO DE ORIGEN:', origen_data.get('usuario', '')),
    ]

    for row, label, value in campos_origen:
        ws.merge_cells(f'D{row}:L{row}')
        ws[f'D{row}'] = label
        ws[f'D{row}'].font = header_font
        ws.merge_cells(f'M{row}:Z{row}')
        ws[f'M{row}'] = value
        ws[f'M{row}'].font = normal_font
        ws[f'M{row}'].border = Border(bottom=Side(style='thin'))

    # Campos de destino
    campos_destino = [
        (row_base + 2, 'SEDE DE DESTINO:', destino_data.get('sede', '')),
        (row_base + 3, 'PISO DE DESTINO:', destino_data.get('piso', '')),
        (row_base + 4, 'UBICACIÓN DE DESTINO:', destino_data.get('ubicacion', '')),
        (row_base + 5, 'USUARIO DE DESTINO:', destino_data.get('usuario', '')),
    ]

    for row, label, value in campos_destino:
        ws.merge_cells(f'AD{row}:AK{row}')
        ws[f'AD{row}'] = label
        ws[f'AD{row}'].font = header_font
        ws.merge_cells(f'AL{row}:AO{row}')
        ws[f'AL{row}'] = value
        ws[f'AL{row}'].font = normal_font
        ws[f'AL{row}'].border = Border(bottom=Side(style='thin'))

    # === SECCIÓN DE FIRMAS ===
    row_firmas = row_base + 7

    ws.merge_cells(f'B{row_firmas}:L{row_firmas}')
    ws[f'B{row_firmas}'] = 'ORIGEN'
    ws[f'B{row_firmas}'].font = header_font
    ws[f'B{row_firmas}'].alignment = Alignment(horizontal='center')

    ws.merge_cells(f'AG{row_firmas}:AO{row_firmas}')
    ws[f'AG{row_firmas}'] = 'DESTINO'
    ws[f'AG{row_firmas}'].font = header_font
    ws[f'AG{row_firmas}'].alignment = Alignment(horizontal='center')

    # Líneas de firma
    row_lineas = row_firmas + 5

    firmas = [
        ('C', 'I', 'USUARIO'),
        ('K', 'R', 'JEFE DE ÁREA'),
        ('S', 'Y', 'SEGURIDAD'),
        ('Z', 'AF', 'RESPONSABLE DEL TRASLADO'),
        ('AH', 'AO', 'USUARIO'),
    ]

    for col_start, col_end, texto in firmas:
        ws.merge_cells(f'{col_start}{row_lineas}:{col_end}{row_lineas}')
        ws[f'{col_start}{row_lineas}'] = texto
        ws[f'{col_start}{row_lineas}'].font = small_font
        ws[f'{col_start}{row_lineas}'].alignment = Alignment(horizontal='center')
        # Línea para firma arriba
        ws.merge_cells(f'{col_start}{row_lineas-1}:{col_end}{row_lineas-1}')
        ws[f'{col_start}{row_lineas-1}'].border = Border(bottom=Side(style='thin'))

    # Configurar área de impresión
    ws.print_area = 'A1:AO55'
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1

    # Guardar en BytesIO
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer
