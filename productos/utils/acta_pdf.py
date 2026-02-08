"""
Utilidades para generación de PDF de Actas de Entrega/Devolución
Sistema de Inventario UTP
"""

from io import BytesIO
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image as RLImage, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
import os
import base64


# Colores UTP
COLOR_UTP_RED = colors.HexColor('#C8102E')
COLOR_HEADER_BG = colors.HexColor('#f0f0f0')
COLOR_BORDER = colors.black


class ActaPDFGenerator:
    """Generador de PDF para Actas de Entrega/Devolución"""

    def __init__(self, acta):
        self.acta = acta
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configurar estilos personalizados"""
        # Título principal
        self.styles.add(ParagraphStyle(
            name='TituloPrincipal',
            parent=self.styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=COLOR_UTP_RED
        ))

        # Subtítulo de sección
        self.styles.add(ParagraphStyle(
            name='SeccionTitulo',
            parent=self.styles['Heading2'],
            fontSize=11,
            alignment=TA_CENTER,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.black,
            backColor=COLOR_HEADER_BG
        ))

        # Texto normal
        self.styles.add(ParagraphStyle(
            name='TextoNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=6
        ))

        # Texto pequeño
        self.styles.add(ParagraphStyle(
            name='TextoPequeno',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_LEFT
        ))

    def _get_logo_path(self):
        """Obtener ruta del logo UTP"""
        static_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo_utp.png')
        if os.path.exists(static_path):
            return static_path
        return None

    def _create_header(self):
        """Crear encabezado del documento"""
        elements = []

        # Tabla de encabezado con logo y texto
        logo_path = self._get_logo_path()

        header_data = [[
            RLImage(logo_path, width=100, height=40) if logo_path and os.path.exists(logo_path) else '',
            '',
            Paragraph('<b>JEFATURA DE<br/>SOPORTE TÉCNICO</b>',
                     ParagraphStyle(name='HeaderRight', fontSize=10, alignment=TA_RIGHT))
        ]]

        header_table = Table(header_data, colWidths=[150, 200, 150])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (-1, 0), (-1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 20))

        return elements

    def _create_title(self):
        """Crear título del acta"""
        tipo_texto = "ENTREGA" if self.acta.tipo == 'entrega' else "DEVOLUCIÓN"
        title = Paragraph(f"ACTA DE {tipo_texto}", self.styles['TituloPrincipal'])
        return [title, Spacer(1, 10)]

    def _create_intro_text(self):
        """Crear texto introductorio"""
        tipo_texto = "ENTREGA" if self.acta.tipo == 'entrega' else "DEVOLUCIÓN"
        texto = f"""Por medio del presente documento se hace la {tipo_texto} del equipo solicitado,
        que consta de las siguientes características técnicas:"""
        return [Paragraph(texto, self.styles['TextoNormal']), Spacer(1, 10)]

    def _create_user_data_section(self):
        """Crear sección de datos del usuario"""
        elements = []
        elements.append(Paragraph('DATOS DE USUARIO', self.styles['SeccionTitulo']))

        colaborador = self.acta.colaborador

        data = [
            ['Usuario', colaborador.nombre_completo],
            ['Cargo', colaborador.cargo],
            ['Gerencia', colaborador.gerencia.nombre],
            ['Sede', colaborador.sede.nombre],
            ['Anexo / RPE', colaborador.anexo or '-'],
            ['Correo', colaborador.correo],
        ]

        table = Table(data, colWidths=[120, 380])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), COLOR_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)

        return elements

    def _create_equipment_data_section(self):
        """Crear sección de datos del equipo"""
        elements = []
        elements.append(Spacer(1, 10))
        elements.append(Paragraph('DATOS DEL EQUIPO ASIGNADO', self.styles['SeccionTitulo']))

        data = [
            ['Fecha de Entrega', self.acta.fecha.strftime('%d/%m/%Y'),
             'Ticket', self.acta.ticket or '-'],
        ]

        table = Table(data, colWidths=[100, 150, 80, 170])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), COLOR_HEADER_BG),
            ('BACKGROUND', (2, 0), (2, 0), COLOR_HEADER_BG),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)

        return elements

    def _create_hardware_section(self):
        """Crear sección de detalle de equipos"""
        elements = []
        elements.append(Spacer(1, 10))
        elements.append(Paragraph('DETALLE DE EQUIPOS', self.styles['SeccionTitulo']))

        # Encabezado de tabla
        header = ['Tipo', 'Marca', 'Modelo', 'Código', 'Serie', 'Procesador', 'Memoria', 'Disco']
        data = [header]

        # Datos de cada item
        for acta_item in self.acta.items.all():
            item = acta_item.item
            specs = getattr(item, 'especificaciones_sistemas', None)

            row = [
                item.tipo_item.nombre if item.tipo_item else '-',
                specs.marca if specs else '-',
                specs.modelo if specs else '-',
                item.codigo_utp if not item.codigo_utp_pendiente else item.codigo_interno,
                item.serie,
                specs.procesador if specs else '-',
                specs.ram_display if specs else '-',
                specs.almacenamiento_display if specs else '-',
            ]
            data.append(row)

        table = Table(data, colWidths=[50, 55, 60, 70, 75, 70, 50, 50])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9d9d9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)

        return elements

    def _create_software_section(self):
        """Crear sección de software instalado"""
        elements = []

        software_list = self.acta.software.all()
        if not software_list:
            return elements

        elements.append(Spacer(1, 10))
        elements.append(Paragraph('SOFTWARE Y APLICACIONES INSTALADAS', self.styles['SeccionTitulo']))

        data = [['Descripción']]
        for sw in software_list:
            data.append([sw.software.nombre])

        table = Table(data, colWidths=[500])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_HEADER_BG),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)

        return elements

    def _create_accessories_section(self):
        """Crear sección de accesorios"""
        elements = []
        elements.append(Spacer(1, 10))
        elements.append(Paragraph('ACCESORIOS / SOFTWARE', self.styles['SeccionTitulo']))

        # Obtener accesorios del primer item (o combinar todos)
        acta_items = self.acta.items.all()
        acc = {
            'cargador': any(ai.acc_cargador for ai in acta_items),
            'seguridad': any(ai.acc_cable_seguridad for ai in acta_items),
            'bateria': any(ai.acc_bateria for ai in acta_items),
            'maletin': any(ai.acc_maletin for ai in acta_items),
            'red': any(ai.acc_cable_red for ai in acta_items),
            'perifericos': any(ai.acc_teclado_mouse for ai in acta_items),
        }

        check = '☑'
        uncheck = '☐'

        data = [
            [f"{check if acc['cargador'] else uncheck} Cargador / Cables",
             f"{check if acc['seguridad'] else uncheck} Cable de seguridad",
             f"{check if acc['bateria'] else uncheck} Batería"],
            [f"{check if acc['maletin'] else uncheck} Maletín",
             f"{check if acc['red'] else uncheck} Cable de red",
             f"{check if acc['perifericos'] else uncheck} Teclado y Mouse"],
        ]

        table = Table(data, colWidths=[166, 166, 166])
        table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)

        return elements

    def _create_page_two(self):
        """Crear segunda página con términos y firmas"""
        elements = []
        elements.append(PageBreak())

        tipo_texto = "ENTREGA" if self.acta.tipo == 'entrega' else "DEVOLUCIÓN"

        # Texto sobre estado del equipo
        elements.append(Paragraph(
            f"El equipo se hace la {tipo_texto} en perfecto estado y sin ningún daño físico.",
            self.styles['TextoNormal']
        ))
        elements.append(Spacer(1, 10))

        # Texto sobre incidencias
        elements.append(Paragraph(
            """Si el equipo sufre robo, pérdida, daño parcial o total, se debe generar un
            reporte de incidencia a través de la Mesa de Ayuda UTP para ser evaluado
            el evento por la Jefatura de Soporte.""",
            self.styles['TextoNormal']
        ))
        elements.append(Spacer(1, 15))

        # Recomendaciones
        elements.append(Paragraph('<b>1. Recomendaciones de Uso</b>', self.styles['TextoNormal']))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(
            """Al usuario que se le está asignando este equipo, tiene la responsabilidad
            de mantenerlo en buenas condiciones físicas; a continuación, se detallan
            algunas recomendaciones para la correcta utilización del equipo:""",
            self.styles['TextoNormal']
        ))

        recomendaciones = [
            "No ingerir alimentos y/o bebidas sobre el equipo de cómputo.",
            "Mantener limpio el equipo y con buena ventilación.",
            "Bloquear el equipo en periodos de inactividad.",
            "Apagar correctamente el equipo: Ir a INICIO → APAGAR. No apagar presionando el botón de encendido.",
            "Ante cualquier inconveniente comunicarse con la Mesa de Ayuda: Anexo: 1444, Correo: mesadeayuda@utp.edu.pe",
        ]

        for rec in recomendaciones:
            elements.append(Paragraph(f"• {rec}", self.styles['TextoPequeno']))

        elements.append(Spacer(1, 15))

        # Políticas
        elements.append(Paragraph('<b>2. Políticas y Normas de Uso</b>', self.styles['TextoNormal']))

        elements.append(Paragraph('<b>Acerca del Software</b>', self.styles['TextoPequeno']))
        politicas_sw = [
            "No instalar/desinstalar software sin autorización.",
            "No borrar ni modificar archivos compartidos.",
            "No alterar configuraciones del equipo.",
        ]
        for pol in politicas_sw:
            elements.append(Paragraph(f"• {pol}", self.styles['TextoPequeno']))

        elements.append(Paragraph('<b>Acerca del Hardware</b>', self.styles['TextoPequeno']))
        politicas_hw = [
            "No realizar cambios físicos al equipo.",
            "No usar el equipo para delitos informáticos.",
            "No usar el equipo con fines personales no autorizados.",
        ]
        for pol in politicas_hw:
            elements.append(Paragraph(f"• {pol}", self.styles['TextoPequeno']))

        elements.append(Spacer(1, 15))

        # Texto de conformidad
        elements.append(Paragraph(
            """Con la firma de este documento, el usuario certifica que el equipo se
            entrega en buenas condiciones y se encuentra conforme con el servicio
            brindado.""",
            self.styles['TextoNormal']
        ))
        elements.append(Spacer(1, 10))

        # Texto legal
        elements.append(Paragraph(
            """Asimismo, con la firma de la presente acta, autoriza de manera expresa a
            la UTP SAC a que en caso de incumplimiento de la "Política de Seguridad
            de Recursos Tecnológicos", pueda realizar el descuento respectivo por
            planilla en su remuneración mensual, referente a la reparación y/o
            costo de reposición del equipo respectivo, inclusive en caso que culminara
            el vínculo laboral sin haber cancelado la totalidad del costo de reparación o
            costo del equipo, autoriza a que el descuento se realice en su liquidación de
            beneficios sociales y/o cualquier monto pendiente de pago a favor del colaborador.""",
            self.styles['TextoPequeno']
        ))
        elements.append(Spacer(1, 15))

        # Fecha
        elements.append(Paragraph(
            f"<b>Fecha:</b> {self.acta.fecha.strftime('%d/%m/%Y')}",
            self.styles['TextoNormal']
        ))
        elements.append(Spacer(1, 30))

        # Firmas
        elements.extend(self._create_signatures_section())

        return elements

    def _create_signatures_section(self):
        """Crear sección de firmas"""
        elements = []

        # Intentar cargar las imágenes de firma
        firma_emisor_img = None
        firma_receptor_img = None

        if self.acta.firma_emisor:
            try:
                firma_emisor_img = RLImage(self.acta.firma_emisor.path, width=75, height=50)
            except:
                pass

        if self.acta.firma_receptor:
            try:
                firma_receptor_img = RLImage(self.acta.firma_receptor.path, width=100, height=50)
            except:
                pass

        # Nombre del emisor (quien genera el acta)
        emisor_nombre = self.acta.creado_por.get_full_name() or self.acta.creado_por.username
        emisor_cargo = "Auxiliar de TI"

        # Nombre del receptor
        receptor_nombre = self.acta.colaborador.nombre_completo
        receptor_cargo = self.acta.colaborador.cargo

        data = [
            [firma_emisor_img or '', firma_receptor_img or ''],
            ['_' * 35, '_' * 35],
            [Paragraph(f'<b>{emisor_nombre}</b>', self.styles['TextoPequeno']),
             Paragraph(f'<b>{receptor_nombre}</b>', self.styles['TextoPequeno'])],
            [emisor_cargo, receptor_cargo],
        ]

        table = Table(data, colWidths=[250, 250])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)

        return elements

    def generate(self):
        """Generar el PDF completo"""
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        elements = []

        # Página 1
        elements.extend(self._create_header())
        elements.extend(self._create_title())
        elements.extend(self._create_intro_text())
        elements.extend(self._create_user_data_section())
        elements.extend(self._create_equipment_data_section())
        elements.extend(self._create_hardware_section())
        elements.extend(self._create_software_section())
        elements.extend(self._create_accessories_section())

        # Página 2
        elements.extend(self._create_page_two())

        doc.build(elements)

        self.buffer.seek(0)
        return self.buffer

    def get_pdf_bytes(self):
        """Obtener bytes del PDF generado"""
        return self.generate().getvalue()


def generar_acta_pdf(acta):
    """
    Función auxiliar para generar PDF de un acta.

    Args:
        acta: Instancia del modelo ActaEntrega

    Returns:
        BytesIO: Buffer con el PDF generado
    """
    generator = ActaPDFGenerator(acta)
    return generator.generate()
