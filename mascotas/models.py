from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

# Días de anticipación con que se avisa una dosis de refuerzo (JO3).
DIAS_AVISO_VACUNA = 30

# Horas de anticipación con que se avisa una cita programada.
HORAS_AVISO_CITA = 24


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
        unique=True,
        verbose_name='Correo electrónico',
        help_text='Correo para notificaciones. No puede repetirse entre dueños.',
    )
    ciudad = models.CharField(
        max_length=80,
        blank=True,
        null=True,
        verbose_name='Ciudad',
        help_text='Ciudad donde vive el dueño (opcional).',
    )

    def __str__(self):
        return f"{self.nombre} ({self.user.get_username()})"

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'Dueños'
        permissions = [
            ("view_own_mascotas", "Puede ver solo sus propias mascotas"),
        ]


class Mascota(models.Model):
    """
    Un paciente de la clínica.
    """
    SEXO_CHOICES = [
        ('macho', 'Macho'),
        ('hembra', 'Hembra'),
    ]
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('en_tratamiento', 'En tratamiento'),
        ('recuperando', 'Recuperando'),
        ('fallecido', 'Fallecido'),
    ]

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
    fecha_nacimiento = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha de nacimiento',
        help_text='Se usa para calcular la edad al mostrar la ficha. Opcional.',
    )
    peso = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'), message='El peso debe ser mayor a 0.')],
        verbose_name='Peso (kg)',
        help_text='Peso actual en kilogramos (opcional).',
    )
    sexo = models.CharField(
        max_length=10,
        choices=SEXO_CHOICES,
        blank=True,
        default='',
        verbose_name='Sexo',
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo',
        verbose_name='Estado',
        help_text='Estado general de la mascota en la clínica.',
    )
    foto = models.ImageField(
        upload_to='mascotas/',
        blank=True,
        null=True,
        verbose_name='Foto',
        help_text='Fotografía de la mascota (opcional).',
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
        if self.fecha_nacimiento and self.fecha_nacimiento > timezone.localdate():
            raise ValidationError(
                {'fecha_nacimiento': 'La fecha de nacimiento no puede ser futura.'}
            )

    def __str__(self):
        return self.nombre

    @property
    def edad_calculada(self):
        """
        Edad en años a partir de la fecha de nacimiento. Si no hay fecha,
        devuelve la edad guardada a mano, para no perder el dato previo.
        """
        if not self.fecha_nacimiento:
            return self.edad
        meses = (timezone.localdate() - self.fecha_nacimiento).days // 30
        return max(0, meses // 12)

    @property
    def edad_texto(self):
        """Edad legible: '3 años' o '5 meses' si es Cachorro."""
        anios = self.edad_calculada
        if not self.fecha_nacimiento:
            return '%d año%s' % (anios, '' if anios == 1 else 's')
        meses = (timezone.localdate() - self.fecha_nacimiento).days // 30
        if meses < 12:
            return '%d mes%s' % (meses, '' if meses == 1 else 'es')
        return '%d año%s' % (anios, '' if anios == 1 else 's')

    @property
    def estado_vacunacion(self):
        """Devuelve 'alergia', 'al_dia' o 'pendiente' según los dos booleanos."""
        if self.alergico:
            return 'alergia'
        if self.vacunado:
            return 'al_dia'
        return 'pendiente'

    @property
    def proxima_vacuna(self):
        """Fecha de la próxima dosis de refuerzo más cercana, o None."""
        refuerzo = self.vacunas.filter(proxima_dosis__isnull=False).order_by('proxima_dosis').first()
        return refuerzo.proxima_dosis if refuerzo else None

    @property
    def ultima_cita(self):
        """Fecha de la última cita ya realizada, o None si nunca ha tenido una."""
        atendida = self.citas.exclude(
            estado__in=['programada', 'cancelada']
        ).order_by('-fecha').first()
        return atendida.fecha if atendida else None

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'Mascotas'
        permissions = [
            ("view_historial_medico", "Puede ver el historial médico completo"),
            ("manage_vacunas", "Puede gestionar vacunas de cualquier mascota"),
            ("view_own_mascotas", "Puede ver solo sus propias mascotas"),
        ]


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
    duracion = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(5, message='La duración mínima es 5 minutos.'),
            MaxValueValidator(480, message='La duración máxima es 480 minutos (8 horas).'),
        ],
        verbose_name='Duración (minutos)',
        help_text='Cuánto seاليات la consulta. Opcional.',
    )
    alerta_enviada_el = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Recordatorio enviado el',
        help_text='Momento en que se envió el recordatorio de esta cita por correo.',
    )

    def __str__(self):
        return f"Cita: {self.mascota.nombre} - {self.fecha} {self.hora}"

    class Meta:
        ordering = ['fecha', 'hora']
        verbose_name_plural = 'Citas'
        permissions = [
            ("view_own_citas", "Puede ver solo sus propias citas"),
        ]


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
        permissions = [
            ("view_own_historial", "Puede ver solo su propio historial"),
        ]


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
    alerta_enviada_el = models.DateField(
        blank=True,
        null=True,
        verbose_name='Alerta enviada el',
        help_text='Fecha en que se envió el recordatorio por correo de la próxima dosis.',
    )

    def __str__(self):
        return f"Vacuna: {self.mascota.nombre} - {self.get_tipo_display()} ({self.fecha_aplicacion})"

    @property
    def dias_para_refuerzo(self):
        """Días que faltan para la próxima dosis (negativo si ya venció)."""
        if not self.proxima_dosis:
            return None
        return (self.proxima_dosis - timezone.localdate()).days

    @property
    def plazo_refuerzo(self):
        """Texto amigable del plazo: 'venció hace 3 día(s)', 'vence hoy', 'vence en 10 día(s)'."""
        dias = self.dias_para_refuerzo
        if dias is None:
            return 'sin refuerzo registrado'
        if dias < 0:
            return f'venció hace {-dias} día(s)'
        if dias == 0:
            return 'vence hoy'
        return f'vence en {dias} día(s)'

    @property
    def estado_dosis(self):
        """
        Estado del refuerzo (JO3):
          - 'vencida': la próxima dosis ya pasó.
          - 'proxima': vence dentro de DIAS_AVISO_VACUNA días.
          - 'al_dia': la próxima dosis está lejos.
          - 'sin_refuerzo': no tiene próxima dosis registrada.
        """
        dias = self.dias_para_refuerzo
        if dias is None:
            return 'sin_refuerzo'
        if dias < 0:
            return 'vencida'
        if dias <= DIAS_AVISO_VACUNA:
            return 'proxima'
        return 'al_dia'

    class Meta:
        ordering = ['-fecha_aplicacion']
        verbose_name_plural = 'Vacunas'
        permissions = [
            ("view_own_vacunas", "Puede ver solo sus propias vacunas"),
        ]


