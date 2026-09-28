from django.contrib import admin
from django.contrib.admin.actions import delete_selected

from .models import Mascota, Cita, HistorialMedico, Vacuna


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
class MascotaAdmin(admin.ModelAdmin):
    # ── Listado ──
    list_display = (
        'nombre', 'especie', 'edad', 'dueno', 'vacunado',
        'alergico', 'estado_vacunacion',
    )
    list_filter = ('especie', 'vacunado', 'alergico', 'dueno')
    search_fields = ('nombre', 'dueno__user__username', 'dueno__nombre')
    ordering = ('nombre',)
    date_hierarchy = None  # no aplica para Mascota (no tiene fecha)

    # ── Formulario de edición ──
    fieldsets = (
        ('Datos principales', {
            'fields': ('nombre', 'especie', 'edad', 'raza')
        }),
        ('Dueño', {
            'fields': ('dueno',),
            'description': 'Dueño registrado del sistema. Deja vacío para mascotas sin dueño asignado.',
        }),
        ('Estado de vacunación', {
            'fields': ('vacunado', 'alergico'),
            'classes': ('collapse',),
            'description': 'Marcar si la mascota está vacunada o es alérgica a las vacunas.',
        }),
    )
    readonly_fields = ('estado_vacunacion',)

    # ── Relaciones (inlines) ──
    inlines = [CitaInline, HistorialMedicoInline, VacunaInline]

    # ── Acciones masivas ──
    actions = [marcar_como_vacunadas, marcar_como_no_vacunadas, delete_selected]


# ────────────────────────────────────────────────────────────────────────────────
# Admin de Cita
# ────────────────────────────────────────────────────────────────────────────────

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('mascota', 'veterinario', 'fecha', 'hora', 'estado', 'motivo')
    list_filter = ('estado', 'fecha', 'veterinario')
    search_fields = ('mascota__nombre', 'veterinario')
    ordering = ('-fecha', '-hora')
    date_hierarchy = 'fecha'

    fieldsets = (
        ('Datos de la cita', {
            'fields': ('mascota', 'veterinario', 'fecha', 'hora'),
        }),
        ('Motivo y estado', {
            'fields': ('motivo', 'estado'),
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',),
        }),
    )


# ────────────────────────────────────────────────────────────────────────────────
# Admin de HistorialMedico
# ────────────────────────────────────────────────────────────────────────────────

@admin.register(HistorialMedico)
class HistorialMedicoAdmin(admin.ModelAdmin):
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
class VacunaAdmin(admin.ModelAdmin):
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

    readonly_fields = ('fecha_aplicacion',)