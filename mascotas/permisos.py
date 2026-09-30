"""
Reglas de acceso a nivel de objeto (qué registros ve cada usuario).

Se centralizan aquí para que las vistas, el dashboard, los reportes y el
carnet PDF usen exactamente la misma regla. Si la regla cambia, se cambia
solo en este archivo.

Regla:
  - Superusuario y personal de la clínica (grupos Veterinarios o
    Administradores) ven los registros de todos los dueños.
  - Un "cliente" (usuario con perfil de Dueño y sin rol de personal) ve
    solo sus propias mascotas y lo relacionado con ellas.

Esto corrige la versión anterior de G2, donde cualquier usuario que no fuera
superusuario (incluidos veterinarios) quedaba viendo listas vacías.
"""

GRUPOS_PERSONAL = ('Veterinarios', 'Administradores')


def es_personal(user):
    """True si el usuario es superusuario o pertenece a un grupo del personal."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name__in=GRUPOS_PERSONAL).exists()


def es_cliente(user):
    """True si el usuario es dueño de mascotas y no es personal de la clínica."""
    if not user.is_authenticated or es_personal(user):
        return False
    return user.duenos.exists()


def filtrar_por_dueno(queryset, user, ruta='mascota__dueno__user'):
    """
    Filtra un queryset para que el usuario solo vea lo que le corresponde.

    `ruta` es el camino desde el modelo hasta el User del dueño, por ejemplo:
      - Mascota                 -> 'dueno__user'
      - Cita / Vacuna / Factura -> 'mascota__dueno__user' (o 'dueno__user')
      - Dueño                   -> 'user'
    """
    if es_cliente(user):
        return queryset.filter(**{ruta: user})
    return queryset


def rol_de(user):
    """Nombre del rol para mostrar en la barra superior."""
    if not user.is_authenticated:
        return ''
    if user.is_superuser or user.groups.filter(name='Administradores').exists() or user.has_perm('mascotas.add_mascota'):
        return 'Administrador'
    if user.groups.filter(name='Veterinarios').exists():
        return 'Veterinario'
    if es_cliente(user) or user.groups.filter(name='Clientes').exists():
        return 'Cliente'
    if user.has_perm('mascotas.view_mascota'):
        return 'Veterinario'
    return ''


def contexto_rol(request):
    """Context processor: deja {{ rol_usuario }} disponible en todas las plantillas."""
    return {'rol_usuario': rol_de(request.user) if hasattr(request, 'user') else ''}

