from django.core.management.base import BaseCommand

from mascotas.alertas import enviar_recordatorios_citas, enviar_recordatorios_recetas
from mascotas.models import HORAS_AVISO_CITA


class Command(BaseCommand):
    """
    Envía a los dueños los dos avisos automáticos que pide el enunciado,
    aparte del de vacunas (que envía `enviar_alertas_vacunas`):

      - cita que es en las próximas 24 horas,
      - receta indicada que ya está lista para retirar.

    Antes este comando avisaba solo de las citas del día siguiente y usaba un
    `Vacuna.objects.por_vencer()` que ya no existe, así que fallaba con
    AttributeError. Ahora las tres alertas comparten la lógica de
    `mascotas/alertas.py`, que es la misma que usan las vistas y los tests.

    Solo se avisa a dueños con correo registrado. Sin `EMAIL_HOST_PASSWORD`
    en .env los correos se muestran en la consola.

    Uso:
        python manage.py enviar_recordatorios                    # envía los correos
        python manage.py enviar_recordatorios --simular          # solo informa cuántos saldrían
        python manage.py enviar_recordatorios --horas 48         # avisa 48 horas antes
        python manage.py enviar_recordatorios --solo citas       # solo el aviso de citas
        python manage.py enviar_recordatorios --solo recetas     # solo el aviso de recetas
    """
    help = 'Envía recordatorios de cita próxima y avisos de receta lista.'

    def add_arguments(self, parser):
        parser.add_argument('--horas', type=int, default=HORAS_AVISO_CITA,
                            help=f'Horas de anticipación de la cita (por defecto {HORAS_AVISO_CITA}).')
        parser.add_argument('--simular', action='store_true',
                            help='No envía nada, solo informa cuántos correos saldrían.')
        parser.add_argument('--solo', choices=('citas', 'recetas'), default=None,
                            help='Envía solo el aviso indicado y deja el otro fuera.')

    def handle(self, *args, **options):
        simular = options['simular']
        verbo = 'se enviarían' if simular else 'enviados'
        solo = options['solo']

        if solo in (None, 'citas'):
            self._informe('Recordatorios de cita',
                          enviar_recordatorios_citas(horas=options['horas'], simular=simular),
                          verbo)

        if solo in (None, 'recetas'):
            self._informe('Avisos de receta',
                          enviar_recordatorios_recetas(simular=simular),
                          verbo)

    def _informe(self, titulo, resumen, verbo):
        self.stdout.write(self.style.SUCCESS(f'{titulo} {verbo}: {resumen["enviados"]}'))
        if resumen['ya_avisados']:
            self.stdout.write(f'Ya avisados antes: {resumen["ya_avisados"]}')
        if resumen['sin_correo']:
            self.stdout.write(f'Dueños sin correo: {resumen["sin_correo"]}')
        if resumen['errores']:
            self.stdout.write(self.style.ERROR(
                f'Errores de envío: {resumen["errores"]} '
                '(revisa EMAIL_HOST_PASSWORD en .env)'
            ))
