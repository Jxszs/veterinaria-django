from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


class Dueño(models.Model):
    """
    Dueño registrado del sistema.
    Tiene una FK a User para vincular con la cuenta de autenticación.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='duenos',
        help_text='Usuario registrado del sistema asociado a este dueño.',
    )
    nombre = models.CharField(max_length=100, verbose_name='Nombre completo')
    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Número de WhatsApp para contacto (opcional).',
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Teléfono fijo o celular alternativo (opcional).',
    )
    direccion = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='Dirección de domicilio del dueño (opcional).',
    )
    email = models.EmailField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Correo electrónico',
        help_text='Correo para notificaciones (opcional).',
    )

    def __str__(self):
        return f"{self.nombre} ({self.user.get_username()})"

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'Dueños'


class Mascota(models.Model):
    """
    Un paciente de la clínica.
    """
    nombre = models.CharField(max_length=100)
    especie = models.CharField(max_length=50)
    edad = models.IntegerField(
        validators=[
            MinValueValidator(0, message='La edad no puede ser negativa.'),
            MaxValueValidator(40, message='La edad no puede ser mayor a 40 años.'),
        ]
    )
    # Nova FK a Dueño: cada mascota tiene un dueño registrado
    dueno = models.ForeignKey(
        Dueño,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mascotas',
        verbose_name='Dueño',
        help_text='Dueño registrado del sistema. Opcional al crear la mascota.',
    )
    raza = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Raza',
        help_text='Raza de la mascota (ej: Labrador, Siames, Angora...)',
    )
    vacunado = models.BooleanField(default=False)
    alergico = models.BooleanField(
        default=False,
        verbose_name='Alérgico a las vacunas',
        help_text='Marcar si la mascota no puede recibir vacunas por alergia.',
    )

    def clean(self):
        super().clean()
        if self.vacunado and self.alergico:
            raise ValidationError(
                'Una mascota no puede estar vacunada y ser alérgica a las vacunas a la vez.'
            )

    def __str__(self):
        return self.nombre

    @property
    def estado_vacunacion(self):
        if self.alergico:
            return 'alergia'
        if self.vacunado:
            return 'al_dia'
        return 'pendiente'

    class Meta:
        ordering = ['nombre']