import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import DatabaseError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import Dueño, Mascota, Cita, HistorialMedico, Vacuna
from .forms import DuenoForm, MascotaForm, CitaForm, HistorialMedicoForm, VacunaForm
from .permisos import filtrar_por_dueno


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
# Ayudantes reutilizables (JO1): guardan/eliminan con el mismo manejo de
# errores que usan las vistas de mascotas (try/except DatabaseError + mensajes).
# ────────────────────────────────────────────────────────────────────────────────

def _guardar_formulario(request, form_class, template, url_exito, mensaje_ok,
                        instancia=None, contexto_extra=None, initial=None):
    """
    Procesa un formulario de alta o edición.

    - GET: muestra el formulario vacío (o con los datos de `instancia`).
    - POST válido: guarda dentro de try/except y redirige a `url_exito`.
    - POST inválido: vuelve a mostrar el formulario con los errores en rojo.

    `mensaje_ok` recibe el objeto guardado y devuelve el texto de éxito.
    """
    if request.method == 'POST':
        form = form_class(request.POST, instance=instancia)
        if form.is_valid():
            try:
                objeto = form.save()
            except DatabaseError:
                logger.exception('Error al guardar %s', form_class.__name__)
                messages.error(request, 'No se pudieron guardar los datos. ' + ERROR_BD)
            else:
                messages.success(request, mensaje_ok(objeto))
                return redirect(url_exito)
        else:
            messages.warning(request, 'Revisa los campos marcados en rojo.')
    else:
        form = form_class(instance=instancia, initial=initial)
    contexto = {'form': form, 'object': instancia}
    contexto.update(contexto_extra or {})
    return render(request, template, contexto)


def _confirmar_eliminacion(request, objeto, template, url_exito, descripcion):
    """GET muestra la confirmación; POST elimina con manejo de errores."""
    if request.method == 'POST':
        try:
            objeto.delete()
        except DatabaseError:
            logger.exception('Error al eliminar %s', descripcion)
            messages.error(request, f'No se pudo eliminar {descripcion}. ' + ERROR_BD)
        else:
            messages.success(request, f'Se eliminó {descripcion}.')
        return redirect(url_exito)
    return render(request, template, {'object': objeto})


def _mascota_inicial(request):
    """Permite abrir un formulario con la mascota ya elegida (?mascota=ID)."""
    mascota_id = request.GET.get('mascota', '')
    return {'mascota': mascota_id} if mascota_id.isdigit() else None


# ────────────────────────────────────────────────────────────────────────────────
# Vistas para Dueño (JO1)
# ────────────────────────────────────────────────────────────────────────────────

@login_required
@permission_required('mascotas.view_dueño', raise_exception=True)
def listar_duenos(request):
    """Lista de dueños con buscador por nombre, correo o usuario."""
    query = request.GET.get('q', '').strip()[:100]
    contexto = {'duenos': [], 'query': query}
    try:
        duenos = filtrar_por_dueno(
            Dueño.objects.select_related('user').annotate(total_mascotas=Count('mascotas')),
            request.user, ruta='user',
        )
        if query:
            duenos = duenos.filter(
                Q(nombre__icontains=query) | Q(email__icontains=query)
                | Q(user__username__icontains=query)
            )
        contexto['duenos'] = list(duenos)
    except DatabaseError:
        logger.exception('Error al listar dueños')
        messages.error(request, 'No se pudieron cargar los dueños. ' + ERROR_BD)
    return render(request, 'mascotas/dueno_list.html', contexto)


@login_required
@permission_required('mascotas.add_dueño', raise_exception=True)
def crear_dueno(request):
    return _guardar_formulario(
        request, DuenoForm, 'mascotas/dueno_form.html', 'mascotas:lista_duenos',
        lambda d: f'Se registró al dueño "{d.nombre}".',
    )


@login_required
@permission_required('mascotas.change_dueño', raise_exception=True)
def editar_dueno(request, pk):
    dueno = get_object_or_404(Dueño, pk=pk)
    return _guardar_formulario(
        request, DuenoForm, 'mascotas/dueno_form.html', 'mascotas:lista_duenos',
        lambda d: f'Se actualizaron los datos de "{d.nombre}".', instancia=dueno,
    )


@login_required
@permission_required('mascotas.delete_dueño', raise_exception=True)
def eliminar_dueno(request, pk):
    """Al eliminar un dueño sus mascotas NO se borran: quedan sin dueño (SET_NULL)."""
    dueno = get_object_or_404(Dueño, pk=pk)
    return _confirmar_eliminacion(
        request, dueno, 'mascotas/dueno_confirm_delete.html', 'mascotas:lista_duenos',
        f'al dueño "{dueno.nombre}"',
    )


# ────────────────────────────────────────────────────────────────────────────────
# Vistas para Cita
# ────────────────────────────────────────────────────────────────────────────────

