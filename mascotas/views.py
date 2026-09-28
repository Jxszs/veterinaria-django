import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import DatabaseError
from django.shortcuts import get_object_or_404, redirect, render

from .models import Mascota, Cita, HistorialMedico, Vacuna
from .forms import MascotaForm, CitaForm, HistorialMedicoForm, VacunaForm


logger = logging.getLogger(__name__)
ERROR_BD = 'No se pudo conectar con la base de datos. Intenta nuevamente en unos minutos.'


@login_required
def listar_mascotas(request):
    """
    Vista principal: muestra TODAS las mascotas de la clínica.
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

# ────────────────────────────────────────────────────────────────────────────────
# Vistas para Cita
# ────────────────────────────────────────────────────────────────────────────────

@login_required
@permission_required('mascotas.view_cita', raise_exception=True)
def listar_citas(request):
    """Lista todas las citas programadas."""
    query = request.GET.get('q', '').strip()[:100]
    estado = request.GET.get('estado', '').strip()

    contexto = {
        'citas': [],
        'query': query,
        'estado_seleccionado': estado,
    }

    try:
        citas = Cita.objects.select_related('mascota').all()
        if query:
            citas = citas.filter(mascota__nombre__icontains=query)
        if estado:
            citas = citas.filter(estado__iexact=estado)
        contexto['citas'] = list(citas)
    except DatabaseError:
        logger.exception('Error al listar citas')
        messages.error(request, 'No se pudieron cargar las citas. ' + ERROR_BD)

    return render(request, 'mascotas/cita_list.html', contexto)


@login_required
@permission_required('mascotas.add_cita', raise_exception=True)
def crear_cita(request):
    """Alta de una nueva cita."""
    if request.method == 'POST':
        form = CitaForm(request.POST)
        if form.is_valid():
            try:
                cita = form.save()
            except DatabaseError:
                logger.exception('Error al crear cita')
                messages.error(request, 'No se pudo guardar la cita. ' + ERROR_BD)
            else:
                messages.success(request, f'Se programó cita para "{cita.mascota.nombre}".')
                return redirect('mascotas:lista_citas')
        else:
            messages.warning(request, 'Revisa los campos marcados en rojo.')
    else:
        form = CitaForm()
    return render(request, 'mascotas/cita_form.html', {'form': form})


@login_required
@permission_required('mascotas.change_cita', raise_exception=True)
def editar_cita(request, pk):
    """Edición de una cita existente."""
    cita = get_object_or_404(Cita, pk=pk)
    if request.method == 'POST':
        form = CitaForm(request.POST, instance=cita)
        if form.is_valid():
            try:
                form.save()
            except DatabaseError:
                logger.exception('Error al editar cita %s', pk)
                messages.error(request, 'No se pudieron guardar los cambios. ' + ERROR_BD)
            else:
                messages.success(request, f'Se actualizó la cita de "{cita.mascota.nombre}".')
                return redirect('mascotas:lista_citas')
        else:
            messages.warning(request, 'Revisa los campos marcados en rojo.')
    else:
        form = CitaForm(instance=cita)
    return render(request, 'mascotas/cita_form.html', {'form': form, 'object': cita})


@login_required
@permission_required('mascotas.delete_cita', raise_exception=True)
def eliminar_cita(request, pk):
    """Eliminación de una cita."""
    cita = get_object_or_404(Cita, pk=pk)
    if request.method == 'POST':
        try:
            cita.delete()
        except DatabaseError:
            logger.exception('Error al eliminar cita %s', pk)
            messages.error(request, 'No se pudo eliminar la cita. ' + ERROR_BD)
        else:
            messages.success(request, 'Se eliminó la cita.')
        return redirect('mascotas:lista_citas')
    return render(request, 'mascotas/cita_confirm_delete.html', {'object': cita})


# ────────────────────────────────────────────────────────────────────────────────
# Vistas para HistorialMedico
# ────────────────────────────────────────────────────────────────────────────────

@login_required
@permission_required('mascotas.view_historialmedico', raise_exception=True)
def listar_historial(request):
    """Lista el historial médico de todas las mascotas."""
    query = request.GET.get('q', '').strip()[:100]
    mascota_id = request.GET.get('mascota', '').strip()

    contexto = {
        'historial': [],
        'query': query,
        'mascota_seleccionada': mascota_id,
    }

    try:
        historial = HistorialMedico.objects.select_related('mascota').all()
        if query:
            historial = historial.filter(mascota__nombre__icontains=query)
        if mascota_id:
            historial = historial.filter(mascota__pk=mascota_id)
        contexto['historial'] = list(historial)
    except DatabaseError:
        logger.exception('Error al listar historial')
        messages.error(request, 'No se pudo cargar el historial. ' + ERROR_BD)

    return render(request, 'mascotas/historial_list.html', contexto)


@login_required
@permission_required('mascotas.add_historialmedico', raise_exception=True)
def crear_historial(request):
    """Registro nuevo de historial médico."""
    if request.method == 'POST':
        form = HistorialMedicoForm(request.POST)
        if form.is_valid():
            try:
                registro = form.save()
            except DatabaseError:
                logger.exception('Error al crear historial')
                messages.error(request, 'No se pudo guardar el registro. ' + ERROR_BD)
            else:
                messages.success(request, f'Se registró historial para "{registro.mascota.nombre}".')
                return redirect('mascotas:lista_historial')
        else:
            messages.warning(request, 'Revisa los campos marcados en rojo.')
    else:
        form = HistorialMedicoForm()
    return render(request, 'mascotas/historial_form.html', {'form': form})


# ────────────────────────────────────────────────────────────────────────────────
# Vistas para Vacuna
# ────────────────────────────────────────────────────────────────────────────────

@login_required
@permission_required('mascotas.view_vacuna', raise_exception=True)
def listar_vacunas(request):
    """Lista todas las vacunas registradas."""
    query = request.GET.get('q', '').strip()[:100]
    tipo = request.GET.get('tipo', '').strip()

    contexto = {
        'vacunas': [],
        'query': query,
        'tipo_seleccionado': tipo,
    }

    try:
        vacunas = Vacuna.objects.select_related('mascota').all()
        if query:
            vacunas = vacunas.filter(mascota__nombre__icontains=query)
        if tipo:
            vacunas = vacunas.filter(tipo__iexact=tipo)
        contexto['vacunas'] = list(vacunas)
    except DatabaseError:
        logger.exception('Error al listar vacunas')
        messages.error(request, 'No se pudieron cargar las vacunas. ' + ERROR_BD)

    return render(request, 'mascotas/vacuna_list.html', contexto)


@login_required
@permission_required('mascotas.add_vacuna', raise_exception=True)
def crear_vacuna(request):
    """Registro de nueva vacunación."""
    if request.method == 'POST':
        form = VacunaForm(request.POST)
        if form.is_valid():
            try:
                vacuna = form.save()
            except DatabaseError:
                logger.exception('Error al crear vacuna')
                messages.error(request, 'No se pudo registrar la vacuna. ' + ERROR_BD)
            else:
                messages.success(
                    request,
                    f'Se registró vacuna "{vacuna.tipo}" para "{vacuna.mascota.nombre}".'
                )
                return redirect('mascotas:lista_vacunas')
        else:
            messages.warning(request, 'Revisa los campos marcados en rojo.')
    else:
        form = VacunaForm()
    return render(request, 'mascotas/vacuna_form.html', {'form': form})