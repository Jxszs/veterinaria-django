"""
Pruebas de las funcionalidades avanzadas (GA4).

Cubren lo agregado en JO1-JO5 (dueños, citas, alertas, facturación, dashboard)
y en GA2-GA3 (roles, permisos por dueño e inventario). Las pruebas originales
del modelo Mascota, validación y manejo de errores siguen en tests.py.

Ejecutar todas:  python manage.py test mascotas
Solo estas:      python manage.py test mascotas.test_avanzado
"""
from datetime import time, timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from mascotas.models import (
    Cita, DetalleFactura, Dueño, Factura, HistorialMedico, Mascota, Producto, Vacuna,
)
from mascotas.templatetags.veterinaria_extras import formato_clp

hoy = timezone.localdate()


def mgmt(n=3, ini=0):
    """Datos de control del formset de líneas de factura."""
    return {
        'detalles-TOTAL_FORMS': str(n), 'detalles-INITIAL_FORMS': str(ini),
        'detalles-MIN_NUM_FORMS': '1', 'detalles-MAX_NUM_FORMS': '1000',
    }


class DuenosYCrudTest(TestCase):
    """JO1: dueños, CRUD de historial/vacunas y visibilidad por dueño."""

    def setUp(self):
        self.root = User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        self.cli = User.objects.create_user('cli', password='clave12345')
        self.d = Dueño.objects.create(user=self.cli, nombre='Ana Soto', email='a@x.cl')
        self.m = Mascota.objects.create(nombre='Toby', especie='Perro', edad=3, dueno=self.d)
        self.m2 = Mascota.objects.create(nombre='Otro', especie='Gato', edad=3)
        self.client.login(username='root', password='clave12345')

    def test_paginas(self):
        for n in ['lista','lista_duenos','crear_dueno','lista_citas','lista_vacunas','lista_historial','crear_vacuna','crear_historial','crear']:
            r = self.client.get(reverse('mascotas:'+n))
            self.assertEqual(r.status_code, 200, n)
        self.assertContains(self.client.get(reverse('mascotas:lista')), 'Dueños')

    def test_dueno_crud(self):
        u = User.objects.create_user('nuevo', password='x12345678')
        r = self.client.post(reverse('mascotas:crear_dueno'), {'user': u.pk, 'nombre': ' <b>pedro</b> rojas ', 'telefono': '+56 9 1234 5678'})
        self.assertEqual(r.status_code, 302)
        d = Dueño.objects.get(user=u)
        self.assertEqual(d.nombre, 'Pedro Rojas')
        self.assertEqual(d.telefono, '+56912345678')
        r = self.client.post(reverse('mascotas:crear_dueno'), {'user': u.pk, 'nombre': 'Otro Nombre', 'email': 'o@x.cl'})
        self.assertContains(r, 'ya tiene un perfil')
        r = self.client.post(reverse('mascotas:crear_dueno'), {'user': self.root.pk, 'nombre': 'Sin Contacto'})
        self.assertContains(r, 'al menos un medio de contacto')
        r = self.client.post(reverse('mascotas:editar_dueno', args=[d.pk]), {'user': u.pk, 'nombre': 'Pedro R', 'email': 'p@x.cl'})
        self.assertEqual(r.status_code, 302)
        self.client.post(reverse('mascotas:eliminar_dueno', args=[self.d.pk]))
        self.m.refresh_from_db()
        self.assertIsNone(self.m.dueno)

    def test_vacuna_historial_crud(self):
        v = Vacuna.objects.create(mascota=self.m, tipo='rabia', fecha_aplicacion=hoy)
        r = self.client.get(reverse('mascotas:editar_vacuna', args=[v.pk]))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('mascotas:eliminar_vacuna', args=[v.pk]))
        self.assertFalse(Vacuna.objects.exists())
        h = HistorialMedico.objects.create(mascota=self.m, fecha=hoy, veterinario='Dr X', diagnostico='ok')
        r = self.client.post(reverse('mascotas:editar_historial', args=[h.pk]), {'mascota': self.m.pk, 'fecha': (hoy+timedelta(days=3)).isoformat(), 'veterinario': 'Dr X', 'diagnostico':'x'})
        self.assertContains(r, 'fecha futura')
        r = self.client.post(reverse('mascotas:editar_historial', args=[h.pk]), {'mascota': self.m.pk, 'fecha': hoy.isoformat(), 'veterinario': 'Dr X'})
        self.assertContains(r, 'al menos el diagn')
        r = self.client.post(reverse('mascotas:eliminar_historial', args=[h.pk]))
        self.assertFalse(HistorialMedico.objects.exists())

    def test_cliente_solo_ve_lo_suyo(self):
        Vacuna.objects.create(mascota=self.m, tipo='rabia', fecha_aplicacion=hoy)
        v2 = Vacuna.objects.create(mascota=self.m2, tipo='rabia', fecha_aplicacion=hoy)
        self.cli.user_permissions.add(*Permission.objects.filter(codename__in=['view_vacuna','change_vacuna']))
        self.client.login(username='cli', password='clave12345')
        r = self.client.get(reverse('mascotas:lista_vacunas'))
        self.assertEqual(len(r.context['vacunas']), 1)
        self.assertEqual(self.client.get(reverse('mascotas:editar_vacuna', args=[v2.pk])).status_code, 404)
        # un veterinario (grupo) ve todo
        vet = User.objects.create_user('vet', password='clave12345')
        g,_=Group.objects.get_or_create(name='Veterinarios')
        vet.groups.add(g)
        vet.user_permissions.add(*Permission.objects.filter(codename='view_vacuna'))
        self.client.login(username='vet', password='clave12345')
        r = self.client.get(reverse('mascotas:lista_vacunas'))
        self.assertEqual(len(r.context['vacunas']), 2)


