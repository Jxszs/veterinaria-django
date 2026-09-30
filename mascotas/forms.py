from datetime import datetime, time

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.html import strip_tags
import re

from .models import Dueño, Mascota, Cita, HistorialMedico, Vacuna

# Solo letras (con tildes y ñ), espacios, guiones y apóstrofes.
SOLO_LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' -]+$")

# Teléfono chileno o internacional: opcional "+" y entre 8 y 15 dígitos.
TELEFONO = re.compile(r"^\+?\d{8,15}$")


def limpiar_texto(valor):
    """Sanitiza el texto: quita etiquetas HTML y espacios de sobra."""
    valor = strip_tags(valor or '')
    return ' '.join(valor.split())


class MascotaForm(forms.ModelForm):
    """Formulario para crear y editar mascotas desde la interfaz web."""

    class Meta:
        model = Mascota
        fields = ['nombre', 'especie', 'raza', 'edad', 'dueno', 'vacunado', 'alergico']
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
            'raza': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Labrador, Siamés (opcional)',
                'maxlength': 100,
            }),
            'edad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 40,
            }),
            'dueno': forms.Select(attrs={'class': 'form-select'}),
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
            'raza': 'Raza',
            'edad': 'Edad (años)',
            'dueno': 'Dueño',
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

    def clean_raza(self):
        # La raza es opcional, pero si se escribe debe ser texto válido.
        raza = limpiar_texto(self.cleaned_data.get('raza'))
        if not raza:
            return None
        if not SOLO_LETRAS.match(raza):
            raise forms.ValidationError('La raza solo puede contener letras y espacios.')
        return raza.title()


