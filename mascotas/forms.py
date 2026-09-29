from django import forms
from django.utils.html import strip_tags
import re

from .models import Mascota, Cita, HistorialMedico, Vacuna

# Solo letras (con tildes y ñ), espacios, guiones y apóstrofes.
SOLO_LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' -]+$")


def limpiar_texto(valor):
    """Sanitiza el texto: quita etiquetas HTML y espacios de sobra."""
    valor = strip_tags(valor or '')
    return ' '.join(valor.split())


class MascotaForm(forms.ModelForm):
    """Formulario para crear y editar mascotas desde la interfaz web."""

    class Meta:
        model = Mascota
        fields = ['nombre', 'especie', 'edad', 'vacunado', 'alergico']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Firulais',
                'maxlength': 100,
            }),
            'especie': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Perro, Gato, Conejo, Loro...',
                'maxlength': 50,
            }),
            'edad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 40,
            }),
            'vacunado': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'alergico': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        labels = {
            'nombre': 'Nombre de la mascota',
            'especie': 'Especie',
            'edad': 'Edad (años)',
            'vacunado': '¿Está vacunado?',
            'alergico': '¿Es alérgico a las vacunas?',
        }
        error_messages = {
            'nombre': {'required': 'Debes ingresar el nombre de la mascota.'},
            'especie': {'required': 'Debes ingresar la especie.'},
            'edad': {
                'required': 'Debes ingresar la edad.',
                'invalid': 'La edad debe ser un número entero.',
            },
        }

    def clean_nombre(self):
        nombre = limpiar_texto(self.cleaned_data.get('nombre'))
        if len(nombre) < 2:
            raise forms.ValidationError('El nombre debe tener al menos 2 letras.')
        if not SOLO_LETRAS.match(nombre):
            raise forms.ValidationError('El nombre solo puede contener letras y espacios.')
        return nombre.title()

    def clean_especie(self):
        especie = limpiar_texto(self.cleaned_data.get('especie'))
        if len(especie) < 3:
            raise forms.ValidationError('La especie debe tener al menos 3 letras.')
        if not SOLO_LETRAS.match(especie):
            raise forms.ValidationError('La especie solo puede contener letras y espacios.')
        # "perro", "PERRO" y "Perro" quedan igual, así el filtro no se duplica.
        return especie.capitalize()


class CitaForm(forms.ModelForm):
    """Formulario para crear y editar citas."""

    class Meta:
        model = Cita
        fields = ['mascota', 'veterinario', 'fecha', 'hora', 'motivo', 'estado']
        widgets = {
            'mascota': forms.Select(attrs={'class': 'form-select'}),
            'veterinario': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Dr. Pérez',
            }),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'hora': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }),
            'motivo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Chequeo anual, vacunación...',
            }),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'mascota': 'Mascota',
            'veterinario': 'Veterinario a cargo',
            'fecha': 'Fecha',
            'hora': 'Hora',
            'motivo': 'Motivo',
            'estado': 'Estado',
        }


class HistorialMedicoForm(forms.ModelForm):
    """Formulario para registrar historial médico."""

    class Meta:
        model = HistorialMedico
        fields = ['mascota', 'fecha', 'diagnostico', 'tratamiento', 'veterinario', 'notas']
        widgets = {
            'mascota': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'diagnostico': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Diagnóstico principal',
            }),
            'tratamiento': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Tratamiento indicado',
            }),
            'veterinario': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dr. apellido',
            }),
            'notas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notas adicionales (opcional)',
            }),
        }
        labels = {
            'mascota': 'Mascota',
            'fecha': 'Fecha del registro',
            'diagnostico': 'Diagnóstico',
            'tratamiento': 'Tratamiento',
            'veterinario': 'Veterinario',
            'notas': 'Notas',
        }


class VacunaForm(forms.ModelForm):
    """Formulario para registrar vacunación."""

    class Meta:
        model = Vacuna
        fields = ['mascota', 'tipo', 'fecha_aplicacion', 'proxima_dosis', 'lote', 'fabricante', 'observaciones']
        widgets = {
            'mascota': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'fecha_aplicacion': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'proxima_dosis': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'lote': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: L-2024-001',
            }),
            'fabricante': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Intervet, Boehringer...',
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones (opcional)',
            }),
        }
        labels = {
            'mascota': 'Mascota',
            'tipo': 'Tipo de vacuna',
            'fecha_aplicacion': 'Fecha de aplicación',
            'proxima_dosis': 'Próxima dosis',
            'lote': 'Nº de lote',
            'fabricante': 'Fabricante',
            'observaciones': 'Observaciones',
        }