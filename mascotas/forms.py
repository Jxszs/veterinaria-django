from django import forms
from django.utils.html import strip_tags
import re

from .models import Mascota

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