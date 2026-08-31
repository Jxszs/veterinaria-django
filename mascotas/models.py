from django.db import models


class Mascota(models.Model):
    """
    Un paciente de la clínica.

    Los 4 campos base tienen los mismos 4 tipos de dato que pide el repaso
    de conceptos (2 CharField, 1 IntegerField, 1 BooleanField). `alergico`
    es un 5to campo (BooleanField) que se agrega aparte para cubrir el
    tercer estado de vacunación ("alergia a vacunas") que pide el
    enunciado del Caso 5, sin romper la combinación de tipos exigida en
    los 4 campos base.
    """
    nombre = models.CharField(max_length=100)
    especie = models.CharField(max_length=50)
    edad = models.IntegerField()
    vacunado = models.BooleanField(default=False)
    alergico = models.BooleanField(
        default=False,
        verbose_name='Alérgico a las vacunas',
        help_text='Marcar si la mascota no puede recibir vacunas por alergia.',
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

    class Meta:
        ordering = ['nombre']
