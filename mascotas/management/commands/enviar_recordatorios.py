import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from mascotas.models import Cita, Vacuna


class Command(BaseCommand):
    """
    Envía recordatorios por correo a los dueños:
    - Dosis de vacuna que vencen dentro de los próximos N días (por defecto 7).
    - Citas programadas para mañana.

    Solo se envía a dueños que tengan correo registrado.
    Si no hay SMTP configurado en .env, los correos se muestran en la consola.

    Uso:
        python manage.py enviar_recordatorios
        python manage.py enviar_recordatorios --dias 15
        python manage.py enviar_recordatorios --simular   (no envía, solo muestra)
    """
    help = 'Envía recordatorios de vacunas por vencer y citas de mañana a los dueños.'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=7,
                            help='Días de anticipación para avisar dosis por vencer (por defecto 7).')
        parser.add_argument('--simular', action='store_true',
                            help='Muestra qué se enviaría, sin enviar correos.')

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        manana = hoy + datetime.timedelta(days=1)
        simular = options['simular']

        vacunas = (
            Vacuna.objects.por_vencer(dias=options['dias'], hoy=hoy)
            .filter(mascota__dueno__email__isnull=False)
            .exclude(mascota__dueno__email='')
            .select_related('mascota', 'mascota__dueno')
        )
        citas = (
            Cita.objects.filter(fecha=manana, estado='programada')
            .filter(mascota__dueno__email__isnull=False)
            .exclude(mascota__dueno__email='')
            .select_related('mascota', 'mascota__dueno')
        )

        enviados = 0
        for vacuna in vacunas:
            dueno = vacuna.mascota.dueno
            asunto = f'Recordatorio: vacuna de {vacuna.mascota.nombre}'
            mensaje = (
                f'Hola {dueno.nombre},\n\n'
                f'Te recordamos que la próxima dosis de {vacuna.get_tipo_display()} '
                f'de {vacuna.mascota.nombre} corresponde el {vacuna.proxima_dosis:%d/%m/%Y}.\n'
                'Agenda una hora con nosotros.\n\nClínica Veterinaria'
            )
            enviados += self._enviar(dueno.email, asunto, mensaje, simular)

        for cita in citas:
            dueno = cita.mascota.dueno
            asunto = f'Recordatorio: cita de {cita.mascota.nombre} mañana'
            mensaje = (
                f'Hola {dueno.nombre},\n\n'
                f'{cita.mascota.nombre} tiene una cita mañana {cita.fecha:%d/%m/%Y} '
                f'a las {cita.hora:%H:%M} con {cita.veterinario}.\n\nClínica Veterinaria'
            )
            enviados += self._enviar(dueno.email, asunto, mensaje, simular)

        verbo = 'se enviarían' if simular else 'enviados'
        self.stdout.write(self.style.SUCCESS(f'Recordatorios {verbo}: {enviados}'))

    def _enviar(self, correo, asunto, mensaje, simular):
        if simular:
            self.stdout.write(f'[simulación] Para {correo}: {asunto}')
            return 1
        try:
            send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [correo])
        except Exception as error:  # SMTP caído, credenciales malas, etc.
            self.stderr.write(f'No se pudo enviar a {correo}: {error}')
            return 0
        return 1
