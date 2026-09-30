from django.contrib import admin
from django.utils.html import format_html
from django.contrib.admin.actions import delete_selected

from .templatetags.veterinaria_extras import formato_clp
from .models import (
    Cita, DetalleFactura, Dueño, Factura, HistorialMedico, Mascota, Producto,
    Receta, Vacuna,
)
from .permisos import filtrar_por_dueno


# ────────────────────────────────────────────────────────────────────────────────
# Filtrado por dueño (GA2): misma regla que la web (mascotas/permisos.py)
# ────────────────────────────────────────────────────────────────────────────────

class FiltradoPorDuenoMixin:
    """
    Aplica en el admin la misma regla de la interfaz web: el personal ve todo
    y un cliente con acceso al admin ve solo lo suyo.
    Antes se usaba hasattr(user, 'duenos'), que siempre es True, y dejaba a los
    veterinarios sin ver ningún registro.
    `ruta_dueno` indica cómo llegar desde el modelo al User del dueño.
    """
    ruta_dueno = 'mascota__dueno__user'

    def get_queryset(self, request):
        return filtrar_por_dueno(super().get_queryset(request), request.user, ruta=self.ruta_dueno)


# ────────────────────────────────────────────────────────────────────────────────
# Inlines: ver/editar modelos relacionados dentro del admin de Mascota
# ────────────────────────────────────────────────────────────────────────────────

class CitaInline(admin.TabularInline):
    """Citás de la mascota — se ven y se pueden agregar desde el admin de Mascota."""
    model = Cita
    extra = 1
    fieldsets = (
        (None, {'fields': ('veterinario', 'fecha', 'hora', 'motivo', 'estado')}),
    )
    ordering = ('fecha', 'hora')


class HistorialMedicoInline(admin.TabularInline):
    """Histórico médico de la mascota — se ve y se puede registrar desde el admin de Mascota."""
    model = HistorialMedico
    extra = 1
    fieldsets = (
        (None, {'fields': ('fecha', 'diagnostico', 'tratamiento', 'veterinario', 'notas')}),
    )
    ordering = ('-fecha',)


class VacunaInline(admin.TabularInline):
    """Vacunas de la mascota — se ven y se pueden registrar desde el admin de Mascota."""
    model = Vacuna
    extra = 1
    fieldsets = (
        (None, {'fields': ('tipo', 'fecha_aplicacion', 'proxima_dosis', 'lote', 'fabricante', 'observaciones')}),
    )
    ordering = ('-fecha_aplicacion',)


class RecetaInline(admin.TabularInline):
    """
    Recetas indicadas en las citas de una mascota.

    Solo funciona colgado del admin de Cita (la receta cuelga de la cita, no
    de la mascota), así que aquí solo se declara la clase.
    """
    model = Receta
    extra = 1
    fields = ('medicamento', 'dosis', 'duracion_dias', 'fecha')
    ordering = ('-fecha',)
    verbose_name = 'Receta'
    verbose_name_plural = 'Recetas'


# ────────────────────────────────────────────────────────────────────────────────
# Acción personalizada: marcar varias mascotas como vacunadas a la vez
# ────────────────────────────────────────────────────────────────────────────────

@admin.action(description='Marcar seleccionadas como vacunadas')
def marcar_como_vacunadas(modeladmin, request, queryset):
    """Acción masiva: marcar como vacunadas las mascotas seleccionadas en el admin."""
    count = queryset.update(vacunado=True)
    if count == 1:
        msg = '1 mascota marcada como vacunada.'
    else:
        msg = f'{count} mascotas marcadas como vacunadas.'
    modeladmin.message_user(request, msg)


@admin.action(description='Marcar seleccionadas como no vacunadas')
def marcar_como_no_vacunadas(modeladmin, request, queryset):
    """Acción masiva: marcar como no vacunadas las mascotas seleccionadas en el admin."""
    count = queryset.update(vacunado=False)
    if count == 1:
        msg = '1 mascota marcada como no vacunada.'
    else:
        msg = f'{count} mascotas marcadas como no vacunadas.'
    modeladmin.message_user(request, msg)


