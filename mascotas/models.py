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
        """Devuelve 'alergia', 'al_dia' o 'pendiente' según los dos booleanos."""
        if self.alergico:
            return 'alergia'
        if self.vacunado:
            return 'al_dia'
        return 'pendiente'


class Cita(models.Model):
    """
    Una cita programada en la clínica.
    """
    ESTADO_CHOICES = [
        ('programada', 'Programada'),
        ('en_curso', 'En curso'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
    ]

    mascota = models.ForeignKey(
        Mascota,
        on_delete=models.CASCADE,
        related_name='citas',
        verbose_name='Mascota',
    )
    veterinario = models.CharField(max_length=100, verbose_name='Veterinario a cargo')
    fecha = models.DateField(verbose_name='Fecha de la cita')
    hora = models.TimeField(verbose_name='Hora de la cita')
    motivo = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Motivo de la consulta',
        help_text='Ej: chequeo anual, vacunación, lesión...',
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observaciones',
        help_text='Notas de la cita (llenado por el veterinario).',
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='programada',
        verbose_name='Estado',
    )

    def __str__(self):
        return f"Cita: {self.mascota.nombre} - {self.fecha} {self.hora}"

    class Meta:
        ordering = ['fecha', 'hora']
        verbose_name_plural = 'Citas'


class HistorialMedico(models.Model):
    """
    Registro del historial médico de una mascota.
    """
    mascota = models.ForeignKey(
        Mascota,
        on_delete=models.CASCADE,
        related_name='historial',
        verbose_name='Mascota',
    )
    fecha = models.DateField(verbose_name='Fecha del registro')
    diagnostico = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        verbose_name='Diagnóstico',
    )
    tratamiento = models.TextField(
        blank=True,
        null=True,
        verbose_name='Tratamiento indicado',
    )
    veterinario = models.CharField(max_length=100, verbose_name='Veterinario')
    notas = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notas adicionales',
    )

    def __str__(self):
        return f"Historial: {self.mascota.nombre} - {self.fecha}"

    class Meta:
        ordering = ['-fecha']
        verbose_name_plural = 'Históricos médicos'


class Vacuna(models.Model):
    """
    Registro de vacunación de una mascota.
    """
    TIPOS_CHOICES = [
        ('multivitaminica', 'Multivitamínica'),
        ('antirrabica', 'Antirrábica'),
        ('triple_virus', 'Triple virus'),
        ('covid_canino', 'COVID Canino'),
        ('rabia', 'Rabia'),
        ('otra', 'Otra'),
    ]

    mascota = models.ForeignKey(
        Mascota,
        on_delete=models.CASCADE,
        related_name='vacunas',
        verbose_name='Mascota',
    )
    tipo = models.CharField(
        max_length=30,
        choices=TIPOS_CHOICES,
        verbose_name='Tipo de vacuna',
    )
    fecha_aplicacion = models.DateField(verbose_name='Fecha de aplicación')
    proxima_dosis = models.DateField(
        blank=True,
        null=True,
        verbose_name='Próxima dosis',
        help_text='Fecha cuando se debe aplicar la siguiente dosis.',
    )
    lote = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Nº de lote',
        help_text='Número de lote del fabricante.',
    )
    fabricante = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Fabricante',
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observaciones',
    )

    def __str__(self):
        return f"Vacuna: {self.mascota.nombre} - {self.tipo} ({self.fecha_aplicacion})"

    class Meta:
        ordering = ['-fecha_aplicacion']
        verbose_name_plural = 'Vacunas'
