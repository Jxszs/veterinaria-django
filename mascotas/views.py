import csv
import logging
from datetime import date, time

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import DatabaseError, transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .models import Cita, Dueño, Factura, HistorialMedico, Mascota, Vacuna
from .forms import (
    CitaForm, DetalleFacturaFormSet, DuenoForm, FacturaForm, HistorialMedicoForm,
    MascotaForm, VacunaForm,
)
from .alertas import enviar_recordatorios, mascotas_sin_vacunas, vacunas_con_refuerzo_pendiente
from .models import DIAS_AVISO_VACUNA
from .permisos import filtrar_por_dueno
from .reportes import carnet_vacunas_pdf
from .templatetags.veterinaria_extras import formato_clp


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
# Ficha de la mascota con línea de tiempo (JO2)
# ────────────────────────────────────────────────────────────────────────────────

def _linea_de_tiempo(mascota):
    """
    Junta citas, vacunas e historial médico en una sola lista ordenada
    del evento más reciente al más antiguo.
    """
    eventos = []
    for cita in mascota.citas.all():
        eventos.append({
            'fecha': cita.fecha, 'hora': cita.hora, 'tipo': 'cita', 'icono': '📅',
            'titulo': f'Cita: {cita.motivo or "consulta"}',
            'detalle': f'{cita.veterinario} — {cita.get_estado_display()}',
            'objeto': cita,
        })
    for vacuna in mascota.vacunas.all():
        detalle = f'Lote {vacuna.lote}' if vacuna.lote else ''
        if vacuna.proxima_dosis:
            detalle = (detalle + ' — ' if detalle else '') + f'próxima dosis {vacuna.proxima_dosis:%d/%m/%Y}'
        eventos.append({
            'fecha': vacuna.fecha_aplicacion, 'hora': None, 'tipo': 'vacuna', 'icono': '💉',
            'titulo': f'Vacuna {vacuna.get_tipo_display()}', 'detalle': detalle,
            'objeto': vacuna,
        })
    for registro in mascota.historial.all():
        eventos.append({
            'fecha': registro.fecha, 'hora': None, 'tipo': 'historial', 'icono': '🩺',
            'titulo': registro.diagnostico or 'Registro clínico',
            'detalle': f'{registro.veterinario} — {registro.tratamiento or "sin tratamiento indicado"}',
            'objeto': registro,
        })
    # Orden: fecha y hora descendente (los eventos sin hora van al final del día).
    eventos.sort(key=lambda e: (e['fecha'], e['hora'] or time.min), reverse=True)
    return eventos