class CitasYFichaTest(TestCase):
    """JO2: validación de citas, cancelación y ficha con línea de tiempo."""

    def setUp(self):
        self.root = User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        self.m = Mascota.objects.create(nombre='Toby', especie='Perro', edad=3)
        self.m2 = Mascota.objects.create(nombre='Luna', especie='Gato', edad=2)
        self.client.login(username='root', password='clave12345')
        self.man = hoy+timedelta(days=1)

    def post(self, **k):
        d = {'mascota': self.m.pk, 'veterinario': 'Dr. Pérez', 'fecha': self.man.isoformat(), 'hora': '10:00', 'estado': 'programada'}
        d.update(k)
        return self.client.post(reverse('mascotas:crear_cita'), d)

    def test_validaciones(self):
        self.assertEqual(self.post().status_code, 302)
        self.assertContains(self.post(mascota=self.m2.pk), 'ya tiene una cita')
        self.assertContains(self.post(veterinario='Dra. Soto'), 'ya tiene otra cita')
        self.assertContains(self.post(fecha=(hoy-timedelta(days=2)).isoformat(), hora='11:00'), 'ya pas')
        self.assertContains(self.post(hora='22:00'), 'atiende de')
        self.assertContains(self.post(veterinario='12'), 'al menos 3')
        # editar una cita antigua sin cambiar fecha es válido
        c = Cita.objects.create(mascota=self.m2, veterinario='Dr X', fecha=hoy-timedelta(days=5), hora=time(10), estado='finalizada')
        r = self.client.post(reverse('mascotas:editar_cita', args=[c.pk]), {'mascota': self.m2.pk, 'veterinario': 'Dr X', 'fecha': c.fecha.isoformat(), 'hora': '10:00', 'estado': 'finalizada', 'observaciones': 'todo ok'})
        self.assertEqual(r.status_code, 302)
        r = self.client.get(reverse('mascotas:editar_cita', args=[c.pk]))
        self.assertContains(r, c.fecha.isoformat())

    def test_cancelar(self):
        c = Cita.objects.create(mascota=self.m, veterinario='Dr X', fecha=self.man, hora=time(10))
        self.assertEqual(self.client.get(reverse('mascotas:cancelar_cita', args=[c.pk])).status_code, 405)
        self.client.post(reverse('mascotas:cancelar_cita', args=[c.pk]))
        c.refresh_from_db()
        self.assertEqual(c.estado, 'cancelada')
        r = self.client.post(reverse('mascotas:cancelar_cita', args=[c.pk]), follow=True)
        self.assertContains(r, 'no se puede cancelar')
        # ahora el horario queda libre
        self.assertEqual(self.post(mascota=self.m2.pk).status_code, 302)

    def test_filtros_y_ficha(self):
        Cita.objects.create(mascota=self.m, veterinario='Dr X', fecha=hoy, hora=time(10))
        Cita.objects.create(mascota=self.m, veterinario='Dr X', fecha=hoy-timedelta(days=3), hora=time(10), estado='finalizada')
        Vacuna.objects.create(mascota=self.m, tipo='rabia', fecha_aplicacion=hoy-timedelta(days=10), proxima_dosis=hoy+timedelta(days=355))
        HistorialMedico.objects.create(mascota=self.m, fecha=hoy-timedelta(days=1), veterinario='Dr X', diagnostico='Otitis')
        self.assertEqual(len(self.client.get(reverse('mascotas:lista_citas'), {'cuando': 'hoy'}).context['citas']), 1)
        self.assertEqual(len(self.client.get(reverse('mascotas:lista_citas'), {'cuando': 'pasadas'}).context['citas']), 1)
        r = self.client.get(reverse('mascotas:ficha', args=[self.m.pk]))
        self.assertEqual(r.status_code, 200)
        tipos = [e['tipo'] for e in r.context['eventos']]
        self.assertEqual(tipos, ['cita', 'historial', 'cita', 'vacuna'])
        self.assertContains(r, 'Otitis')
        r = self.client.get(reverse('mascotas:crear_vacuna') + f'?mascota={self.m.pk}')
        self.assertEqual(r.context['form'].initial['mascota'], str(self.m.pk))

    def test_cliente_no_ve_ficha_ajena(self):
        cli = User.objects.create_user('cli', password='clave12345')
        d = Dueño.objects.create(user=cli, nombre='Ana', email='a@x.cl')
        self.m.dueno = d
        self.m.save()
        self.client.login(username='cli', password='clave12345')
        self.assertEqual(self.client.get(reverse('mascotas:ficha', args=[self.m.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('mascotas:ficha', args=[self.m2.pk])).status_code, 404)


class AlertasYCarnetTest(TestCase):
    """JO3: alertas de vacunación, correo y carnet PDF."""

    def setUp(self):
        self.root = User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        cli = User.objects.create_user('cli', password='clave12345')
        self.d = Dueño.objects.create(user=cli, nombre='Ana Soto', email='ana@x.cl')
        self.m = Mascota.objects.create(nombre='Toby', especie='Perro', edad=3, dueno=self.d)
        self.m2 = Mascota.objects.create(nombre='Nube', especie='Gato', edad=3)
        self.alerg = Mascota.objects.create(nombre='Copito', especie='Conejo', edad=1, alergico=True)
        self.client.login(username='root', password='clave12345')

    def test_form(self):
        base = {'mascota': self.m2.pk, 'tipo': 'rabia', 'fecha_aplicacion': hoy.isoformat()}
        self.assertContains(self.client.post(reverse('mascotas:crear_vacuna'), dict(base, fecha_aplicacion=(hoy+timedelta(1)).isoformat())), 'fecha futura')
        self.assertContains(self.client.post(reverse('mascotas:crear_vacuna'), dict(base, proxima_dosis=hoy.isoformat())), 'posterior')
        self.assertContains(self.client.post(reverse('mascotas:crear_vacuna'), dict(base, mascota=self.alerg.pk)), 'alérgica')
        r = self.client.post(reverse('mascotas:crear_vacuna'), dict(base, lote=' l-22 '))
        self.assertEqual(r.status_code, 302)
        self.m2.refresh_from_db()
        self.assertTrue(self.m2.vacunado)
        self.assertEqual(Vacuna.objects.get().lote, 'L-22')

    def test_alertas_y_correo(self):
        # Dosis antigua de rabia cuyo refuerzo ya se aplicó: no debe alertar.
        Vacuna.objects.create(mascota=self.m, tipo='rabia', fecha_aplicacion=hoy-timedelta(400), proxima_dosis=hoy-timedelta(35))
        Vacuna.objects.create(mascota=self.m, tipo='rabia', fecha_aplicacion=hoy-timedelta(30), proxima_dosis=hoy+timedelta(335))  # refuerzo ya puesto
        venc = Vacuna.objects.create(mascota=self.m, tipo='triple_virus', fecha_aplicacion=hoy-timedelta(380), proxima_dosis=hoy-timedelta(15))
        prox = Vacuna.objects.create(mascota=self.m2, tipo='rabia', fecha_aplicacion=hoy-timedelta(350), proxima_dosis=hoy+timedelta(10))
        r = self.client.get(reverse('mascotas:alertas_vacunas'))
        self.assertEqual([v.pk for v in r.context['vencidas']], [venc.pk])
        self.assertEqual([v.pk for v in r.context['proximas']], [prox.pk])
        self.assertContains(r, 'venció hace 15 día(s)')
        self.assertEqual([m.nombre for m in r.context['sin_vacunas']], [])
        r = self.client.post(reverse('mascotas:enviar_alertas_vacunas'), follow=True)
        self.assertContains(r, 'Recordatorios enviados: 1.')
        self.assertContains(r, '1 dueño(s) sin correo')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Triple virus', mail.outbox[0].body)
        call_command('enviar_alertas_vacunas')
        self.assertEqual(len(mail.outbox), 1)  # no repite
        # editar proxima dosis reinicia el aviso
        venc.refresh_from_db()
        self.assertIsNotNone(venc.alerta_enviada_el)
        self.client.post(reverse('mascotas:editar_vacuna', args=[venc.pk]), {'mascota': self.m.pk, 'tipo': 'triple_virus', 'fecha_aplicacion': venc.fecha_aplicacion.isoformat(), 'proxima_dosis': (hoy+timedelta(5)).isoformat()})
        venc.refresh_from_db()
        self.assertIsNone(venc.alerta_enviada_el)

    def test_carnet_pdf(self):
        Vacuna.objects.create(mascota=self.m, tipo='rabia', fecha_aplicacion=hoy, lote='A1')
        r = self.client.get(reverse('mascotas:carnet_vacunas', args=[self.m.pk]))
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))
        self.client.login(username='cli', password='clave12345')
        self.assertEqual(self.client.get(reverse('mascotas:carnet_vacunas', args=[self.m2.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('mascotas:enviar_alertas_vacunas')).status_code, 403)


class FacturacionTest(TestCase):
    """JO4: facturas, totales con IVA, estados y permisos."""

    def setUp(self):
        self.root = User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        self.cli = User.objects.create_user('cli', password='clave12345')
        self.d = Dueño.objects.create(user=self.cli, nombre='Ana Soto', email='a@x.cl')
        u2 = User.objects.create_user('otro', password='x')
        self.d2 = Dueño.objects.create(user=u2, nombre='Luis Paz', email='l@x.cl')
        self.m = Mascota.objects.create(nombre='Toby', especie='Perro', edad=3, dueno=self.d)
        self.m2 = Mascota.objects.create(nombre='Nube', especie='Gato', edad=3, dueno=self.d2)
        self.client.login(username='root', password='clave12345')

    def datos(self, **k):
        d = {'dueno': self.d.pk, 'mascota': self.m.pk, 'fecha': hoy.isoformat(), 'estado': 'pendiente', **mgmt(),
             'detalles-0-descripcion': 'Consulta general', 'detalles-0-cantidad': '1', 'detalles-0-precio_unitario': '15000',
             'detalles-1-descripcion': 'Vacuna rabia', 'detalles-1-cantidad': '2', 'detalles-1-precio_unitario': '8000'}
        d.update(k)
        return d

    def test_crear_y_totales(self):
        self.assertEqual(self.client.get(reverse('mascotas:crear_factura') + f'?mascota={self.m.pk}').context['form'].initial['dueno'], self.d.pk)
        r = self.client.post(reverse('mascotas:crear_factura'), self.datos())
        self.assertEqual(r.status_code, 302, r.content[:3000] if r.status_code==200 else '')
        f = Factura.objects.get()
        self.assertEqual((f.neto, f.iva, f.total), (31000, 5890, 36890))
        r = self.client.get(reverse('mascotas:detalle_factura', args=[f.pk]))
        self.assertContains(r, '$36.890')
        self.assertContains(self.client.get(reverse('mascotas:lista_facturas')), '$36.890')

    def test_validaciones(self):
        self.assertContains(self.client.post(reverse('mascotas:crear_factura'), self.datos(mascota=self.m2.pk)), 'no pertenece')
        self.assertContains(self.client.post(reverse('mascotas:crear_factura'), self.datos(estado='pagada')), 'con qué se pagó')
        vacio = self.datos(**{'detalles-0-descripcion': '', 'detalles-0-precio_unitario': '', 'detalles-1-descripcion': '', 'detalles-1-cantidad': '', 'detalles-1-precio_unitario': '', 'detalles-0-cantidad': ''})
        r = self.client.post(reverse('mascotas:crear_factura'), vacio)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Factura.objects.exists())
        self.assertContains(self.client.post(reverse('mascotas:crear_factura'), self.datos(**{'detalles-0-precio_unitario': '-5'})), 'Revisa')
        self.assertContains(self.client.post(reverse('mascotas:crear_factura'), self.datos(fecha=(hoy+timedelta(3)).isoformat())), 'fecha futura')

    def test_estados_y_permisos(self):
        self.client.post(reverse('mascotas:crear_factura'), self.datos())
        f = Factura.objects.get()
        self.client.post(reverse('mascotas:estado_factura', args=[f.pk]), {'accion': 'pagar', 'metodo_pago': 'debito'})
        f.refresh_from_db()
        self.assertEqual((f.estado, f.metodo_pago, f.fecha_pago), ('pagada', 'debito', hoy))
        r = self.client.get(reverse('mascotas:eliminar_factura', args=[f.pk]), follow=True)
        self.assertContains(r, 'Primero anula')
        f2 = Factura.objects.create(dueno=self.d2)
        DetalleFactura.objects.create(factura=f2, descripcion='xx x', precio_unitario=100)
        self.client.post(reverse('mascotas:estado_factura', args=[f2.pk]), {'accion': 'anular'})
        r = self.client.get(reverse('mascotas:editar_factura', args=[f2.pk]), follow=True)
        self.assertContains(r, 'anulada no se puede')
        self.client.post(reverse('mascotas:eliminar_factura', args=[f2.pk]))
        self.assertFalse(Factura.objects.filter(pk=f2.pk).exists())
        # editar existente con formset
        r = self.client.get(reverse('mascotas:editar_factura', args=[f.pk]))
        self.assertEqual(r.status_code, 200)
        self.cli.user_permissions.add(Permission.objects.get(codename='view_factura'))
        Factura.objects.create(dueno=self.d2)
        self.client.login(username='cli', password='clave12345')
        self.assertEqual(len(self.client.get(reverse('mascotas:lista_facturas')).context['facturas']), 1)
        self.assertEqual(self.client.get(reverse('mascotas:crear_factura')).status_code, 403)
        self.assertEqual(formato_clp(1234567), '$1.234.567')

    def test_admin(self):
        f = Factura.objects.create(dueno=self.d)
        for url in ['/admin/mascotas/factura/', f'/admin/mascotas/factura/{f.pk}/change/', '/admin/mascotas/factura/add/']:
            self.assertEqual(self.client.get(url).status_code, 200, url)


class DashboardYReportesTest(TestCase):
    """JO5: dashboard e informes CSV."""

    def setUp(self):
        self.root = User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        self.cli = User.objects.create_user('cli', password='clave12345')
        self.d = Dueño.objects.create(user=self.cli, nombre='Ana Muñoz', email='a@x.cl')
        self.m = Mascota.objects.create(nombre='Toby', especie='Perro', edad=3, dueno=self.d)
        Mascota.objects.create(nombre='Ñandú', especie='Ave', edad=1, alergico=True)
        Cita.objects.create(mascota=self.m, veterinario='Dr X', fecha=hoy, hora=time(10))
        f = Factura.objects.create(dueno=self.d, estado='pagada', metodo_pago='debito', fecha=hoy)
        DetalleFactura.objects.create(factura=f, descripcion='Consulta', precio_unitario=10000)
        f2 = Factura.objects.create(dueno=self.d, fecha=hoy)
        DetalleFactura.objects.create(factura=f2, descripcion='Vac', precio_unitario=5000)

    def test_dashboard(self):
        self.client.login(username='root', password='clave12345')
        r = self.client.get('/', follow=True)
        self.assertEqual(r.resolver_match.url_name, 'dashboard')
        self.assertEqual(r.context['total_mascotas'], 2)
        self.assertEqual(len(r.context['citas_hoy']), 1)
        self.assertEqual(r.context['ingreso_mes'], 11900)
        self.assertEqual(r.context['por_cobrar'], 5950)
        self.assertContains(r, '$11.900')
        self.assertEqual(len(r.context['ingresos']), 6)

    def test_cliente_dashboard_sin_facturacion(self):
        self.cli.user_permissions.add(Permission.objects.get(codename='view_cita'))
        self.client.login(username='cli', password='clave12345')
        r = self.client.get(reverse('mascotas:dashboard'))
        self.assertEqual(r.context['total_mascotas'], 1)
        self.assertNotIn('ingresos', r.context)
        self.assertNotContains(r, 'Ingresos pagados')

    def test_csv(self):
        self.client.login(username='root', password='clave12345')
        r = self.client.get(reverse('mascotas:reporte_mascotas'), {'estado': 'alergia'})
        txt = r.content.decode('utf-8-sig')
        self.assertIn('Ñandú;Ave', txt)
        self.assertNotIn('Toby', txt)
        r = self.client.get(reverse('mascotas:reporte_facturas'), {'mes': hoy.strftime('%Y-%m')})
        txt = r.content.decode('utf-8-sig')
        self.assertIn('Ana Muñoz', txt)
        self.assertEqual(len(txt.strip().splitlines()), 3)
        self.client.login(username='cli', password='clave12345')
        self.assertEqual(self.client.get(reverse('mascotas:reporte_facturas')).status_code, 403)
        self.assertNotIn('Ñandú', self.client.get(reverse('mascotas:reporte_mascotas')).content.decode('utf-8-sig'))


class RolesYPermisosTest(TestCase):
    """GA2: grupos Administradores/Veterinarios/Clientes y filtro por dueño."""

    def setUp(self):
        call_command('setup_grupos', verbosity=0)
        self.vet = User.objects.create_user('vet', password='clave12345', is_staff=True)
        self.vet.groups.add(Group.objects.get(name='Veterinarios'))
        self.cli = User.objects.create_user('cli', password='clave12345')
        self.cli.groups.add(Group.objects.get(name='Clientes'))
        d = Dueño.objects.create(user=self.cli, nombre='Ana', email='a@x.cl')
        self.m = Mascota.objects.create(nombre='Toby', especie='Perro', edad=3, dueno=d)
        self.m2 = Mascota.objects.create(nombre='Luna', especie='Gato', edad=3)
        Vacuna.objects.create(mascota=self.m2, tipo='rabia', fecha_aplicacion=hoy)

    def test_vet(self):
        self.client.login(username='vet', password='clave12345')
        r = self.client.get(reverse('mascotas:lista'))
        self.assertEqual(len(r.context['mascotas']), 2)
        self.assertContains(r, '>Veterinario')
        self.assertEqual(len(self.client.get(reverse('mascotas:lista_vacunas')).context['vacunas']), 1)
        r = self.client.get('/admin/mascotas/vacuna/')
        self.assertContains(r, 'Luna')
        r = self.client.post('/admin/mascotas/vacuna/add/', {'mascota': self.m.pk, 'tipo': 'rabia', 'fecha_aplicacion': hoy.isoformat()})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Vacuna.objects.count(), 2)
        self.assertEqual(self.client.get(reverse('mascotas:crear')).status_code, 403)

    def test_cli(self):
        self.client.login(username='cli', password='clave12345')
        r = self.client.get(reverse('mascotas:lista'))
        self.assertEqual([m.nombre for m in r.context['mascotas']], ['Toby'])
        self.assertContains(r, '>Cliente')
        self.assertEqual(len(self.client.get(reverse('mascotas:lista_vacunas')).context['vacunas']), 0)

    def test_admin_dueno(self):
        User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        self.client.login(username='root', password='clave12345')
        self.assertContains(self.client.get('/admin/mascotas/dueño/'), 'Ana')


