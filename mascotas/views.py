from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MascotaForm
from .models import Mascota


@login_required
def listar_mascotas(request):
    """
    Vista principal: muestra TODAS las mascotas de la clínica.

    - Consulta los datos con Mascota.objects.all() (ordenados alfabéticamente
      por el Meta.ordering del modelo).
    - Permite filtrar esa misma consulta por nombre, especie y estado de
      vacunación usando los parámetros de la URL (?q=, ?especie=, ?estado=).
    - Pasa los datos como contexto al template, que los recorre con
      {% for %} y decide el color de cada fila con {% if %}.
    """
    mascotas = Mascota.objects.all()

    # Búsqueda rápida por nombre (ej: cuando llama el dueño preguntando por su mascota)
    query = request.GET.get('q', '').strip()
    if query:
        mascotas = mascotas.filter(nombre__icontains=query)

    # Filtro por especie (perro, gato, conejo, loro, etc.)
    especie = request.GET.get('especie', '').strip()
    if especie:
        mascotas = mascotas.filter(especie__iexact=especie)

    # Filtro rápido por estado de vacunación: al día, pendiente o alergia
    estado = request.GET.get('estado', '').strip()
    if estado == 'al_dia':
        mascotas = mascotas.filter(vacunado=True, alergico=False)
    elif estado == 'pendiente':
        mascotas = mascotas.filter(vacunado=False, alergico=False)
    elif estado == 'alergia':
        mascotas = mascotas.filter(alergico=True)

    contexto = {
        'mascotas': mascotas,
        'query': query,
        'especie_seleccionada': especie,
        'estado_seleccionado': estado,
        'especies': Mascota.objects.order_by('especie').values_list('especie', flat=True).distinct(),
        'total_pendientes': Mascota.objects.filter(vacunado=False, alergico=False).count(),
    }
    return render(request, 'mascotas/mascota_list.html', contexto)


@login_required
@permission_required('mascotas.add_mascota', raise_exception=True)
def crear_mascota(request):
    """Alta de una nueva mascota mediante un formulario web. Solo Administradores."""
    if request.method == 'POST':
        form = MascotaForm(request.POST)
        if form.is_valid():
            mascota = form.save()
            messages.success(request, f'Se registró a "{mascota.nombre}" correctamente.')
            return redirect('mascotas:lista')
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
            form.save()
            messages.success(request, f'Se actualizó a "{mascota.nombre}" correctamente.')
            return redirect('mascotas:lista')
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
        mascota.delete()
        messages.success(request, f'Se eliminó a "{nombre}".')
        return redirect('mascotas:lista')
    return render(request, 'mascotas/mascota_confirm_delete.html', {'object': mascota})