# ────────────────────────────────────────────────────────────────────────────────
# Facturación (JO4)
# ────────────────────────────────────────────────────────────────────────────────

# IVA en Chile. Los precios se ingresan netos (sin IVA) y en pesos enteros.
TASA_IVA = 0.19


class Factura(models.Model):
    """
    Cobro a un dueño por atenciones de la clínica. El detalle (servicios y
    productos) está en DetalleFactura; los montos se calculan, no se escriben.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de pago'),
        ('pagada', 'Pagada'),
        ('anulada', 'Anulada'),
    ]
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('debito', 'Tarjeta de débito'),
        ('credito', 'Tarjeta de crédito'),
        ('transferencia', 'Transferencia'),
    ]

    dueno = models.ForeignKey(
        Dueño,
        on_delete=models.PROTECT,
        related_name='facturas',
        verbose_name='Dueño',
        help_text='No se puede borrar un dueño que tiene facturas.',
    )
    mascota = models.ForeignKey(
        Mascota,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='facturas',
        verbose_name='Mascota atendida',
    )
    cita = models.ForeignKey(
        Cita,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='facturas',
        verbose_name='Cita asociada',
    )
    fecha = models.DateField(default=timezone.localdate, verbose_name='Fecha de emisión')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    metodo_pago = models.CharField(
        max_length=20, choices=METODO_PAGO_CHOICES, blank=True, verbose_name='Método de pago'
    )
    fecha_pago = models.DateField(blank=True, null=True, verbose_name='Fecha de pago')
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name_plural = 'Facturas'
        permissions = [
            ("view_own_facturas", "Puede ver solo sus propias facturas"),
        ]

    def __str__(self):
        return f'{self.numero} - {self.dueno.nombre}'

    @property
    def numero(self):
        return f'F-{self.pk:06d}' if self.pk else 'F-(nueva)'

    @property
    def neto(self):
        return sum(detalle.subtotal for detalle in self.detalles.all())

    @property
    def iva(self):
        return round(self.neto * TASA_IVA)

    @property
    def total(self):
        return self.neto + self.iva

    def clean(self):
        super().clean()
        if self.mascota_id and self.dueno_id and self.mascota.dueno_id != self.dueno_id:
            raise ValidationError({'mascota': 'La mascota elegida no pertenece a este dueño.'})
        if self.cita_id and self.mascota_id and self.cita.mascota_id != self.mascota_id:
            raise ValidationError({'cita': 'La cita elegida es de otra mascota.'})
        if self.estado == 'pagada' and not self.metodo_pago:
            raise ValidationError({'metodo_pago': 'Indica con qué se pagó la factura.'})


class DetalleFactura(models.Model):
    """Una línea de la factura: servicio o producto, cantidad y precio unitario neto."""
    factura = models.ForeignKey(
        Factura, on_delete=models.CASCADE, related_name='detalles', verbose_name='Factura'
    )
    descripcion = models.CharField(max_length=150, verbose_name='Descripción')
    cantidad = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1, message='La cantidad mínima es 1.'),
            MaxValueValidator(999, message='La cantidad máxima es 999.'),
        ],
    )
    precio_unitario = models.PositiveIntegerField(
        verbose_name='Precio unitario neto (CLP)',
        validators=[MaxValueValidator(10_000_000, message='El precio no puede superar $10.000.000.')],
    )

    class Meta:
        ordering = ['id']
        verbose_name = 'Detalle de factura'
        verbose_name_plural = 'Detalles de factura'

    def __str__(self):
        return f'{self.cantidad} x {self.descripcion}'

    @property
    def subtotal(self):
        return (self.cantidad or 0) * (self.precio_unitario or 0)


# ────────────────────────────────────────────────────────────────────────────────
# Recetas (indicación del veterinario tras una consulta)
# ────────────────────────────────────────────────────────────────────────────────


class Receta(models.Model):
    """
    Medicamento recetado en una cita, con su dosis y duración.

    Se liga a la Cita porque la receta siempre nace de una consulta; desde
    ahí se sabe qué mascota y qué dueño la recibe.
    """
    cita = models.ForeignKey(
        Cita,
        on_delete=models.CASCADE,
        related_name='recetas',
        verbose_name='Cita',
    )
    medicamento = models.CharField(
        max_length=120,
        verbose_name='Medicamento',
        help_text='Nombre del medicamento recetado (ej: Amoxicilina 500mg).',
    )
    dosis = models.CharField(
        max_length=120,
        verbose_name='Dosis',
        help_text='Cómo se administra (ej: 1 comprimido cada 12 horas).',
    )
    duracion_dias = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1, message='La duración mínima es 1 día.'),
            MaxValueValidator(365, message='La duración máxima es 365 días.'),
        ],
        verbose_name='Duración (días)',
        help_text='Cuántos días debe seguir el tratamiento.',
    )
    fecha = models.DateField(
        default=timezone.localdate,
        verbose_name='Fecha de la indicación',
    )
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    receta_lista_el = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Aviso de receta enviada el',
        help_text='Momento en que se avisó al dueño que la receta está lista.',
    )

    def __str__(self):
        return f'Receta: {self.medicamento} ({self.cita.mascota.nombre})'

    @property
    def fecha_fin(self):
        """Último día del tratamiento."""
        return self.fecha + timedelta(days=self.duracion_dias - 1)

    @property
    def en_curso(self):
        """True si la receta está vigente hoy."""
        hoy = timezone.localdate()
        return self.fecha <= hoy <= self.fecha_fin

    @property
    def dias_restantes(self):
        """Días que faltan para terminar el tratamiento (0 si ya venció)."""
        return max(0, (self.fecha_fin - timezone.localdate()).days)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Receta'
        verbose_name_plural = 'Recetas'
        permissions = [
            ("view_own_recetas", "Puede ver solo sus propias recetas"),
        ]


# ────────────────────────────────────────────────────────────────────────────────
# Inventario con semáforo (GA3)
# ────────────────────────────────────────────────────────────────────────────────

# Días antes del vencimiento en que un producto pasa a amarillo.
DIAS_AVISO_VENCIMIENTO = 30


class Producto(models.Model):
    """
    Medicamentos, vacunas, alimentos e insumos de la clínica.

    Semáforo de stock:
      - rojo: sin stock, stock en la mitad del mínimo o menos, o producto vencido.
      - amarillo: stock igual o bajo el mínimo, o vence dentro de 30 días.
      - verde: todo en orden.
    """
    CATEGORIA_CHOICES = [
        ('medicamento', 'Medicamento'),
        ('vacuna', 'Vacuna'),
        ('alimento', 'Alimento'),
        ('insumo', 'Insumo clínico'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=120, unique=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='medicamento', verbose_name='Categoría')
    stock = models.PositiveIntegerField(default=0, verbose_name='Stock actual')
    stock_minimo = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1, message='El stock mínimo debe ser al menos 1.')],
        verbose_name='Stock mínimo',
        help_text='Bajo esta cantidad el producto pasa a amarillo.',
    )
    unidad = models.CharField(max_length=30, default='unidad', help_text='Ej: unidad, caja, frasco, kg.')
    precio_venta = models.PositiveIntegerField(default=0, verbose_name='Precio de venta neto (CLP)')
    fecha_vencimiento = models.DateField(blank=True, null=True, verbose_name='Fecha de vencimiento')
    activo = models.BooleanField(default=True, help_text='Desmarcar si ya no se trabaja con este producto.')

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'Productos'

    def __str__(self):
        return f'{self.nombre} ({self.stock} {self.unidad})'

    @property
    def vencido(self):
        return bool(self.fecha_vencimiento and self.fecha_vencimiento < timezone.localdate())

    @property
    def por_vencer(self):
        if not self.fecha_vencimiento or self.vencido:
            return False
        return (self.fecha_vencimiento - timezone.localdate()).days <= DIAS_AVISO_VENCIMIENTO

    @property
    def semaforo(self):
        if self.stock == 0 or self.vencido or self.stock * 2 <= self.stock_minimo:
            return 'rojo'
        if self.stock <= self.stock_minimo or self.por_vencer:
            return 'amarillo'
        return 'verde'

    @property
    def motivo_semaforo(self):
        """Explica en palabras por qué el producto tiene ese color."""
        if self.vencido:
            return 'Producto vencido'
        if self.stock == 0:
            return 'Sin stock'
        if self.stock * 2 <= self.stock_minimo:
            return 'Stock crítico'
        if self.stock <= self.stock_minimo:
            return 'Stock bajo el mínimo'
        if self.por_vencer:
            return f'Vence el {self.fecha_vencimiento:%d/%m/%Y}'
        return 'Stock suficiente'
