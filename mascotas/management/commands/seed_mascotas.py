from django.core.management.base import BaseCommand

from mascotas.models import Mascota

DATOS_INICIALES = [
    {'nombre': 'Firulais', 'especie': 'Perro', 'edad': 3, 'vacunado': True, 'alergico': False},
    {'nombre': 'Michi', 'especie': 'Gato', 'edad': 2, 'vacunado': False, 'alergico': False},
    {'nombre': 'Perico', 'especie': 'Loro', 'edad': 1, 'vacunado': False, 'alergico': False},
    {'nombre': 'Rocky', 'especie': 'Perro', 'edad': 5, 'vacunado': True, 'alergico': False},
    {'nombre': 'Copito', 'especie': 'Conejo', 'edad': 1, 'vacunado': False, 'alergico': True},
    {'nombre': 'Luna', 'especie': 'Gato', 'edad': 4, 'vacunado': True, 'alergico': False},
]


class Command(BaseCommand):
    """
    Carga mascotas de ejemplo (mínimo 5, según pide la rúbrica en la
    sección Admin) para probar el sistema y usarlas en la demo en vivo.

    Uso:
        python manage.py seed_mascotas
    """
    help = 'Carga mascotas de ejemplo (mínimo 5) para pruebas y la presentación en vivo.'

    def handle(self, *args, **options):
        creados = 0
        for datos in DATOS_INICIALES:
            _, fue_creado = Mascota.objects.get_or_create(nombre=datos['nombre'], defaults=datos)
            if fue_creado:
                creados += 1

        total = Mascota.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'{creados} mascota(s) nueva(s) creada(s). Total en la base de datos: {total}.'
        ))