# ────────────────────────────────────────────────────────────────────────────────
# Admin de Mascota — con todas las técnicas avanzadas de Gabriel
# ────────────────────────────────────────────────────────────────────────────────

@admin.register(Mascota)
class MascotaAdmin(FiltradoPorDuenoMixin, admin.ModelAdmin):
    ruta_dueno = 'dueno__user'

    # ── Listado ──
    # proxima_vacuna y ultima_cita son las columnas de seguimiento que pide
    # el enunciado: muestran de un vistazo qué falta por renovar.
    list_display = (
        'nombre', 'especie', 'raza', 'sexo', 'estado', 'dueno', 'edad_calculada',
        'proxima_vacuna', 'ultima_cita', 'estado_vacunacion',
    )
    list_filter = ('especie', 'sexo', 'estado', 'vacunado', 'alergico', 'dueno')
    search_fields = ('nombre', 'raza', 'dueno__user__username', 'dueno__nombre')
    ordering = ('nombre',)

    # ── Formulario de edición ──
    fieldsets = (
        ('Datos principales', {
            'fields': ('nombre', 'especie', 'raza', 'sexo', 'foto')
        }),
        ('Edad y peso', {
            'fields': ('edad', 'fecha_nacimiento', 'peso'),
            'description': 'Si informas la fecha de nacimiento, la edad se calcula sola.',
        }),
        ('Dueño', {
            'fields': ('dueno',),
            'description': 'Dueño registrado del sistema. Deja vacío para mascotas sin dueño asignado.',
        }),
        ('Estado', {
            'fields': ('estado', 'vacunado', 'alergico'),
            'classes': ('collapse',),
            'description': 'Estado general de la mascota y su situación con las vacunas.',
        }),
        ('Seguimiento', {
            'fields': ('proxima_vacuna', 'ultima_cita'),
            'classes': ('collapse', 'readonly'),
            'description': 'Se calculan solos a partir de las vacunas y citas registradas.',
        }),
    )
    readonly_fields = ('estado_vacunacion', 'proxima_vacuna', 'ultima_cita', 'edad_calculada')

    # ── Relaciones (inlines) ──
    inlines = [CitaInline, HistorialMedicoInline, VacunaInline]

    # ── Acciones masivas ──
    actions = [marcar_como_vacunadas, marcar_como_no_vacunadas, delete_selected]


# ────────────────────────────────────────────────────────────────────────────────
# Admin de Cita
# ────────────────────────────────────────────────────────────────────────────────

@admin.register(Cita)
class CitaAdmin(FiltradoPorDuenoMixin, admin.ModelAdmin):
    list_display = ('mascota', 'veterinario', 'fecha', 'hora', 'estado', 'motivo', 'duracion')
    list_filter = ('estado', 'fecha', 'veterinario')
    # También lo usa el autocompletado de citas en el admin de Receta.
    search_fields = ('mascota__nombre', 'veterinario', 'motivo')
    ordering = ('-fecha', '-hora')
    date_hierarchy = 'fecha'

    fieldsets = (
        ('Datos de la cita', {
            'fields': ('mascota', 'veterinario', 'fecha', 'hora', 'duracion'),
        }),
        ('Motivo y estado', {
            'fields': ('motivo', 'estado'),
        }),
        ('Observaciones', {
            'fields': ('observaciones', 'alerta_enviada_el'),
            'classes': ('collapse',),
        }),
    )
    # Las recetas se indican y editan desde la propia cita.
    inlines = [RecetaInline]


# ────────────────────────────────────────────────────────────────────────────────
# Admin de HistorialMedico
# ────────────────────────────────────────────────────────────────────────────────

