import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import DatabaseError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MascotaForm
from .models import Mascota

logger = logging.getLogger(__name__)
ERROR_BD = 'No se pudo conectar con la base de datos. Intenta nuevamente en unos minutes.'


@login_required
def listar_mascotas(request):
    """
    Vista principal: muestra TODAS las mascotas de la clínica.

    - Consulta los datos con Mascota.objects.all() (ordenados alfabéticamente
      por el Meta.ordering del modelo).
    - Permite filtrar esa misma consulta por nombre, especie y estado de
      vacunación usando los parámetros de la URL (?q=, ?especie=, ?estado=).
    - Si la base de datos falla, muestra un mensaje claro en vez de un error 500.
    """
    query = request.GET.get('q', '').strip()[:100]
    especie = request.GET.get('especie', '').strip()[:50]
    estado = request.GET.get('estado', '').strip()

    contexto = {
        'mascotas': [],
        'query': query,
        'especie_seleccionada': especie,
        'estado_seleccionado': estado,
        'especies': [],
        'total_pendientes': 0,
    }

    try:
        mascotas = Mascota.objects.all()

        if query:
            mascotas = mascotas.filter(nombre__icontains=query)

        if especie:
            mascotas = mascotas.filter(especie__iexact=especie)

        if estado == 'al_dia':
            mascotas = mascotas.filter(vacunado=True, alergico=False)
        elif estado == 'pendiente':
            mascotas = mascotas.filter(vacunado=False, alergico=False)
        elif estado == 'alergia':
            mascotas = mascotas.filter(alergico=True)

        # list() obliga a ejecutar la consulta aquí, dentro del try.
        contexto['mascotas'] = list(mascotas)
        contexto['especies'] = list(
            Mascota.objects.order_by('especie').values_list('especie', flat=True).distinct()
        )
        contexto['total_pendientes'] = Mascota.objects.filter(
            vacunado=False, alergico=False
        ).count()
    except DatabaseError:
        logger.exception('Error al listar mascotas')
        messages.error(request, ERROR_BD)

    return render(request, 'mascotas/mascota_list.html', contexto)


@login_required
@permission_required('mascotas.add_mascota', raise_exception=True)
def crear_mascota(request):
    """Alta de una nueva mascota mediante un formulario web. Solo Administradores."""
    if request.method == 'POST':
        form = MascotaForm(request.POST)
        if form.is_valid():
            try:
                mascota = form.save()
            except DatabaseError:
                logger.exception('Error al crear mascota')
                messages.error(request, 'No se pudo guardar la mascota. ' + ERROR_BD)
            else:
                messages.success(request, f'Se registró a "{mascota.nombre}" correctamente.')
                return redirect('mascotas:lista')
        else:
            messages.warning(request, 'Revisa los campos marcados en rojo.')
    else:
        form = MascotaForm()
    return render(request, 'mascotas/mascota_form.html', {'form': form})


@login_required
@permission_required('mascotas.change_mascota', raise_exception=True)
def editar_mascota(request, pk):
    """Edición de una mascota existente (ej: marcarla como vacunada). Solo Administradores."""
    mascota = get_object_or_404(Mascota, pk=pk)
    if request.method == 'POST':
        form = MascotaForm(request.POST, instance=mascota)
        if form.is_valid():
            try:
                form.save()
            except DatabaseError:
                logger.exception('Error al editar mascota %s', pk)
                messages.error(request, 'No se pudieron guardar los cambios. ' + ERROR_BD)
            else:
                messages.success(request, f'Se actualizó a "{mascota.nombre}" correctamente.')
                return redirect('mascotas:lista')
        else:
            messages.warning(request, 'Revisa los campos marcados en rojo.')
    else:
        form = MascotaForm(instance=mascota)
    return render(request, 'mascotas/mascota_form.html', {'form': form, 'object': mascota})


@login_required
@permission_required('mascotas.delete_mascota', raise_exception=True)
def eliminar_mascota(request, pk):
    """Eliminación de una mascota, con confirmación previa. Solo Administradores."""
    mascota = get_object_or_404(Mascota, pk=pk)
    if request.method == 'POST':
        nombre = mascota.nombre
        try:
            mascota.delete()
        except DatabaseError:
            logger.exception('Error al eliminar mascota %s', pk)
            messages.error(request, f'No se pudo eliminar a "{nombre}". ' + ERROR_BD)
        else:
            messages.success(request, f'Se eliminó a "{nombre}".')
        return redirect('mascotas:lista')
    return render(request, 'mascotas/mascota_confirm_delete.html', {'object': mascota})