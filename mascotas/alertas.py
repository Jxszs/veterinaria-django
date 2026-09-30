"""
Alertas de vacunación (JO3).

Este módulo lo usan tanto la página de alertas como el comando
`python manage.py enviar_alertas_vacunas`, para que ambos calculen
exactamente lo mismo.
"""
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Exists, OuterRef
from django.utils import timezone

from .models import Cita, DIAS_AVISO_VACUNA, HORAS_AVISO_CITA, Mascota, Receta, Vacuna

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


# ────────────────────────────────────────────────────────────────────────────────
# Recordatorio de cita próxima (24 horas antes)
# ────────────────────────────────────────────────────────────────────────────────

def citas_para_recordar(horas=HORAS_AVISO_CITA, queryset=None):
    """
    Citas programadas que empiezan dentro de las próximas `horas` horas.

    Solo se avisa de las citas que aún no pasaron y que siguen 'programadas',
    para no avisar de una consulta que ya se hizo o se canceló.
    """
    queryset = queryset if queryset is not None else Cita.objects.all()
    ahora = timezone.localtime()
    return (
        queryset.filter(estado='programada', alerta_enviada_el__isnull=True)
        .select_related('mascota', 'mascota__dueno')
        .order_by('fecha', 'hora')
    )


def enviar_recordatorios_citas(horas=HORAS_AVISO_CITA, simular=False):
    """
    Envía a cada dueño el recordatorio de la cita que tiene en las próximas
    `horas` horas. Marca `Cita.alerta_enviada_el` para no repetir el aviso.

    Devuelve: {'enviados': n, 'sin_correo': n, 'ya_avisados': n, 'errores': n}
    """
    resumen = {'enviados': 0, 'sin_correo': 0, 'ya_avisados': 0, 'errores': 0}
    ahora = timezone.localtime()
    limite = ahora + timedelta(hours=horas)
    for cita in citas_para_recordar(horas):
        # La cita tiene que caer dentro de la ventana y no haber pasado ya.
        momento = timezone.make_aware(
            datetime.combine(cita.fecha, cita.hora),
            timezone.get_current_timezone(),
        )
        if momento < ahora or momento > limite:
            continue
        if cita.alerta_enviada_el:
            resumen['ya_avisados'] += 1
            continue
        dueno = cita.mascota.dueno
        if not dueno or not dueno.email:
            resumen['sin_correo'] += 1
            continue
        if simular:
            resumen['enviados'] += 1
            continue
        try:
            send_mail(
                subject=f'Recordatorio de cita para {cita.mascota.nombre}',
                message=(
                    f'Hola {dueno.nombre}:\n\n'
                    f'Te recordamos la cita de {cita.mascota.nombre} '
                    f'el {cita.fecha:%d/%m/%Y} a las {cita.hora:%H:%M} '
                    f'con {cita.veterinario}.\n\n'
                    f'Motivo: {cita.motivo or "consulta general"}.\n\n'
                    'Si necesitas cambiar la hora, responde este correo.\n\n'
                    'Saludos,\nClínica Veterinaria'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[dueno.email],
            )
        except Exception:
            logger.exception('No se pudo enviar el recordatorio de la cita %s', cita.pk)
            resumen['errores'] += 1
            continue
        cita.alerta_enviada_el = ahora
        cita.save(update_fields=['alerta_enviada_el'])
        resumen['enviados'] += 1
    return resumen


# ────────────────────────────────────────────────────────────────────────────────
# Aviso de receta lista para retirar
# ────────────────────────────────────────────────────────────────────────────────

def recetas_para_avisar(queryset=None):
    """Recetas indicadas hoy que todavía no se le avisó al dueño."""
    queryset = queryset if queryset is not None else Receta.objects.all()
    return (
        queryset.filter(receta_lista_el__isnull=True)
        .select_related('cita', 'cita__mascota', 'cita__mascota__dueno')
        .order_by('-fecha')
    )


def enviar_recordatorios_recetas(simular=False):
    """
    Avisa al dueño que ya puede retirar la receta de la consulta de hoy.

    Devuelve: {'enviados': n, 'sin_correo': n, 'ya_avisados': n, 'errores': n}
    """
    resumen = {'enviados': 0, 'sin_correo': 0, 'ya_avisados': 0, 'errores': 0}
    hoy = timezone.localdate()
    for receta in recetas_para_avisar():
        if receta.fecha != hoy:
            continue
        dueno = receta.cita.mascota.dueno
        if not dueno or not dueno.email:
            resumen['sin_correo'] += 1
            continue
        if simular:
            resumen['enviados'] += 1
            continue
        try:
            send_mail(
                subject=f'Receta lista para {receta.cita.mascota.nombre}',
                message=(
                    f'Hola {dueno.nombre}:\n\n'
                    f'La receta de {receta.cita.mascota.nombre} ya está lista '
                    f'para retirar en la clínica.\n\n'
                    f'Medicamento: {receta.medicamento}\n'
                    f'Dosis: {receta.dosis}\n'
                    f'Duración: {receta.duracion_dias} día(s)\n\n'
                    'Recuerda pasar por ella en horario de atención.\n\n'
                    'Saludos,\nClínica Veterinaria'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[dueno.email],
            )
        except Exception:
            logger.exception('No se pudo avisar la receta %s', receta.pk)
            resumen['errores'] += 1
            continue
        receta.receta_lista_el = timezone.localtime()
        receta.save(update_fields=['receta_lista_el'])
        resumen['enviados'] += 1
    return resumen
