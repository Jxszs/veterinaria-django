"""
Alertas de vacunación (JO3).

Este módulo lo usan tanto la página de alertas como el comando
`python manage.py enviar_alertas_vacunas`, para que ambos calculen
exactamente lo mismo.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Exists, OuterRef
from django.utils import timezone

from .models import DIAS_AVISO_VACUNA, Mascota, Vacuna

logger = logging.getLogger(__name__)


def vacunas_con_refuerzo_pendiente(dias=DIAS_AVISO_VACUNA, queryset=None):
    """
    Vacunas cuya próxima dosis ya venció o vence dentro de `dias` días.

    Solo cuenta la dosis MÁS RECIENTE de cada tipo por mascota: si a la
    mascota ya se le puso el refuerzo, la dosis anterior no genera alerta.
    Las mascotas alérgicas a las vacunas se excluyen.
    """
    queryset = queryset if queryset is not None else Vacuna.objects.all()
    limite = timezone.localdate() + timedelta(days=dias)
    dosis_posterior = Vacuna.objects.filter(
        mascota=OuterRef('mascota'),
        tipo=OuterRef('tipo'),
        fecha_aplicacion__gt=OuterRef('fecha_aplicacion'),
    )
    return (
        queryset.filter(proxima_dosis__isnull=False, proxima_dosis__lte=limite)
        .exclude(mascota__alergico=True)
        .exclude(Exists(dosis_posterior))
        .select_related('mascota', 'mascota__dueno')
        .order_by('proxima_dosis')
    )


def mascotas_sin_vacunas(queryset=None):
    """Mascotas marcadas como pendientes que no tienen ninguna vacuna registrada."""
    queryset = queryset if queryset is not None else Mascota.objects.all()
    return (
        queryset.filter(vacunado=False, alergico=False, vacunas__isnull=True)
        .select_related('dueno')
        .order_by('nombre')
    )


def _texto_correo(vacuna):
    dueno = vacuna.mascota.dueno
    if vacuna.estado_dosis == 'vencida':
        cuando = f'venció el {vacuna.proxima_dosis:%d/%m/%Y}'
    else:
        cuando = f'corresponde el {vacuna.proxima_dosis:%d/%m/%Y}'
    return (
        f'Hola {dueno.nombre}:\n\n'
        f'Te recordamos que la próxima dosis de la vacuna {vacuna.get_tipo_display()} '
        f'de {vacuna.mascota.nombre} {cuando}.\n\n'
        'Puedes agendar una hora respondiendo este correo o llamando a la clínica.\n\n'
        'Saludos,\nClínica Veterinaria'
    )


def enviar_recordatorios(dias=DIAS_AVISO_VACUNA, simular=False):
    """
    Envía un correo por cada vacuna pendiente cuyo dueño tenga correo y a la
    que todavía no se le haya enviado aviso. Marca `alerta_enviada_el` para no
    repetir el correo al día siguiente.

    Devuelve un resumen: {'enviados': n, 'sin_correo': n, 'ya_avisados': n, 'errores': n}
    """
    resumen = {'enviados': 0, 'sin_correo': 0, 'ya_avisados': 0, 'errores': 0}
    for vacuna in vacunas_con_refuerzo_pendiente(dias):
        dueno = vacuna.mascota.dueno
        if vacuna.alerta_enviada_el:
            resumen['ya_avisados'] += 1
            continue
        if not dueno or not dueno.email:
            resumen['sin_correo'] += 1
            continue
        if simular:
            resumen['enviados'] += 1
            continue
        try:
            send_mail(
                subject=f'Recordatorio de vacuna para {vacuna.mascota.nombre}',
                message=_texto_correo(vacuna),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[dueno.email],
            )
        except Exception:  # SMTP caído, credenciales malas, etc.
            logger.exception('No se pudo enviar el recordatorio de la vacuna %s', vacuna.pk)
            resumen['errores'] += 1
            continue
        vacuna.alerta_enviada_el = timezone.localdate()
        vacuna.save(update_fields=['alerta_enviada_el'])
        resumen['enviados'] += 1
    return resumen
