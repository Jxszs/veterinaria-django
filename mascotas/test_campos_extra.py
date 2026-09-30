"""
Pruebas de los campos y las funcionalidades que completan el modelo de datos
del enunciado (Caso 5: Clínica Veterinaria).

Cubre:
  - campos nuevos de Dueño (ciudad, email único) y Mascota (sexo, estado,
    fecha de nacimiento, peso, foto),
  - el modelo Receta completo con su CRUD web y el aislamiento por dueño,
  - la alerta de cita en 24 horas y el aviso de receta lista,
  - la paginación de las listas (Criterio 2.1.3, READ: "muestra + paginación"),
  - las columnas proxima_vacuna y ultima_cita del admin.

Ejecutar todas:  python manage.py test mascotas
Solo estas:      python manage.py test mascotas.test_campos_extra
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from mascotas.alertas import (
    enviar_recordatorios_citas, enviar_recordatorios_recetas, recetas_para_avisar,
)
from mascotas.forms import DuenoForm, MascotaForm, RecetaForm
from mascotas.models import (
    Cita, Dueño, Mascota, Receta, Vacuna,
)

hoy = timezone.localdate()


class CamposDueñoTest(TestCase):
    """Ciudad nueva y correo único entre dueños."""

    def setUp(self):
        self.u1 = User.objects.create_user('u1', password='clave12345')
        self.u2 = User.objects.create_user('u2', password='clave12345')

    def test_ciudad_se_guarda(self):
        form = DuenoForm({'user': self.u1.pk, 'nombre': 'Ana Soto',
                          'email': 'ana@x.cl', 'ciudad': 'santiago'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().ciudad, 'Santiago')

    def test_ciudad_rechaza_numeros(self):
        form = DuenoForm({'user': self.u1.pk, 'nombre': 'Ana Soto',
                          'email': 'ana@x.cl', 'ciudad': '123'})
        self.assertFalse(form.is_valid())
        self.assertIn('ciudad', form.errors)

    def test_email_no_se_repite(self):
        Dueño.objects.create(user=self.u1, nombre='Ana', email='dup@x.cl')
        form = DuenoForm({'user': self.u2.pk, 'nombre': 'Otra', 'email': 'dup@x.cl'})
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class CamposMascotaTest(TestCase):
    """Sexo, estado, fecha de nacimiento, peso y foto."""

    def setUp(self):
        self.u = User.objects.create_user('cli', password='clave12345')
        self.root = User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        self.d = Dueño.objects.create(user=self.u, nombre='Ana', email='a@x.cl')
        self.client.login(username='root', password='clave12345')

    def _datos(self, **extra):
        base = {'nombre': 'Toby', 'especie': 'Perro', 'edad': '3'}
        base.update(extra)
        return base

    def test_sexo_estado_por_defecto(self):
        form = MascotaForm(self._datos())
        self.assertTrue(form.is_valid(), form.errors)
        mascota = form.save(commit=False)
        self.assertEqual(mascota.estado, 'activo')
        self.assertEqual(mascota.sexo, '')

    def test_guarda_todos_los_campos_nuevos(self):
        form = MascotaForm(self._datos(
            sexo='hembra', estado='en_tratamiento', peso='12.50',
            fecha_nacimiento='2019-05-10', dueno=self.d.pk,
        ))
        self.assertTrue(form.is_valid(), form.errors)
        mascota = form.save()
        self.assertEqual(mascota.sexo, 'hembra')
        self.assertEqual(mascota.estado, 'en_tratamiento')
        self.assertEqual(mascota.peso, Decimal('12.50'))
        self.assertEqual(mascota.fecha_nacimiento, date(2019, 5, 10))
        self.assertEqual(mascota.dueno, self.d)

    def test_fecha_nacimiento_futura_se_rechaza(self):
        futura = (hoy + timedelta(days=30)).isoformat()
        form = MascotaForm(self._datos(fecha_nacimiento=futura))
        self.assertFalse(form.is_valid())
        self.assertIn('fecha_nacimiento', form.errors)

    def test_peso_cero_o_negativo_se_rechaza(self):
        for peso in ('0', '-3'):
            form = MascotaForm(self._datos(peso=peso))
            self.assertFalse(form.is_valid(), f'peso={peso} deberia fallar')
            self.assertIn('peso', form.errors)

    def test_edad_se_calcula_desde_fecha_nacimiento(self):
        m = Mascota.objects.create(
            nombre='Toby', especie='Perro', edad=0,
            fecha_nacimiento=hoy - timedelta(days=365 * 3 + 10),
        )
        self.assertEqual(m.edad_calculada, 3)
        self.assertIn('3 año', m.edad_texto)

    def test_edad_texto_en_meses_si_es_cachorro(self):
        m = Mascota.objects.create(
            nombre='Cachorro', especie='Perro', edad=0,
            fecha_nacimiento=hoy - timedelta(days=150),
        )
        self.assertIn('mes', m.edad_texto)

    def test_edad_cae_a_la_ingresada_sin_fecha(self):
        m = Mascota.objects.create(nombre='Viejo', especie='Gato', edad=7)
        self.assertEqual(m.edad_calculada, 7)
        self.assertEqual(m.edad_texto, '7 años')

    def test_foto_se_sube(self):
        """
        La foto se sube por el formulario web. Se usa el cliente de pruebas con
        format='multipart' porque los archivos viajan aparte de los datos.
        """
        # PNG mínimo de 1x1.
        png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00'
            b'\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        archivo = SimpleUploadedFile('toby.png', png, 'image/png')
        respuesta = self.client.post(
            reverse('mascotas:crear'),
            {'nombre': 'Firulais', 'especie': 'Gato', 'edad': '2', 'foto': archivo},
            format='multipart',
        )
        self.assertEqual(respuesta.status_code, 302)
        mascota = Mascota.objects.get(nombre='Firulais')
        self.assertIsNotNone(mascota.foto, 'la foto no se guardó')
        # No se comprueba el nombre del archivo: en las pruebas MEDIA_ROOT está
        # vacío, así que Django no le pone nombre ni guarda el archivo en disco.
        self.assertEqual(mascota.foto.read(), png)

    def test_proxima_vacuna_y_ultima_cita_se_calculan(self):
        m = Mascota.objects.create(nombre='Toby', especie='Perro', edad=3, dueno=self.d)
        self.assertIsNone(m.proxima_vacuna)
        self.assertIsNone(m.ultima_cita)

        Vacuna.objects.create(
            mascota=m, tipo='antirrabica', fecha_aplicacion=hoy - timedelta(days=300),
            proxima_dosis=hoy + timedelta(days=10),
        )
        Vacuna.objects.create(
            mascota=m, tipo='triple_virus', fecha_aplicacion=hoy - timedelta(days=100),
            proxima_dosis=hoy + timedelta(days=90),
        )
        # Devuelve la más cercana, no la primera de la lista.
        self.assertEqual(m.proxima_vacuna, hoy + timedelta(days=10))

        Cita.objects.create(
            mascota=m, veterinario='Dr. X', fecha=hoy - timedelta(days=5), hora=time(10, 0),
            estado='finalizada',
        )
        # Una cita programada en el futuro no cuenta como última atención.
        Cita.objects.create(
            mascota=m, veterinario='Dr. X', fecha=hoy + timedelta(days=5), hora=time(10, 0),
            estado='programada',
        )
        self.assertEqual(m.ultima_cita, hoy - timedelta(days=5))


class RecetaTest(TestCase):
    """Modelo Receta: validaciones, CRUD web y aislamiento por dueño."""

    def setUp(self):
        self.root = User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        self.cli = User.objects.create_user('cli', password='clave12345')
        self.otro = User.objects.create_user('otro', password='clave12345')
        self.d = Dueño.objects.create(user=self.cli, nombre='Ana', email='a@x.cl')
        self.d2 = Dueño.objects.create(user=self.otro, nombre='Luis', email='l@x.cl')
        self.m = Mascota.objects.create(nombre='Toby', especie='Perro', edad=3, dueno=self.d)
        self.m2 = Mascota.objects.create(nombre='Otto', especie='Gato', edad=2, dueno=self.d2)
        self.cita = Cita.objects.create(
            mascota=self.m, veterinario='Dr. X', fecha=hoy, hora=time(10, 0), estado='finalizada',
        )
        self.client.login(username='root', password='clave12345')

    def _datos(self, **extra):
        base = {
            'cita': self.cita.pk, 'medicamento': 'amoxicilina 500',
            'dosis': '1 comprimido cada 12 horas', 'duracion_dias': '7',
            'fecha': hoy.isoformat(),
        }
        base.update(extra)
        return base

    def test_formulario_valido(self):
        form = RecetaForm(self._datos())
        self.assertTrue(form.is_valid(), form.errors)
        receta = form.save()
        self.assertEqual(receta.medicamento, 'Amoxicilina 500')

    def test_exige_medicamento_dosis_y_duracion(self):
        form = RecetaForm(self._datos(medicamento='', dosis='', duracion_dias=''))
        self.assertFalse(form.is_valid())
        for campo in ('medicamento', 'dosis', 'duracion_dias'):
            self.assertIn(campo, form.errors)

    def test_no_ofrece_citas_canceladas(self):
        cita_cancelada = Cita.objects.create(
            mascota=self.m, veterinario='Dr. X', fecha=hoy, hora=time(15, 0), estado='cancelada',
        )
        opciones = dict(RecetaForm().fields['cita'].choices)
        self.assertIn(self.cita.pk, opciones)
        self.assertNotIn(cita_cancelada.pk, opciones)

    def test_fecha_no_puede_ser_anterior_a_la_cita(self):
        form = RecetaForm(self._datos(fecha=(hoy - timedelta(days=5)).isoformat()))
        self.assertFalse(form.is_valid())
        self.assertIn('fecha', form.errors)

    def test_fecha_fin_y_estado(self):
        receta = Receta.objects.create(
            cita=self.cita, medicamento='A', dosis='1', duracion_dias=7, fecha=hoy,
        )
        self.assertEqual(receta.fecha_fin, hoy + timedelta(days=6))
        self.assertTrue(receta.en_curso)
        self.assertEqual(receta.dias_restantes, 6)

    def test_receta_terminada_no_esta_en_curso(self):
        receta = Receta.objects.create(
            cita=self.cita, medicamento='A', dosis='1', duracion_dias=3,
            fecha=hoy - timedelta(days=10),
        )
        self.assertFalse(receta.en_curso)
        self.assertEqual(receta.dias_restantes, 0)

    def test_crud_web_completo(self):
        # CREATE
        r = self.client.post(reverse('mascotas:crear_receta'), self._datos())
        receta = Receta.objects.get()
        self.assertRedirects(r, reverse('mascotas:recetas'))
        self.assertEqual(receta.medicamento, 'Amoxicilina 500')

        # READ
        r = self.client.get(reverse('mascotas:recetas'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Amoxicilina 500')

        # UPDATE
        r = self.client.post(
            reverse('mascotas:editar_receta', args=[receta.pk]),
            self._datos(medicamento='amoxicilina 250', duracion_dias='10'),
        )
        self.assertRedirects(r, reverse('mascotas:recetas'))
        receta.refresh_from_db()
        self.assertEqual(receta.medicamento, 'Amoxicilina 250')
        self.assertEqual(receta.duracion_dias, 10)

        # DELETE (pide confirmación antes)
        r = self.client.get(reverse('mascotas:eliminar_receta', args=[receta.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Receta.objects.count(), 1)
        self.client.post(reverse('mascotas:eliminar_receta', args=[receta.pk]))
        self.assertEqual(Receta.objects.count(), 0)

    def test_crear_desde_la_ficha_deja_preseleccionada_la_mascota(self):
        r = self.client.get(reverse('mascotas:crear_receta') + f'?mascota={self.m.pk}')
        self.assertEqual(r.status_code, 200)
        citas = dict(r.context['form'].fields['cita'].choices)
        self.assertIn(self.cita.pk, citas)

    def test_aparece_en_la_linea_de_tiempo_de_la_ficha(self):
        Receta.objects.create(
            cita=self.cita, medicamento='Amoxicilina', dosis='1 c/12h',
            duracion_dias=7, fecha=hoy,
        )
        r = self.client.get(reverse('mascotas:ficha', args=[self.m.pk]))
        self.assertEqual(r.status_code, 200)
        tipos = [evento['tipo'] for evento in r.context['eventos']]
        self.assertIn('receta', tipos)

    def test_cliente_no_ve_recetas_de_otros(self):
        # La receta de Ana es la que el cliente NO debe ver (ingresa como "otro").
        receta_ajena = Receta.objects.create(
            cita=self.cita, medicamento='Secreto', dosis='1', duracion_dias=5, fecha=hoy,
        )
        # Y una suya, para comprobar que sí ve lo propio.
        cita_propia = Cita.objects.create(
            mascota=self.m2, veterinario='Dr. X', fecha=hoy, hora=time(11, 0),
        )
        Receta.objects.create(
            cita=cita_propia, medicamento='Mia', dosis='1', duracion_dias=5, fecha=hoy,
        )
        # El usuario entra como Cliente: puede ver recetas, pero solo las suyas.
        from django.core.management import call_command
        call_command('setup_grupos', verbosity=0)
        self.otro.groups.add(Group.objects.get(name='Clientes'))

        self.client.logout()
        self.client.login(username='otro', password='clave12345')

        r = self.client.get(reverse('mascotas:recetas'))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'Secreto')
        self.assertContains(r, 'Mia')

        r = self.client.get(reverse('mascotas:editar_receta', args=[receta_ajena.pk]))
        # Un cliente no tiene permiso de edición, así que el permiso lo corta
        # antes de llegar a la regla por dueño (403, no 404).
        self.assertEqual(r.status_code, 403)


class AlertasCitaYRecetaTest(TestCase):
    """Recordatorio de cita en 24 h y aviso de receta lista."""

    def setUp(self):
        self.cli = User.objects.create_user('cli', password='clave12345')
        self.d = Dueño.objects.create(user=self.cli, nombre='Ana', email='ana@x.cl')
        self.m = Mascota.objects.create(nombre='Toby', especie='Perro', edad=3, dueno=self.d)
        self.cita = Cita.objects.create(
            mascota=self.m, veterinario='Dr. X', fecha=hoy, hora=time(10, 0),
        )
        self.root = User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        self.client.login(username='root', password='clave12345')
        mail.outbox = []

    def _cita_en_horas(self, horas):
        momento = timezone.localtime() + timedelta(hours=horas)
        return Cita.objects.create(
            mascota=self.m, veterinario='Dr. X',
            fecha=momento.date(), hora=momento.time().replace(microsecond=0),
        )

    def test_avisa_cita_dentro_de_24_horas(self):
        self._cita_en_horas(5)
        resumen = enviar_recordatorios_citas(simular=False)
        self.assertEqual(resumen['enviados'], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Toby', mail.outbox[0].subject)
        self.assertIn('ana@x.cl', mail.outbox[0].to)

    def test_no_avisa_cita_mas_alla_de_24_horas(self):
        self._cita_en_horas(48)
        resumen = enviar_recordatorios_citas(simular=False)
        self.assertEqual(resumen['enviados'], 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_no_repite_el_aviso_de_una_cita(self):
        self._cita_en_horas(5)
        enviar_recordatorios_citas(simular=False)
        segunda = enviar_recordatorios_citas(simular=False)
        self.assertEqual(segunda['enviados'], 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_no_avisa_cita_cancelada(self):
        cita = self._cita_en_horas(5)
        cita.estado = 'cancelada'
        cita.save()
        resumen = enviar_recordatorios_citas(simular=False)
        self.assertEqual(resumen['enviados'], 0)

    def test_no_avisa_si_no_hay_correo(self):
        self.d.email = None
        self.d.save()
        self._cita_en_horas(5)
        resumen = enviar_recordatorios_citas(simular=False)
        self.assertEqual(resumen['enviados'], 0)
        self.assertEqual(resumen['sin_correo'], 1)

    def test_comando_simular_no_envia(self):
        self._cita_en_horas(5)
        from io import StringIO
        salida = StringIO()
        from django.core.management import call_command
        call_command('enviar_recordatorios', '--simular', stdout=salida)
        self.assertIn('Recordatorios de cita', salida.getvalue())
        self.assertEqual(len(mail.outbox), 0)

    def test_avisa_receta_lista(self):
        receta = Receta.objects.create(
            cita=self.cita, medicamento='Amoxicilina', dosis='1 c/12h',
            duracion_dias=7, fecha=hoy,
        )
        resumen = enviar_recordatorios_recetas(simular=False)
        self.assertEqual(resumen['enviados'], 1)
        self.assertIn('Receta lista', mail.outbox[0].subject)
        receta.refresh_from_db()
        self.assertIsNotNone(receta.receta_lista_el)

    def test_no_avisa_receta_indicada_otro_dia(self):
        Receta.objects.create(
            cita=self.cita, medicamento='A', dosis='1', duracion_dias=7,
            fecha=hoy - timedelta(days=3),
        )
        resumen = enviar_recordatorios_recetas(simular=False)
        self.assertEqual(resumen['enviados'], 0)

    def test_boton_avisar_manda_un_solo_correo(self):
        receta = Receta.objects.create(
            cita=self.cita, medicamento='Amoxicilina', dosis='1', duracion_dias=7, fecha=hoy,
        )
        otra = Receta.objects.create(
            cita=self.cita, medicamento='Vitaminas', dosis='1', duracion_dias=30, fecha=hoy,
        )
        mail.outbox = []
        r = self.client.post(reverse('mascotas:avisar_receta', args=[receta.pk]))
        self.assertRedirects(r, reverse('mascotas:recetas'))
        self.assertEqual(len(mail.outbox), 1)
        receta.refresh_from_db()
        otra.refresh_from_db()
        self.assertIsNotNone(receta.receta_lista_el)
        self.assertIsNone(otra.receta_lista_el)

    def test_boton_avisar_es_solo_post(self):
        receta = Receta.objects.create(
            cita=self.cita, medicamento='A', dosis='1', duracion_dias=7, fecha=hoy,
        )
        r = self.client.get(reverse('mascotas:avisar_receta', args=[receta.pk]))
        self.assertEqual(r.status_code, 405)

    def test_pagina_de_alertas_lista_citas_y_recetas(self):
        self._cita_en_horas(3)
        Receta.objects.create(
            cita=self.cita, medicamento='A', dosis='1', duracion_dias=7, fecha=hoy,
        )
        r = self.client.get(reverse('mascotas:alertas_vacunas'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['citas_proximas']), 1)
        self.assertEqual(len(r.context['recetas_sin_avisar']), 1)


class PaginacionTest(TestCase):
    """Criterio 2.1.3 (READ): las listas muestran paginación."""

    def setUp(self):
        self.root = User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        self.client.login(username='root', password='clave12345')
        for i in range(25):
            Mascota.objects.create(nombre=f'Mascota {i:02d}', especie='Perro', edad=1)
        for i in range(15):
            Dueño.objects.create(
                user=User.objects.create_user(f'user{i:02d}'), nombre=f'Dueño {i:02d}',
            )

    def _comprobar(self, url, nombre_lista, total, por_pagina=10):
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total_registros'], total)
        self.assertEqual(len(r.context[nombre_lista]), por_pagina)
        self.assertTrue(r.context['page_obj'].has_next())
        return r

    def test_lista_de_mascotas_pagina(self):
        self._comprobar(reverse('mascotas:lista'), 'mascotas', 25)

    def test_lista_de_duenos_pagina(self):
        self._comprobar(reverse('mascotas:lista_duenos'), 'duenos', 15)

    def test_primera_pagina_no_devuelve_todo(self):
        r = self.client.get(reverse('mascotas:lista'))
        nombres = [m.nombre for m in r.context['mascotas']]
        self.assertNotIn('Mascota 24', nombres)

    def test_segunda_pagina_muestra_los_siguientes(self):
        r = self.client.get(reverse('mascotas:lista') + '?pagina=2')
        self.assertEqual(r.status_code, 200)
        nombres = [m.nombre for m in r.context['mascotas']]
        self.assertEqual(len(nombres), 10)
        # La lista viene ordenada por nombre: la segunda página va de la 10 a la 19.
        self.assertEqual(nombres[0], 'Mascota 10')
        self.assertEqual(nombres[-1], 'Mascota 19')

    def test_ultima_pagina_muestra_el_resto(self):
        r = self.client.get(reverse('mascotas:lista') + '?pagina=3')
        self.assertEqual(len(r.context['mascotas']), 5)

    def test_pagina_fuera_de_rango_no_rompe(self):
        r = self.client.get(reverse('mascotas:lista') + '?pagina=999')
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse('mascotas:lista') + '?pagina=abc')
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse('mascotas:lista') + '?pagina=-1')
        self.assertEqual(r.status_code, 200)

    def test_lista_menos_que_una_pagina_no_muestra_controles(self):
        r = self.client.get(reverse('mascotas:lista_citas'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total_registros'], 0)

    def test_filtro_se_conserva_al_cambiar_de_pagina(self):
        r = self.client.get(reverse('mascotas:lista') + '?especie=Perro&pagina=2')
        self.assertEqual(r.status_code, 200)
        siguiente = r.context['pagina_siguiente']
        self.assertIsNotNone(siguiente)
        self.assertIn('pagina=3', siguiente)
        self.assertIn('especie=Perro', siguiente)


class AdminAvanzadoTest(TestCase):
    """Columnas de seguimiento y admin de Receta."""

    def setUp(self):
        self.root = User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        self.client.login(username='root', password='clave12345')
        self.d = Dueño.objects.create(
            user=User.objects.create_user('u1'), nombre='Ana', email='a@x.cl',
        )
        self.m = Mascota.objects.create(
            nombre='Toby', especie='Perro', edad=3, dueno=self.d, sexo='macho',
        )
        self.cita = Cita.objects.create(
            mascota=self.m, veterinario='Dr. X', fecha=hoy, hora=time(10, 0), estado='finalizada',
        )
        self.receta = Receta.objects.create(
            cita=self.cita, medicamento='Amoxicilina', dosis='1 c/12h',
            duracion_dias=7, fecha=hoy,
        )

    def test_admin_de_mascota_tiene_las_columnas_pedidas(self):
        from mascotas.admin import MascotaAdmin
        for columna in ('nombre', 'dueno', 'especie', 'proxima_vacuna', 'ultima_cita'):
            self.assertIn(columna, MascotaAdmin.list_display)

    def test_admin_de_receta_registrado(self):
        from django.contrib import admin
        from mascotas.models import Receta
        self.assertIn(Receta, admin.site._registry)

    def test_changelist_de_mascotas_carga(self):
        r = self.client.get('/admin/mascotas/mascota/')
        self.assertEqual(r.status_code, 200)

    def test_changelist_de_recetas_carga(self):
        r = self.client.get('/admin/mascotas/receta/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Amoxicilina')

    def test_pagina_de_edicion_de_receta_carga(self):
        r = self.client.get(f'/admin/mascotas/receta/{self.receta.pk}/change/')
        self.assertEqual(r.status_code, 200)

    def test_setup_grupos_incluye_permisos_de_receta(self):
        from django.core.management import call_command
        from django.contrib.auth.models import Group
        call_command('setup_grupos', verbosity=0)
        admin = Group.objects.get(name='Administradores')
        vet = Group.objects.get(name='Veterinarios')
        cli = Group.objects.get(name='Clientes')
        self.assertTrue(admin.permissions.filter(codename='add_receta').exists())
        self.assertTrue(vet.permissions.filter(codename='change_receta').exists())
        self.assertTrue(cli.permissions.filter(codename='view_receta').exists())
        # El cliente no puede crear ni borrar recetas.
        self.assertFalse(cli.permissions.filter(codename='add_receta').exists())
        self.assertFalse(cli.permissions.filter(codename='delete_receta').exists())
