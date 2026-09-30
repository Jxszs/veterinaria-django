"""
Documentos descargables (JO3): carnet de vacunación en PDF con ReportLab.
"""
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

VERDE = colors.HexColor('#198754')
GRIS = colors.HexColor('#6c757d')


def _fecha(valor):
    return valor.strftime('%d/%m/%Y') if valor else '—'


def carnet_vacunas_pdf(mascota):
    """Devuelve los bytes de un PDF con los datos de la mascota y sus vacunas."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f'Carnet de vacunación - {mascota.nombre}',
    )
    estilos = getSampleStyleSheet()
    elementos = [
        Paragraph('Clínica Veterinaria', estilos['Title']),
        Paragraph('Carnet de vacunación', estilos['Heading2']),
        Spacer(1, 0.3 * cm),
    ]

    dueno = mascota.dueno
    datos = [
        ['Mascota', mascota.nombre, 'Especie', mascota.especie],
        ['Raza', mascota.raza or '—', 'Edad', f'{mascota.edad} año(s)'],
        ['Dueño', dueno.nombre if dueno else 'Sin dueño asignado',
         'Contacto', (dueno.telefono or dueno.whatsapp or dueno.email or '—') if dueno else '—'],
    ]
    tabla_datos = Table(datos, colWidths=[2.5 * cm, 6 * cm, 2.5 * cm, 6 * cm])
    tabla_datos.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), GRIS),
        ('TEXTCOLOR', (2, 0), (2, -1), GRIS),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos += [tabla_datos, Spacer(1, 0.5 * cm)]

    if mascota.alergico:
        elementos.append(Paragraph(
            '<b>Atención:</b> mascota alérgica a las vacunas. No vacunar sin evaluación veterinaria.',
            estilos['Normal'],
        ))
        elementos.append(Spacer(1, 0.3 * cm))

    vacunas = list(mascota.vacunas.order_by('fecha_aplicacion'))
    if vacunas:
        filas = [['Vacuna', 'Aplicada', 'Lote', 'Fabricante', 'Próxima dosis']]
        for vacuna in vacunas:
            filas.append([
                vacuna.get_tipo_display(), _fecha(vacuna.fecha_aplicacion),
                vacuna.lote or '—', vacuna.fabricante or '—', _fecha(vacuna.proxima_dosis),
            ])
        tabla = Table(filas, repeatRows=1, colWidths=[4 * cm, 2.6 * cm, 3 * cm, 4 * cm, 3.4 * cm])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VERDE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f7fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabla)
    else:
        elementos.append(Paragraph('La mascota no tiene vacunas registradas.', estilos['Normal']))

    elementos += [
        Spacer(1, 1 * cm),
        Paragraph(
            f'Documento generado el {timezone.localtime():%d/%m/%Y a las %H:%M}.',
            estilos['Italic'],
        ),
    ]
    doc.build(elementos)
    return buffer.getvalue()
