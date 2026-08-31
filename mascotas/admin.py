from django.contrib import admin

from .models import Mascota


@admin.register(Mascota)
class MascotaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'especie', 'edad', 'vacunado', 'alergico')
    list_filter = ('especie', 'vacunado', 'alergico')
    search_fields = ('nombre',)
    ordering = ('nombre',)
