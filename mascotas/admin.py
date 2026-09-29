from django.contrib import admin

from .models import Mascota, Cita, HistorialMedico, Vacuna


@admin.register(Mascota)
class MascotaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'especie', 'edad', 'dueno', 'vacunado', 'alergico')
    list_filter = ('especie', 'vacunado', 'alergico')
    search_fields = ('nombre',)
    ordering = ('nombre',)

    def get_queryset(self, request):
        """Filtrar por dueño: solo superusuario ve todas, los demás solo sus mascotas."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'duenos'):
            return qs.filter(dueno__user=request.user)
        return qs.none()


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('mascota', 'veterinario', 'fecha', 'hora', 'estado')
    list_filter = ('estado', 'fecha', 'veterinario')
    search_fields = ('mascota__nombre', 'veterinario')
    ordering = ('-fecha', '-hora')
    date_hierarchy = 'fecha'

    def get_queryset(self, request):
        """Filtrar por dueño: solo superusuario ve todas, los demás solo sus citas."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'duenos'):
            return qs.filter(mascota__dueno__user=request.user)
        return qs.none()


@admin.register(HistorialMedico)
class HistorialMedicoAdmin(admin.ModelAdmin):
    list_display = ('mascota', 'fecha', 'diagnostico', 'veterinario')
    list_filter = ('fecha', 'veterinario')
    search_fields = ('mascota__nombre', 'diagnostico', 'veterinario')
    ordering = ('-fecha',)
    date_hierarchy = 'fecha'

    def get_queryset(self, request):
        """Filtrar por dueño: solo superusuario ve todas, los demás solo su historial."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'duenos'):
            return qs.filter(mascota__dueno__user=request.user)
        return qs.none()


@admin.register(Vacuna)
class VacunaAdmin(admin.ModelAdmin):
    list_display = ('mascota', 'tipo', 'fecha_aplicacion', 'proxima_dosis', 'fabricante')
    list_filter = ('tipo', 'fecha_aplicacion', 'fabricante')
    search_fields = ('mascota__nombre', 'lote', 'fabricante')
    ordering = ('-fecha_aplicacion',)
    date_hierarchy = 'fecha_aplicacion'

    def get_queryset(self, request):
        """Filtrar por dueño: solo superusuario ve todas, los demás solo sus vacunas."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'duenos'):
            return qs.filter(mascota__dueno__user=request.user)
        return qs.none()