@login_required
def ficha_mascota(request, pk):
    """
    Ficha clínica de una mascota: datos, dueño, próximas citas y una línea de
    tiempo con todo lo que le ha pasado (citas, vacunas e historial).
    Un cliente solo puede abrir la ficha de sus propias mascotas.
    """
    mascota = get_object_or_404(
        filtrar_por_dueno(Mascota.objects.select_related('dueno'), request.user, ruta='dueno__user'),
        pk=pk,
    )
    contexto = {'mascota': mascota, 'eventos': [], 'proximas_citas': []}
    try:
        hoy = timezone.localdate()
        contexto['proximas_citas'] = list(
            mascota.citas.filter(fecha__gte=hoy, estado='programada').order_by('fecha', 'hora')
        )
        contexto['eventos'] = _linea_de_tiempo(mascota)
    except DatabaseError:
        logger.exception('Error al cargar la ficha de la mascota %s', pk)
        messages.error(request, 'No se pudo cargar la ficha completa. ' + ERROR_BD)
    return render(request, 'mascotas/mascota_ficha.html', contexto)


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
    cuando = request.GET.get('cuando', '').strip()

    contexto = {
        'citas': [],
        'query': query,
        'estado_seleccionado': estado,
        'cuando_seleccionado': cuando,
        'estados': Cita.ESTADO_CHOICES,
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
        hoy = timezone.localdate()
        if cuando == 'hoy':
            citas = citas.filter(fecha=hoy)
        elif cuando == 'proximas':
            citas = citas.filter(fecha__gte=hoy, estado='programada')
        elif cuando == 'pasadas':
            citas = citas.filter(fecha__lt=hoy).order_by('-fecha', '-hora')
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


@login_required
@permission_required('mascotas.change_cita', raise_exception=True)
@require_POST
def cancelar_cita(request, pk):
    """
    Cancela una cita sin borrarla (JO2), así queda en el historial de la mascota.
    Solo se puede cancelar una cita programada o en curso. Solo acepta POST (CSRF).
    """
    cita = get_object_or_404(filtrar_por_dueno(Cita.objects.all(), request.user), pk=pk)
    if cita.estado not in ('programada', 'en_curso'):
        messages.warning(
            request, f'La cita ya está {cita.get_estado_display().lower()}; no se puede cancelar.'
        )
    else:
        cita.estado = 'cancelada'
        try:
            cita.save(update_fields=['estado'])
        except DatabaseError:
            logger.exception('Error al cancelar cita %s', pk)
            messages.error(request, 'No se pudo cancelar la cita. ' + ERROR_BD)
        else:
            messages.success(
                request, f'Se canceló la cita de "{cita.mascota.nombre}" del {cita.fecha:%d/%m/%Y}.'
            )
    siguiente = request.POST.get('next', '')
    if siguiente.startswith('/') and not siguiente.startswith('//'):
        return redirect(siguiente)
    return redirect('mascotas:lista_citas')


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
                # Al registrar una vacuna, la mascota pasa a estar vacunada.
                if not vacuna.mascota.vacunado:
                    vacuna.mascota.vacunado = True
                    vacuna.mascota.save(update_fields=['vacunado'])
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


# ────────────────────────────────────────────────────────────────────────────────
# Alertas de vacunación y carnet PDF (JO3)
# ────────────────────────────────────────────────────────────────────────────────

@login_required
@permission_required('mascotas.view_vacuna', raise_exception=True)
def alertas_vacunas(request):
    """
    Refuerzos vencidos o por vencer y mascotas pendientes sin ninguna vacuna.
    Un cliente solo ve las alertas de sus mascotas.
    """
    contexto = {'vencidas': [], 'proximas': [], 'sin_vacunas': [], 'dias_aviso': DIAS_AVISO_VACUNA}
    try:
        pendientes = vacunas_con_refuerzo_pendiente(
            queryset=filtrar_por_dueno(Vacuna.objects.all(), request.user)
        )
        for vacuna in pendientes:
            clave = 'vencidas' if vacuna.estado_dosis == 'vencida' else 'proximas'
            contexto[clave].append(vacuna)
        contexto['sin_vacunas'] = list(mascotas_sin_vacunas(
            filtrar_por_dueno(Mascota.objects.all(), request.user, ruta='dueno__user')
        ))
    except DatabaseError:
        logger.exception('Error al calcular alertas de vacunas')
        messages.error(request, 'No se pudieron calcular las alertas. ' + ERROR_BD)
    return render(request, 'mascotas/alertas_vacunas.html', contexto)


@login_required
@permission_required('mascotas.manage_vacunas', raise_exception=True)
@require_POST
def enviar_alertas_vacunas(request):
    """Envía los recordatorios por correo desde la web (mismo código que el comando)."""
    try:
        resumen = enviar_recordatorios()
    except DatabaseError:
        logger.exception('Error al enviar recordatorios')
        messages.error(request, 'No se pudieron enviar los recordatorios. ' + ERROR_BD)
        return redirect('mascotas:alertas_vacunas')
    texto = f"Recordatorios enviados: {resumen['enviados']}."
    if resumen['ya_avisados']:
        texto += f" {resumen['ya_avisados']} ya habían sido avisados."
    if resumen['sin_correo']:
        texto += f" {resumen['sin_correo']} dueño(s) sin correo registrado."
    messages.success(request, texto)
    if resumen['errores']:
        messages.error(
            request,
            f"{resumen['errores']} correo(s) no se pudieron enviar. Revisa la configuración de correo en .env.",
        )
    return redirect('mascotas:alertas_vacunas')


@login_required
def carnet_vacunas(request, pk):
    """Descarga el carnet de vacunación de una mascota en PDF."""
    mascota = get_object_or_404(
        filtrar_por_dueno(Mascota.objects.select_related('dueno'), request.user, ruta='dueno__user'),
        pk=pk,
    )
    try:
        pdf = carnet_vacunas_pdf(mascota)
    except DatabaseError:
        logger.exception('Error al generar el carnet de la mascota %s', pk)
        messages.error(request, 'No se pudo generar el carnet. ' + ERROR_BD)
        return redirect('mascotas:ficha', pk=pk)
    respuesta = HttpResponse(pdf, content_type='application/pdf')
    nombre = slugify(mascota.nombre) or 'mascota'
    respuesta['Content-Disposition'] = f'attachment; filename="carnet-vacunas-{nombre}.pdf"'
    return respuesta


# ────────────────────────────────────────────────────────────────────────────────
# Facturación (JO4)
# ────────────────────────────────────────────────────────────────────────────────

def _facturas_visibles(user):
    return filtrar_por_dueno(
        Factura.objects.select_related('dueno', 'mascota').prefetch_related('detalles'),
        user, ruta='dueno__user',
    )


@login_required
@permission_required('mascotas.view_factura', raise_exception=True)
def listar_facturas(request):
    """Facturas con filtros por dueño/mascota, estado y mes (AAAA-MM)."""
    query = request.GET.get('q', '').strip()[:100]
    estado = request.GET.get('estado', '').strip()
    mes = request.GET.get('mes', '').strip()[:7]
    contexto = {
        'facturas': [], 'query': query, 'estado_seleccionado': estado, 'mes': mes,
        'estados': Factura.ESTADO_CHOICES, 'total_pendiente': 0, 'total_pagado': 0,
    }
    try:
        facturas = _facturas_visibles(request.user)
        if query:
            facturas = facturas.filter(Q(dueno__nombre__icontains=query) | Q(mascota__nombre__icontains=query))
        if estado:
            facturas = facturas.filter(estado=estado)
        if len(mes) == 7 and mes[4] == '-' and mes.replace('-', '').isdigit():
            facturas = facturas.filter(fecha__year=int(mes[:4]), fecha__month=int(mes[5:]))
        facturas = list(facturas)
        contexto['facturas'] = facturas
        contexto['total_pendiente'] = sum(f.total for f in facturas if f.estado == 'pendiente')
        contexto['total_pagado'] = sum(f.total for f in facturas if f.estado == 'pagada')
    except DatabaseError:
        logger.exception('Error al listar facturas')
        messages.error(request, 'No se pudieron cargar las facturas. ' + ERROR_BD)
    return render(request, 'mascotas/factura_list.html', contexto)


@login_required
@permission_required('mascotas.view_factura', raise_exception=True)
def detalle_factura(request, pk):
    factura = get_object_or_404(_facturas_visibles(request.user), pk=pk)
    return render(request, 'mascotas/factura_detalle.html', {'factura': factura})


def _guardar_factura(request, factura=None):
    """
    Guarda la factura y sus líneas juntas. Se usa transaction.atomic: si falla
    una línea, no queda una factura a medias en la base de datos.
    """
    if factura and factura.estado == 'anulada':
        messages.warning(request, 'Una factura anulada no se puede modificar.')
        return redirect('mascotas:detalle_factura', pk=factura.pk)

    if request.method == 'POST':
        form = FacturaForm(request.POST, instance=factura)
        formset = DetalleFacturaFormSet(request.POST, instance=form.instance)
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    factura = form.save()
                    formset.instance = factura
                    formset.save()
            except DatabaseError:
                logger.exception('Error al guardar factura')
                messages.error(request, 'No se pudo guardar la factura. ' + ERROR_BD)
            else:
                messages.success(request, f'Factura {factura.numero} guardada. Total: {formato_clp(factura.total)}.')
                return redirect('mascotas:detalle_factura', pk=factura.pk)
        else:
            messages.warning(request, 'Revisa los campos marcados en rojo.')
    else:
        initial = {}
        mascota_id = request.GET.get('mascota', '')
        if not factura and mascota_id.isdigit():
            mascota = Mascota.objects.filter(pk=mascota_id).first()
            if mascota:
                initial = {'mascota': mascota.pk, 'dueno': mascota.dueno_id}
        form = FacturaForm(instance=factura, initial=initial)
        formset = DetalleFacturaFormSet(instance=factura or Factura())
    return render(request, 'mascotas/factura_form.html', {
        'form': form, 'formset': formset, 'object': factura,
    })


@login_required
@permission_required('mascotas.add_factura', raise_exception=True)
def crear_factura(request):
    return _guardar_factura(request)


@login_required
@permission_required('mascotas.change_factura', raise_exception=True)
def editar_factura(request, pk):
    return _guardar_factura(request, get_object_or_404(Factura, pk=pk))


@login_required
@permission_required('mascotas.change_factura', raise_exception=True)
@require_POST
def cambiar_estado_factura(request, pk):
    """Marca como pagada (con método de pago) o anula una factura pendiente."""
    factura = get_object_or_404(Factura, pk=pk)
    accion = request.POST.get('accion')
    if factura.estado != 'pendiente':
        messages.warning(request, f'La factura ya está {factura.get_estado_display().lower()}.')
        return redirect('mascotas:detalle_factura', pk=pk)
    if accion == 'pagar':
        metodo = request.POST.get('metodo_pago', '')
        if metodo not in dict(Factura.METODO_PAGO_CHOICES):
            messages.error(request, 'Elige un método de pago válido.')
            return redirect('mascotas:detalle_factura', pk=pk)
        factura.estado, factura.metodo_pago, factura.fecha_pago = 'pagada', metodo, timezone.localdate()
    elif accion == 'anular':
        factura.estado = 'anulada'
    else:
        messages.error(request, 'Acción no válida.')
        return redirect('mascotas:detalle_factura', pk=pk)
    try:
        factura.save(update_fields=['estado', 'metodo_pago', 'fecha_pago'])
    except DatabaseError:
        logger.exception('Error al cambiar estado de la factura %s', pk)
        messages.error(request, 'No se pudo actualizar la factura. ' + ERROR_BD)
    else:
        messages.success(request, f'Factura {factura.numero}: {factura.get_estado_display().lower()}.')
    return redirect('mascotas:detalle_factura', pk=pk)


@login_required
@permission_required('mascotas.delete_factura', raise_exception=True)
def eliminar_factura(request, pk):
    """Solo se pueden borrar facturas anuladas; las demás deben anularse primero."""
    factura = get_object_or_404(Factura, pk=pk)
    if factura.estado != 'anulada':
        messages.warning(request, 'Primero anula la factura; solo se eliminan facturas anuladas.')
        return redirect('mascotas:detalle_factura', pk=pk)
    return _confirmar_eliminacion(
        request, factura, 'mascotas/factura_confirm_delete.html', 'mascotas:lista_facturas',
        f'la factura {factura.numero}',
    )


# ────────────────────────────────────────────────────────────────────────────────
# Dashboard y reportes (JO5)
# ────────────────────────────────────────────────────────────────────────────────

MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def _ultimos_meses(hoy, cantidad=6):
    """[(año, mes), ...] de los últimos `cantidad` meses, del más antiguo al actual."""
    meses = []
    anio, mes = hoy.year, hoy.month
    for _ in range(cantidad):
        meses.append((anio, mes))
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    return list(reversed(meses))


def _con_porcentaje(filas, clave='total'):
    """Agrega 'porcentaje' a cada fila (respecto del mayor) para dibujar barras."""
    maximo = max((fila[clave] for fila in filas), default=0) or 1
    for fila in filas:
        fila['porcentaje'] = round(fila[clave] * 100 / maximo)
    return filas


@login_required
def dashboard(request):
    """
    Panel de inicio con los números clave de la clínica. Cada bloque respeta
    los permisos: un cliente ve solo lo de sus mascotas y la facturación solo
    aparece a quien tiene permiso para ver facturas.
    """
    user = request.user
    hoy = timezone.localdate()
    contexto = {'hoy': hoy}
    try:
        mascotas = filtrar_por_dueno(Mascota.objects.all(), user, ruta='dueno__user')
        contexto['total_mascotas'] = mascotas.count()
        contexto['pendientes_vacuna'] = mascotas.filter(vacunado=False, alergico=False).count()
        contexto['por_especie'] = _con_porcentaje(list(
            mascotas.values('especie').annotate(total=Count('id')).order_by('-total', 'especie')
        ))
        contexto['por_estado'] = [
            {'clave': 'al_dia', 'nombre': 'Al día', 'total': mascotas.filter(vacunado=True, alergico=False).count()},
            {'clave': 'pendiente', 'nombre': 'Pendiente', 'total': contexto['pendientes_vacuna']},
            {'clave': 'alergia', 'nombre': 'Alergia', 'total': mascotas.filter(alergico=True).count()},
        ]
        _con_porcentaje(contexto['por_estado'])

        if user.has_perm('mascotas.view_cita'):
            citas = filtrar_por_dueno(Cita.objects.select_related('mascota'), user)
            contexto['citas_hoy'] = list(citas.filter(fecha=hoy).exclude(estado='cancelada').order_by('hora'))
            contexto['citas_proximas'] = citas.filter(fecha__gt=hoy, estado='programada').count()

        if user.has_perm('mascotas.view_vacuna'):
            refuerzos = list(vacunas_con_refuerzo_pendiente(
                queryset=filtrar_por_dueno(Vacuna.objects.all(), user)
            ))
            contexto['refuerzos_vencidos'] = sum(1 for v in refuerzos if v.estado_dosis == 'vencida')
            contexto['refuerzos_proximos'] = len(refuerzos) - contexto['refuerzos_vencidos']

        if user.has_perm('mascotas.view_factura'):
            meses = _ultimos_meses(hoy)
            desde = date(meses[0][0], meses[0][1], 1)
            facturas = list(
                filtrar_por_dueno(Factura.objects.prefetch_related('detalles'), user, ruta='dueno__user')
                .filter(fecha__gte=desde).exclude(estado='anulada')
            )
            ingresos = {m: 0 for m in meses}
            for factura in facturas:
                if factura.estado == 'pagada':
                    ingresos[(factura.fecha.year, factura.fecha.month)] += factura.total
            contexto['ingresos'] = _con_porcentaje([
                {'etiqueta': f'{MESES[m - 1]} {str(a)[2:]}', 'total': ingresos[(a, m)]} for a, m in meses
            ])
            contexto['ingreso_mes'] = ingresos[(hoy.year, hoy.month)]
            contexto['por_cobrar'] = sum(
                f.total for f in filtrar_por_dueno(
                    Factura.objects.filter(estado='pendiente').prefetch_related('detalles'),
                    user, ruta='dueno__user',
                )
            )
    except DatabaseError:
        logger.exception('Error al cargar el dashboard')
        messages.error(request, 'No se pudieron cargar los indicadores. ' + ERROR_BD)
    return render(request, 'mascotas/dashboard.html', contexto)


def _respuesta_csv(nombre_archivo, encabezados, filas):
    """
    CSV listo para abrir en Excel: separador ';' (Excel en español) y BOM
    UTF-8 para que las tildes y la ñ se vean bien.
    """
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    respuesta.write('\ufeff')
    escritor = csv.writer(respuesta, delimiter=';')
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    return respuesta


@login_required
def reporte_mascotas_csv(request):
    """Exporta las mascotas con los mismos filtros de la lista (q, especie, estado)."""
    query = request.GET.get('q', '').strip()[:100]
    especie = request.GET.get('especie', '').strip()[:50]
    estado = request.GET.get('estado', '').strip()
    try:
        mascotas = filtrar_por_dueno(
            Mascota.objects.select_related('dueno').annotate(
                total_vacunas=Count('vacunas', distinct=True), total_citas=Count('citas', distinct=True),
            ),
            request.user, ruta='dueno__user',
        )
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
        estados = {'al_dia': 'Al día', 'pendiente': 'Pendiente', 'alergia': 'Alergia'}
        filas = [
            [m.nombre, m.especie, m.raza or '', m.edad, estados[m.estado_vacunacion],
             m.dueno.nombre if m.dueno else '', (m.dueno.email or '') if m.dueno else '',
             m.total_vacunas, m.total_citas]
            for m in mascotas
        ]
    except DatabaseError:
        logger.exception('Error al exportar mascotas')
        messages.error(request, 'No se pudo generar el reporte. ' + ERROR_BD)
        return redirect('mascotas:lista')
    return _respuesta_csv(
        f'mascotas-{timezone.localdate():%Y-%m-%d}.csv',
        ['Nombre', 'Especie', 'Raza', 'Edad', 'Vacunación', 'Dueño', 'Correo dueño', 'Vacunas', 'Citas'],
        filas,
    )


@login_required
@permission_required('mascotas.view_factura', raise_exception=True)
def reporte_facturas_csv(request):
    """Exporta las facturas del mes indicado (?mes=AAAA-MM) o todas si no se indica."""
    mes = request.GET.get('mes', '').strip()[:7]
    try:
        facturas = _facturas_visibles(request.user)
        if len(mes) == 7 and mes[4] == '-' and mes.replace('-', '').isdigit():
            facturas = facturas.filter(fecha__year=int(mes[:4]), fecha__month=int(mes[5:]))
        filas = [
            [f.numero, f.fecha.strftime('%d/%m/%Y'), f.dueno.nombre, f.mascota.nombre if f.mascota else '',
             f.get_estado_display(), f.get_metodo_pago_display(), f.neto, f.iva, f.total]
            for f in facturas
        ]
    except DatabaseError:
        logger.exception('Error al exportar facturas')
        messages.error(request, 'No se pudo generar el reporte. ' + ERROR_BD)
        return redirect('mascotas:lista_facturas')
    return _respuesta_csv(
        f'facturas-{mes or "todas"}.csv',
        ['Número', 'Fecha', 'Dueño', 'Mascota', 'Estado', 'Método de pago', 'Neto', 'IVA', 'Total'],
        filas,
    )

