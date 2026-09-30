import logging

from django.db import DatabaseError

from .alertas import total_alertas_urgentes

logger = logging.getLogger(__name__)


def alertas(request):
    """
    Agrega 'total_alertas' a todas las plantillas para mostrar el contador
    en el menú. Solo se calcula para usuarios que pueden ver vacunas o citas.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    if not (user.has_perm('mascotas.view_vacuna') or user.has_perm('mascotas.view_cita')):
        return {}
    try:
        return {'total_alertas': total_alertas_urgentes()}
    except DatabaseError:
        logger.exception('No se pudo calcular el total de alertas')
        return {'total_alertas': 0}