class InventarioTest(TestCase):
    """GA3: inventario con semáforo y ajuste de stock."""

    def setUp(self):
        self.root = User.objects.create_superuser('root', 'r@x.cl', 'clave12345')
        self.client.login(username='root', password='clave12345')
        self.verde = Producto.objects.create(nombre='Alimento', stock=50, stock_minimo=10)
        self.amar = Producto.objects.create(nombre='Gasas', stock=8, stock_minimo=10)
        self.rojo = Producto.objects.create(nombre='Amoxicilina', stock=4, stock_minimo=10)
        self.venc = Producto.objects.create(nombre='Suero', stock=50, stock_minimo=10, fecha_vencimiento=hoy-timedelta(1))
        self.pv = Producto.objects.create(nombre='Vacuna X', stock=50, stock_minimo=10, fecha_vencimiento=hoy+timedelta(10))

    def test_semaforo(self):
        self.assertEqual([p.semaforo for p in (self.verde, self.amar, self.rojo, self.venc, self.pv)], ['verde','amarillo','rojo','rojo','amarillo'])
        r = self.client.get(reverse('mascotas:inventario'))
        self.assertEqual(r.context['conteo'], {'rojo': 2, 'amarillo': 2, 'verde': 1})
        self.assertEqual(r.context['productos'][0].semaforo, 'rojo')
        self.assertEqual(len(self.client.get(reverse('mascotas:inventario'), {'semaforo': 'rojo'}).context['productos']), 2)
        self.assertEqual(self.client.get(reverse('mascotas:dashboard')).context['productos_rojo'], 2)

    def test_stock(self):
        url = reverse('mascotas:ajustar_stock', args=[self.rojo.pk])
        self.client.post(url, {'tipo': 'entrada', 'cantidad': 20})
        self.rojo.refresh_from_db()
        self.assertEqual(self.rojo.stock, 24)
        r = self.client.post(url, {'tipo': 'salida', 'cantidad': 100}, follow=True)
        self.assertContains(r, 'No hay stock suficiente')
        self.client.post(url, {'tipo': 'salida', 'cantidad': 24})
        self.rojo.refresh_from_db()
        self.assertEqual(self.rojo.stock, 0)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_crud_y_admin(self):
        r = self.client.post(reverse('mascotas:crear_producto'), {'nombre': 'Gasas', 'categoria': 'insumo', 'stock': 1, 'stock_minimo': 1, 'unidad': 'caja', 'precio_venta': 100})
        self.assertContains(r, 'Ya existe')
        r = self.client.post(reverse('mascotas:crear_producto'), {'nombre': 'Jeringas', 'categoria': 'insumo', 'stock': 1, 'stock_minimo': 0, 'unidad': 'caja', 'precio_venta': 100})
        self.assertContains(r, 'al menos 1')
        r = self.client.post(reverse('mascotas:crear_producto'), {'nombre': 'Jeringas', 'categoria': 'insumo', 'stock': 1, 'stock_minimo': 3, 'unidad': ' CAJA ', 'precio_venta': 100, 'activo': 'on'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Producto.objects.get(nombre='Jeringas').unidad, 'caja')
        for u in ['/admin/mascotas/producto/', '/admin/mascotas/producto/?semaforo=rojo', f'/admin/mascotas/producto/{self.rojo.pk}/change/']:
            self.assertEqual(self.client.get(u).status_code, 200, u)

    def test_permisos(self):
        call_command('setup_grupos', verbosity=0)
        vet = User.objects.create_user('vet', password='clave12345')
        vet.groups.add(Group.objects.get(name='Veterinarios'))
        cli = User.objects.create_user('cli', password='clave12345')
        cli.groups.add(Group.objects.get(name='Clientes'))
        self.client.login(username='vet', password='clave12345')
        self.assertEqual(self.client.get(reverse('mascotas:inventario')).status_code, 200)
        self.assertEqual(self.client.get(reverse('mascotas:crear_producto')).status_code, 403)
        self.client.login(username='cli', password='clave12345')
        self.assertEqual(self.client.get(reverse('mascotas:inventario')).status_code, 403)


class SeedDemoTest(TestCase):
    """GA4: el comando de datos de demostración funciona y no duplica."""

    def test_seed_demo_idempotente(self):
        from io import StringIO
        call_command('seed_demo', password='ClaveDemo12345', stdout=StringIO())
        call_command('seed_demo', password='ClaveDemo12345', stdout=StringIO())
        self.assertEqual(Factura.objects.count(), 2)
        self.assertEqual(Producto.objects.count(), 4)
        cliente = User.objects.get(username='cliente_demo')
        self.assertTrue(self.client.login(username='cliente_demo', password='ClaveDemo12345'))
        respuesta = self.client.get(reverse('mascotas:lista'))
        self.assertEqual(
            sorted(m.nombre for m in respuesta.context['mascotas']),
            sorted(m.nombre for m in Mascota.objects.filter(dueno__user=cliente)),
        )
        self.assertEqual(len(respuesta.context['mascotas']), 2)