@login_required
@permission_required('mascotas.view_cita', raise_exception=True)
def listar_citas(request):
    """
    Lista las citas. El personal ve todas; un cliente solo las de sus mascotas.
    """
    query = request.GET.get('q', '').strip()[:100]
    estado = request.GET.get('estado', '').strip()

    contexto = {
        'citas': [],
        'query': query,
        'estado_seleccionado': estado,
    }

    try:
        # Object-level permission: los clientes solo ven lo de sus mascotas
        citas = filtrar_por_dueno(
            Cita.objects.select_related('mascota', 'mascota__dueno'), request.user
        )

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
        form = CitaForm(initial=_mascota_inicial(request))
    return render(request, 'mascotas/cita_form.html', {'form': form})


@login_required
@permission_required('mascotas.change_cita', raise_exception=True)
def editar_cita(request, pk):
    """Edición de una cita existente."""
    cita = get_object_or_404(filtrar_por_dueno(Cita.objects.all(), request.user), pk=pk)
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
    cita = get_object_or_404(filtrar_por_dueno(Cita.objects.all(), request.user), pk=pk)
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
    """
    Lista el historial médico. El personal ve todo; un cliente solo el de sus mascotas.
    """
    query = request.GET.get('q', '').strip()[:100]
    mascota_id = request.GET.get('mascota', '').strip()

    contexto = {
        'historial': [],
        'query': query,
        'mascota_seleccionada': mascota_id,
    }

    try:
        # Object-level permission: los clientes solo ven lo de sus mascotas
        historial = filtrar_por_dueno(
            HistorialMedico.objects.select_related('mascota', 'mascota__dueno'), request.user
        )

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
        form = HistorialMedicoForm(initial=_mascota_inicial(request))
    return render(request, 'mascotas/historial_form.html', {'form': form})


@login_required
@permission_required('mascotas.change_historialmedico', raise_exception=True)
def editar_historial(request, pk):
    registro = get_object_or_404(
        filtrar_por_dueno(HistorialMedico.objects.all(), request.user), pk=pk
    )
    return _guardar_formulario(
        request, HistorialMedicoForm, 'mascotas/historial_form.html',
        'mascotas:lista_historial',
        lambda r: f'Se actualizó el registro de "{r.mascota.nombre}".', instancia=registro,
    )


@login_required
@permission_required('mascotas.delete_historialmedico', raise_exception=True)
def eliminar_historial(request, pk):
    registro = get_object_or_404(
        filtrar_por_dueno(HistorialMedico.objects.all(), request.user), pk=pk
    )
    return _confirmar_eliminacion(
        request, registro, 'mascotas/historial_confirm_delete.html',
        'mascotas:lista_historial',
        f'el registro del {registro.fecha:%d/%m/%Y} de "{registro.mascota.nombre}"',
    )


# ────────────────────────────────────────────────────────────────────────────────
# Vistas para Vacuna
# ────────────────────────────────────────────────────────────────────────────────

@login_required
@permission_required('mascotas.view_vacuna', raise_exception=True)
def listar_vacunas(request):
    """
    Lista las vacunas. El personal ve todas; un cliente solo las de sus mascotas.
    """
    query = request.GET.get('q', '').strip()[:100]
    tipo = request.GET.get('tipo', '').strip()

    contexto = {
        'vacunas': [],
        'query': query,
        'tipo_seleccionado': tipo,
    }

    try:
        # Object-level permission: los clientes solo ven lo de sus mascotas
        vacunas = filtrar_por_dueno(
            Vacuna.objects.select_related('mascota', 'mascota__dueno'), request.user
        )

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
                    f'Se registró vacuna "{vacuna.get_tipo_display()}" para "{vacuna.mascota.nombre}".'
                )
                return redirect('mascotas:lista_vacunas')
        else:
            messages.warning(request, 'Revisa los campos marcados en rojo.')
    else:
        form = VacunaForm(initial=_mascota_inicial(request))
    return render(request, 'mascotas/vacuna_form.html', {'form': form})


@login_required
@permission_required('mascotas.change_vacuna', raise_exception=True)
def editar_vacuna(request, pk):
    vacuna = get_object_or_404(filtrar_por_dueno(Vacuna.objects.all(), request.user), pk=pk)
    return _guardar_formulario(
        request, VacunaForm, 'mascotas/vacuna_form.html', 'mascotas:lista_vacunas',
        lambda v: f'Se actualizó la vacuna de "{v.mascota.nombre}".', instancia=vacuna,
    )


@login_required
@permission_required('mascotas.delete_vacuna', raise_exception=True)
def eliminar_vacuna(request, pk):
    vacuna = get_object_or_404(filtrar_por_dueno(Vacuna.objects.all(), request.user), pk=pk)
    return _confirmar_eliminacion(
        request, vacuna, 'mascotas/vacuna_confirm_delete.html', 'mascotas:lista_vacunas',
        f'la vacuna {vacuna.get_tipo_display()} de "{vacuna.mascota.nombre}"',
    )