@admin.register(HistorialMedico)
class HistorialMedicoAdmin(FiltradoPorDuenoMixin, admin.ModelAdmin):
    list_display = ('mascota', 'fecha', 'diagnostico', 'veterinario', 'tratamiento_resumido')
    list_filter = ('fecha', 'veterinario')
    search_fields = ('mascota__nombre', 'diagnostico', 'veterinario')
    ordering = ('-fecha',)
    date_hierarchy = 'fecha'

    fieldsets = (
        ('Datos del registro', {
            'fields': ('mascota', 'fecha', 'veterinario'),
        }),
        ('Diagnóstico y tratamiento', {
            'fields': ('diagnostico', 'tratamiento'),
        }),
        ('Notas adicionales', {
            'fields': ('notas',),
            'classes': ('collapse',),
        }),
    )

    def tratamiento_resumido(self, obj):
        if obj.tratamiento:
            return obj.tratamiento[:50] + ('...' if len(obj.tratamiento) > 50 else '')
        return '—'
    tratamiento_resumido.short_description = 'Tratamiento'
    tratamiento_resumido.admin_order_field = 'tratamiento'


# ────────────────────────────────────────────────────────────────────────────────
# Admin de Vacuna
# ────────────────────────────────────────────────────────────────────────────────

@admin.register(Vacuna)
class VacunaAdmin(FiltradoPorDuenoMixin, admin.ModelAdmin):
    list_display = ('mascota', 'tipo', 'fecha_aplicacion', 'proxima_dosis', 'fabricante', 'lote')
    list_filter = ('tipo', 'fecha_aplicacion', 'fabricante')
    search_fields = ('mascota__nombre', 'lote', 'fabricante')
    ordering = ('-fecha_aplicacion',)
    date_hierarchy = 'fecha_aplicacion'

    fieldsets = (
        ('Datos de la vacuna', {
            'fields': ('mascota', 'tipo', 'fecha_aplicacion'),
        }),
        ('Dosis siguiente y lote', {
            'fields': ('proxima_dosis', 'lote', 'fabricante'),
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        # La fecha de aplicación se fija al crear; después no se modifica.
        # (Antes era readonly siempre y no dejaba crear vacunas desde el admin.)
        return ('fecha_aplicacion',) if obj else ()


# ────────────────────────────────────────────────────────────────────────────────
# Admin de Factura (JO4) — con sus líneas de detalle en la misma pantalla
# ────────────────────────────────────────────────────────────────────────────────

class DetalleFacturaInline(admin.TabularInline):
    model = DetalleFactura
    extra = 1
    min_num = 1


@admin.register(Factura)
class FacturaAdmin(FiltradoPorDuenoMixin, admin.ModelAdmin):
    ruta_dueno = 'dueno__user'
    list_display = ('numero', 'fecha', 'dueno', 'mascota', 'estado', 'metodo_pago', 'total_clp')
    list_filter = ('estado', 'metodo_pago', 'fecha')
    search_fields = ('dueno__nombre', 'mascota__nombre', 'observaciones')
    date_hierarchy = 'fecha'
    ordering = ('-fecha', '-id')
    inlines = [DetalleFacturaInline]
    list_select_related = ('dueno', 'mascota')

    @admin.display(description='Total')
    def total_clp(self, obj):
        return formato_clp(obj.total)


# ────────────────────────────────────────────────────────────────────────────────
# Admin de Dueño (GA2) — no estaba registrado
# ────────────────────────────────────────────────────────────────────────────────

class MascotaDelDuenoInline(admin.TabularInline):
    model = Mascota
    fields = ('nombre', 'especie', 'raza', 'edad', 'vacunado', 'alergico')
    extra = 0
    show_change_link = True


@admin.register(Dueño)
class DuenoAdmin(FiltradoPorDuenoMixin, admin.ModelAdmin):
    ruta_dueno = 'user'
    list_display = ('nombre', 'user', 'email', 'telefono', 'whatsapp', 'cantidad_mascotas')
    search_fields = ('nombre', 'email', 'telefono', 'user__username')
    list_filter = ('user__is_active',)
    ordering = ('nombre',)
    inlines = [MascotaDelDuenoInline]
    list_select_related = ('user',)

    @admin.display(description='Mascotas')
    def cantidad_mascotas(self, obj):
        return obj.mascotas.count()


# ────────────────────────────────────────────────────────────────────────────────
# Admin de Producto (GA3) — inventario con semáforo
# ────────────────────────────────────────────────────────────────────────────────

class SemaforoFilter(admin.SimpleListFilter):
    """Filtro lateral por color del semáforo (es una propiedad, no un campo)."""
    title = 'semáforo'
    parameter_name = 'semaforo'

    def lookups(self, request, model_admin):
        return [('rojo', '🔴 Rojo'), ('amarillo', '🟡 Amarillo'), ('verde', '🟢 Verde')]

    def queryset(self, request, queryset):
        if self.value() in ('rojo', 'amarillo', 'verde'):
            ids = [p.pk for p in queryset if p.semaforo == self.value()]
            return queryset.filter(pk__in=ids)
        return queryset


@admin.action(description='Desactivar productos seleccionados')
def desactivar_productos(modeladmin, request, queryset):
    total = queryset.update(activo=False)
    modeladmin.message_user(request, f'{total} producto(s) desactivado(s).')


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('semaforo_color', 'nombre', 'categoria', 'stock', 'stock_minimo', 'unidad',
                    'precio_clp', 'fecha_vencimiento', 'activo')
    list_display_links = ('nombre',)
    list_editable = ('stock',)
    list_filter = (SemaforoFilter, 'categoria', 'activo')
    search_fields = ('nombre',)
    ordering = ('nombre',)
    actions = [desactivar_productos, delete_selected]
    fieldsets = (
        ('Producto', {'fields': ('nombre', 'categoria', 'unidad', 'activo')}),
        ('Stock y precio', {'fields': ('stock', 'stock_minimo', 'precio_venta')}),
        ('Vencimiento', {'fields': ('fecha_vencimiento',)}),
    )

    @admin.display(description='Semáforo')
    def semaforo_color(self, obj):
        colores = {'rojo': '#dc3545', 'amarillo': '#ffc107', 'verde': '#198754'}
        return format_html(
            '<span title="{}" style="display:inline-block;width:14px;height:14px;border-radius:50%;background:{}"></span> {}',
            obj.motivo_semaforo, colores[obj.semaforo], obj.motivo_semaforo,
        )

    @admin.display(description='Precio', ordering='precio_venta')
    def precio_clp(self, obj):
        return formato_clp(obj.precio_venta)


# ────────────────────────────────────────────────────────────────────────────────
# Admin de Receta
# ────────────────────────────────────────────────────────────────────────────────

@admin.register(Receta)
class RecetaAdmin(FiltradoPorDuenoMixin, admin.ModelAdmin):
    ruta_dueno = 'cita__mascota__dueno__user'
    list_display = ('medicamento', 'cita', 'mascota', 'dosis', 'duracion_dias',
                    'fecha', 'fecha_fin', 'estado_receta', 'receta_lista_el')
    list_display_links = ('medicamento',)
    list_filter = ('fecha', 'medicamento')
    search_fields = ('medicamento', 'dosis', 'cita__mascota__nombre',
                     'cita__mascota__dueno__nombre')
    ordering = ('-fecha', '-id')
    date_hierarchy = 'fecha'
    autocomplete_fields = ('cita',)
    fieldsets = (
        ('Indicación', {
            'fields': ('cita', 'medicamento', 'dosis', 'duracion_dias'),
        }),
        ('Control', {
            'fields': ('fecha', 'observaciones', 'receta_lista_el', 'fecha_fin', 'estado_receta'),
        }),
    )
    readonly_fields = ('fecha_fin', 'estado_receta', 'receta_lista_el')
    actions = [delete_selected]

    @admin.display(description='Mascota', ordering='cita__mascota__nombre')
    def mascota(self, obj):
        return obj.cita.mascota.nombre

    @admin.display(description='Termina')
    def fecha_fin(self, obj):
        return obj.fecha_fin

    @admin.display(description='Estado', boolean=True)
    def estado_receta(self, obj):
        return obj.en_curso

