"""
Utilidades para envío de correos de Actas de Entrega/Devolución
Sistema de Inventario UTP - Usando Resend
"""

import base64
import resend
from django.conf import settings
from django.utils import timezone


# Lista de correos en copia (CC)
COPIA_CORREO = [
    "bcjuno@utp.edu.pe",
    "dhuanaco@utp.edu.pe",
    "aurquizop@utp.edu.pe",
    "lchiarellam@utp.edu.pe",
    "aancco@utp.edu.pe",
    "lhuamanic@utp.edu.pe",
    "rbegazo@utp.edu.pe",
    "ataco@utp.edu.pe",
]


def enviar_acta_por_correo(acta, pdf_bytes, fotos_paths=None):
    """
    Envía el acta por correo electrónico al colaborador usando Resend.

    Args:
        acta: Instancia del modelo ActaEntrega
        pdf_bytes: Bytes del PDF generado
        fotos_paths: Lista opcional de rutas de fotos a adjuntar

    Returns:
        bool: True si el envío fue exitoso
    """
    # Configurar API key de Resend
    resend.api_key = settings.RESEND_API_KEY

    colaborador = acta.colaborador

    # Determinar tipo de acta
    if acta.tipo == 'devolucion':
        titulo = "Acta de Devolución de Equipo"
        intro = "Se adjunta el acta de devolución del equipo asignado."
        texto_seguridad = (
            "Cadena de seguridad -- debe devolverse con la clave "
            "<strong>0000</strong>, caso contrario se aplicará la penalidad correspondiente."
        )
    else:
        titulo = "Acta de Entrega de Equipo"
        intro = "Se adjunta el acta de entrega del equipo asignado."
        texto_seguridad = "Cadena de seguridad -- se entrega con la clave <strong>0000</strong>."

    nombre_pdf = f"ACTA_{acta.tipo.upper()}_{acta.numero_acta}.pdf"

    # Construir HTML de equipos
    equipos_html = ""
    for idx, acta_item in enumerate(acta.items.all(), start=1):
        item = acta_item.item
        specs = getattr(item, 'especificaciones_sistemas', None)

        equipos_html += f"""
        <h4 style="margin-bottom:5px;">Activo {idx}</h4>
        <ul>
            <li><b>Tipo:</b> {item.tipo_item.nombre if item.tipo_item else '-'}</li>
            <li><b>Marca:</b> {specs.marca if specs else '-'}</li>
            <li><b>Modelo:</b> {specs.modelo if specs else '-'}</li>
            <li><b>Código:</b> {item.codigo_utp if not item.codigo_utp_pendiente else item.codigo_interno}</li>
            <li><b>Serie:</b> {item.serie}</li>
            <li><b>Procesador:</b> {specs.procesador if specs else '-'}</li>
            <li><b>Memoria RAM:</b> {specs.ram_display if specs else '-'}</li>
            <li><b>Disco:</b> {specs.almacenamiento_display if specs else '-'}</li>
        </ul>
        """

    # Construir HTML de accesorios
    accesorios_items = ""
    acta_items = acta.items.all()

    if any(ai.acc_cargador for ai in acta_items):
        accesorios_items += "<li>Cargador / Cables</li>"

    if any(ai.acc_bateria for ai in acta_items):
        accesorios_items += "<li>Batería</li>"

    if any(ai.acc_maletin for ai in acta_items):
        accesorios_items += "<li>Maletín</li>"

    if any(ai.acc_cable_red for ai in acta_items):
        accesorios_items += "<li>Cable de red</li>"

    if any(ai.acc_teclado_mouse for ai in acta_items):
        accesorios_items += "<li>Teclado y Mouse</li>"

    if any(ai.acc_cable_seguridad for ai in acta_items):
        accesorios_items += f"<li>{texto_seguridad}</li>"

    bloque_accesorios = ""
    if accesorios_items:
        bloque_accesorios = f"""
        <p><strong>Accesorios incluidos:</strong></p>
        <ul>
            {accesorios_items}
        </ul>
        """

    # Cuerpo del correo en HTML
    cuerpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
        <p>Estimado(a) <strong>{colaborador.nombre_completo}</strong>,</p>

        <p>{intro}</p>

        <p><strong>Recomendaciones:</strong></p>
        <ul>
            <li>Mantener el equipo en buen estado evitando golpes y rayaduras.</li>
            <li>No personalizarlo con pegatinas o adhesivos.</li>
        </ul>

        <p>Ante cualquier inconveniente, comunicarse con
        <strong>Mesa de Ayuda TI</strong> al correo
        <a href="mailto:mesadeayuda@utp.edu.pe">mesadeayuda@utp.edu.pe</a>.
        </p>

        <p><strong>Datos del equipo:</strong></p>

        {equipos_html}

        {bloque_accesorios}

        <p style="margin-top:20px;">
            Saludos cordiales,<br>
            <b>Oficina de Soporte UTP Arequipa</b>
        </p>
    </body>
    </html>
    """

    try:
        # Preparar adjuntos
        attachments = [
            {
                "filename": nombre_pdf,
                "content": base64.b64encode(pdf_bytes).decode('utf-8')
            }
        ]

        # Adjuntar fotos si las hay
        if fotos_paths:
            import os
            for foto_path in fotos_paths:
                try:
                    if os.path.exists(foto_path):
                        with open(foto_path, 'rb') as f:
                            foto_content = f.read()
                            filename = os.path.basename(foto_path)
                            attachments.append({
                                "filename": filename,
                                "content": base64.b64encode(foto_content).decode('utf-8')
                            })
                except Exception as e:
                    print(f"Error adjuntando foto {foto_path}: {e}")

        # Enviar con Resend
        params = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [colaborador.correo],
            "cc": COPIA_CORREO,
            "subject": titulo,
            "html": cuerpo_html,
            "attachments": attachments
        }

        response = resend.Emails.send(params)

        # Marcar el acta como enviada
        acta.correo_enviado = True
        acta.fecha_envio_correo = timezone.now()
        acta.save(update_fields=['correo_enviado', 'fecha_envio_correo'])

        return True

    except Exception as e:
        print(f"Error enviando correo con Resend: {e}")
        return False


def get_cc_emails():
    """Retorna la lista de correos en copia"""
    return COPIA_CORREO.copy()
