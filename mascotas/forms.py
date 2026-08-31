from django import forms

from .models import Mascota


class MascotaForm(forms.ModelForm):
    """Formulario para crear y editar mascotas desde la interfaz web."""

    class Meta:
        model = Mascota
        fields = ['nombre', 'especie', 'edad', 'vacunado', 'alergico']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Firulais',
            }),
            'especie': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Perro, Gato, Conejo, Loro...',
            }),
            'edad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
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
