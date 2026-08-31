from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from mascotas.models import Mascota


class Command(BaseCommand):
    """
    Crea los grupos de permisos de la clínica:

    - "Veterinarios": solo pueden VER la lista de mascotas.
    - "Administradores": pueden ver, crear, editar y eliminar mascotas.

    Uso:
        python manage.py setup_grupos
    """
    help = 'Crea los grupos "Veterinarios" (solo lectura) y "Administradores" (control total) sobre Mascota.'

    def handle(self, *args, **options):
        content_type = ContentType.objects.get_for_model(Mascota)
        permisos = {
            codename: Permission.objects.get(content_type=content_type, codename=codename)
            for codename in ('view_mascota', 'add_mascota', 'change_mascota', 'delete_mascota')
        }

        veterinarios, creado_vet = Group.objects.get_or_create(name='Veterinarios')
        veterinarios.permissions.set([permisos['view_mascota']])

        administradores, creado_admin = Group.objects.get_or_create(name='Administradores')
        administradores.permissions.set([
            permisos['view_mascota'],
            permisos['add_mascota'],
            permisos['change_mascota'],
            permisos['delete_mascota'],
        ])

        self.stdout.write(self.style.SUCCESS(
            'Grupos listos: "Veterinarios" (solo ver) y "Administradores" (ver, crear, editar, eliminar).'
        ))
        self.stdout.write(
            'Asigna usuarios a estos grupos desde /admin/ -> Usuarios -> (elige usuario) -> Grupos.'
        )