class DuenoForm(forms.ModelForm):
    """
    Formulario para registrar dueños y asociarlos a un usuario del sistema.
    Un usuario solo puede tener un perfil de dueño.
    """

    class Meta:
        model = Dueño
        fields = ['user', 'nombre', 'email', 'telefono', 'whatsapp', 'direccion']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: María González'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.cl'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: +56912345678'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: +56912345678'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle, número, comuna'}),
        }
        labels = {
            'user': 'Usuario del sistema',
            'nombre': 'Nombre completo',
            'email': 'Correo electrónico',
            'telefono': 'Teléfono',
            'whatsapp': 'WhatsApp',
            'direccion': 'Dirección',
        }
        error_messages = {
            'user': {'required': 'Debes elegir el usuario con el que el dueño inicia sesión.'},
            'nombre': {'required': 'Debes ingresar el nombre del dueño.'},
            'email': {'invalid': 'Ingresa un correo válido (ej: nombre@correo.cl).'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.order_by('username')

    def clean_user(self):
        user = self.cleaned_data.get('user')
        repetido = Dueño.objects.filter(user=user).exclude(pk=self.instance.pk)
        if user and repetido.exists():
            raise forms.ValidationError('Este usuario ya tiene un perfil de dueño registrado.')
        return user

    def clean_nombre(self):
        nombre = limpiar_texto(self.cleaned_data.get('nombre'))
        if len(nombre) < 3:
            raise forms.ValidationError('El nombre debe tener al menos 3 letras.')
        if not SOLO_LETRAS.match(nombre):
            raise forms.ValidationError('El nombre solo puede contener letras y espacios.')
        return nombre.title()

    def _limpiar_telefono(self, campo):
        valor = limpiar_texto(self.cleaned_data.get(campo)).replace(' ', '').replace('-', '')
        if not valor:
            return None
        if not TELEFONO.match(valor):
            raise forms.ValidationError('Número no válido. Usa solo dígitos (8 a 15), con "+" opcional.')
        return valor

    def clean_telefono(self):
        return self._limpiar_telefono('telefono')

    def clean_whatsapp(self):
        return self._limpiar_telefono('whatsapp')

    def clean_direccion(self):
        return limpiar_texto(self.cleaned_data.get('direccion')) or None

    def clean(self):
        datos = super().clean()
        # Sin al menos un medio de contacto, la clínica no puede avisar de vacunas ni citas.
        if not (datos.get('email') or datos.get('telefono') or datos.get('whatsapp')):
            raise forms.ValidationError('Ingresa al menos un medio de contacto: correo, teléfono o WhatsApp.')
        return datos


# Horario de atención de la clínica (usado para validar las citas).
HORA_APERTURA = time(9, 0)
HORA_CIERRE = time(20, 0)


class CitaForm(forms.ModelForm):
    """
    Formulario para programar y editar citas (JO2).

    Valida: que la cita no quede en el pasado, que esté dentro del horario de
    atención y que no choque con otra cita del mismo veterinario o de la misma
    mascota a la misma hora (las citas canceladas no cuentan).
    """

    class Meta:
        model = Cita
        fields = ['mascota', 'veterinario', 'fecha', 'hora', 'motivo', 'estado', 'observaciones']
        widgets = {
            'mascota': forms.Select(attrs={'class': 'form-select'}),
            'veterinario': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Dr. Pérez',
            }),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }, format='%Y-%m-%d'),
            'hora': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }, format='%H:%M'),
            'motivo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Chequeo anual, vacunación...',
            }),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notas del veterinario (opcional)',
            }),
        }
        labels = {
            'mascota': 'Mascota',
            'veterinario': 'Veterinario a cargo',
            'fecha': 'Fecha',
            'hora': 'Hora',
            'motivo': 'Motivo',
            'estado': 'Estado',
            'observaciones': 'Observaciones',
        }
        error_messages = {
            'mascota': {'required': 'Debes elegir la mascota.'},
            'veterinario': {'required': 'Debes indicar el veterinario a cargo.'},
            'fecha': {'required': 'Debes ingresar la fecha.', 'invalid': 'Fecha no válida.'},
            'hora': {'required': 'Debes ingresar la hora.', 'invalid': 'Hora no válida.'},
        }

    def clean_veterinario(self):
        veterinario = limpiar_texto(self.cleaned_data.get('veterinario'))
        if len(veterinario) < 3:
            raise forms.ValidationError('El nombre del veterinario debe tener al menos 3 letras.')
        # Se permite el punto de "Dr." / "Dra."
        if not SOLO_LETRAS.match(veterinario.replace('.', '')):
            raise forms.ValidationError('El veterinario solo puede contener letras, espacios y puntos.')
        return veterinario

    def clean_motivo(self):
        return limpiar_texto(self.cleaned_data.get('motivo')) or None

    def clean_observaciones(self):
        return limpiar_texto(self.cleaned_data.get('observaciones')) or None

    def clean_hora(self):
        hora = self.cleaned_data.get('hora')
        if hora and not (HORA_APERTURA <= hora <= HORA_CIERRE):
            raise forms.ValidationError(
                f'La clínica atiende de {HORA_APERTURA:%H:%M} a {HORA_CIERRE:%H:%M}.'
            )
        return hora

    def clean(self):
        datos = super().clean()
        fecha, hora = datos.get('fecha'), datos.get('hora')
        estado = datos.get('estado')
        if not (fecha and hora):
            return datos

        # Una cita nueva o reprogramada no puede quedar en el pasado.
        cambio_fecha = not self.instance.pk or (
            fecha != self.instance.fecha or hora != self.instance.hora
        )
        momento = timezone.make_aware(datetime.combine(fecha, hora))
        if estado == 'programada' and cambio_fecha and momento < timezone.now():
            self.add_error('fecha', 'No se puede programar una cita en una fecha u hora que ya pasó.')

        if estado == 'cancelada':
            return datos

        # Choques de horario (las citas canceladas no ocupan el horario).
        activas = Cita.objects.filter(fecha=fecha, hora=hora).exclude(
            estado='cancelada'
        ).exclude(pk=self.instance.pk)
        veterinario = datos.get('veterinario')
        if veterinario and activas.filter(veterinario__iexact=veterinario).exists():
            raise forms.ValidationError(
                f'{veterinario} ya tiene una cita el {fecha:%d/%m/%Y} a las {hora:%H:%M}.'
            )
        mascota = datos.get('mascota')
        if mascota and activas.filter(mascota=mascota).exists():
            raise forms.ValidationError(
                f'{mascota.nombre} ya tiene otra cita el {fecha:%d/%m/%Y} a las {hora:%H:%M}.'
            )
        return datos


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
            }, format='%Y-%m-%d'),
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
        error_messages = {
            'mascota': {'required': 'Debes elegir la mascota.'},
            'fecha': {'required': 'Debes ingresar la fecha.', 'invalid': 'Fecha no válida.'},
            'veterinario': {'required': 'Debes ingresar el veterinario.'},
        }

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha > timezone.localdate():
            raise forms.ValidationError('El registro clínico no puede tener fecha futura.')
        return fecha

    def clean_veterinario(self):
        return limpiar_texto(self.cleaned_data.get('veterinario'))

    def clean(self):
        datos = super().clean()
        for campo in ('diagnostico', 'tratamiento', 'notas'):
            if campo in datos:
                datos[campo] = limpiar_texto(datos[campo]) or None
        if not (datos.get('diagnostico') or datos.get('tratamiento')):
            raise forms.ValidationError('Ingresa al menos el diagnóstico o el tratamiento.')
        return datos


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
            }, format='%Y-%m-%d'),
            'proxima_dosis': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }, format='%Y-%m-%d'),
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