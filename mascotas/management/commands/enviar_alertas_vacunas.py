from django.core.management.base import BaseCommand

from mascotas.alertas import enviar_recordatorios
from mascotas.models import DIAS_AVISO_VACUNA


class Command(BaseCommand):
    """
    Envía por correo los recordatorios de vacunas vencidas o por vencer (JO3).

    Uso:
        python manage.py enviar_alertas_vacunas            # envía los correos
        python manage.py enviar_alertas_vacunas --simular  # solo muestra cuántos enviaría
        python manage.py enviar_alertas_vacunas --dias 15  # avisa con 15 días de anticipación

    Se puede programar una vez al día (Programador de tareas de Windows o cron).
    Sin EMAIL_HOST_PASSWORD en .env los correos se muestran en la consola.
    """
    help = 'Envía recordatorios por correo de vacunas vencidas o por vencer.'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=DIAS_AVISO_VACUNA,
                            help=f'Días de anticipación (por defecto {DIAS_AVISO_VACUNA}).')
        parser.add_argument('--simular', action='store_true',
                            help='No envía nada, solo informa cuántos correos saldrían.')

    def handle(self, *args, **options):
        resumen = enviar_recordatorios(dias=options['dias'], simular=options['simular'])
        verbo = 'se enviarían' if options['simular'] else 'enviados'
        self.stdout.write(self.style.SUCCESS(f"Recordatorios {verbo}: {resumen['enviados']}"))
        self.stdout.write(f"Ya avisados antes: {resumen['ya_avisados']}")
        self.stdout.write(f"Dueños sin correo: {resumen['sin_correo']}")
        if resumen['errores']:
            self.stdout.write(self.style.ERROR(f"Errores de envío: {resumen['errores']} (revisa la configuración de correo en .env)"))
