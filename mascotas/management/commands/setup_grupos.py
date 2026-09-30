from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

# Permisos por grupo (GA2). Formato: 'accion_modelo' de la app mascotas.
# Los modelos se nombran en minúscula (dueño incluye la ñ).
CRUD = ('view', 'add', 'change', 'delete')
MODELOS = ('mascota', 'dueño', 'cita', 'historialmedico', 'vacuna', 'factura', 'detallefactura')

GRUPOS = {
    # Control total de la clínica.
    'Administradores': [f'{a}_{m}' for m in MODELOS for a in CRUD] + ['manage_vacunas'],
    # Atención clínica: ven todo y gestionan citas, vacunas e historial.
    'Veterinarios': (
        ['view_mascota', 'view_dueño']
        + [f'{a}_{m}' for m in ('cita', 'historialmedico', 'vacuna') for a in ('view', 'add', 'change')]
        + ['manage_vacunas']
    ),
    # Dueños de mascotas: solo lectura y, por la regla de permisos.py, solo lo suyo.
    'Clientes': ['view_mascota', 'view_cita', 'view_vacuna', 'view_historialmedico', 'view_factura'],
}


class Command(BaseCommand):
    """
    Crea (o actualiza) los grupos de la clínica con sus permisos:

    - "Administradores": ver, crear, editar y eliminar todo.
    - "Veterinarios": ven todo; gestionan citas, historial médico y vacunas.
    - "Clientes": solo ven sus propias mascotas, citas, vacunas, historial y facturas.

    Uso:
        python manage.py setup_grupos

    Se puede ejecutar varias veces: deja los permisos siempre como están aquí.
    """
    help = 'Crea los grupos Administradores, Veterinarios y Clientes con sus permisos.'

    def handle(self, *args, **options):
        for nombre, codenames in GRUPOS.items():
            permisos = Permission.objects.filter(
                content_type__app_label='mascotas', codename__in=codenames
            )
            faltantes = set(codenames) - set(permisos.values_list('codename', flat=True))
            if faltantes:
                self.stdout.write(self.style.WARNING(
                    f'{nombre}: faltan permisos {sorted(faltantes)}. ¿Corriste "python manage.py migrate"?'
                ))
            grupo, _ = Group.objects.get_or_create(name=nombre)
            grupo.permissions.set(permisos)
            self.stdout.write(self.style.SUCCESS(f'Grupo "{nombre}" listo con {permisos.count()} permisos.'))

        self.stdout.write(
            'Asigna usuarios a estos grupos desde /admin/ -> Usuarios -> (elige usuario) -> Grupos.'
        )
