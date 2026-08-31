from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from .models import Mascota


class MascotaModelTest(TestCase):
    def test_str_devuelve_nombre(self):
        mascota = Mascota.objects.create(
            nombre='Firulais', especie='Perro', edad=3, vacunado=True
        )
        self.assertEqual(str(mascota), 'Firulais')

    def test_orden_alfabetico_por_nombre(self):
        Mascota.objects.create(nombre='Zeus', especie='Perro', edad=2, vacunado=True)
        Mascota.objects.create(nombre='Bigotes', especie='Gato', edad=1, vacunado=False)
        nombres = list(Mascota.objects.values_list('nombre', flat=True))
        self.assertEqual(nombres, sorted(nombres))

    def test_estado_vacunacion(self):
        al_dia = Mascota.objects.create(nombre='Rocky', especie='Perro', edad=4, vacunado=True)
        pendiente = Mascota.objects.create(nombre='Michi', especie='Gato', edad=2, vacunado=False)
        alergico = Mascota.objects.create(
            nombre='Copito', especie='Conejo', edad=1, vacunado=False, alergico=True
        )
        self.assertEqual(al_dia.estado_vacunacion, 'al_dia')
        self.assertEqual(pendiente.estado_vacunacion, 'pendiente')
        self.assertEqual(alergico.estado_vacunacion, 'alergia')


class MascotaListViewTest(TestCase):
    def setUp(self):
        self.veterinario = User.objects.create_user(username='vet', password='clave12345')
        content_type = ContentType.objects.get_for_model(Mascota)
        ver = Permission.objects.get(content_type=content_type, codename='view_mascota')
        self.veterinario.user_permissions.add(ver)

        Mascota.objects.create(nombre='Firulais', especie='Perro', edad=3, vacunado=True)
        Mascota.objects.create(nombre='Michi', especie='Gato', edad=2, vacunado=False)
        Mascota.objects.create(nombre='Loro Perico', especie='Loro', edad=1, vacunado=False)

    def test_requiere_login(self):
        response = self.client.get(reverse('mascotas:lista'))
        self.assertEqual(response.status_code, 302)

    def test_veterinario_puede_ver_lista_completa(self):
        self.client.login(username='vet', password='clave12345')
        response = self.client.get(reverse('mascotas:lista'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['mascotas']), 3)

    def test_busqueda_por_nombre(self):
        self.client.login(username='vet', password='clave12345')
        response = self.client.get(reverse('mascotas:lista'), {'q': 'Michi'})
        nombres = [m.nombre for m in response.context['mascotas']]
        self.assertEqual(nombres, ['Michi'])

    def test_filtro_por_especie(self):
        self.client.login(username='vet', password='clave12345')
        response = self.client.get(reverse('mascotas:lista'), {'especie': 'Gato'})
        nombres = [m.nombre for m in response.context['mascotas']]
        self.assertEqual(nombres, ['Michi'])

    def test_filtro_pendientes_de_vacuna(self):
        self.client.login(username='vet', password='clave12345')
        response = self.client.get(reverse('mascotas:lista'), {'estado': 'pendiente'})
        nombres = sorted(m.nombre for m in response.context['mascotas'])
        self.assertEqual(nombres, ['Loro Perico', 'Michi'])

    def test_filtro_alergia_excluye_a_los_no_alergicos(self):
        self.client.login(username='vet', password='clave12345')
        Mascota.objects.create(nombre='Copito', especie='Conejo', edad=1, alergico=True)
        response = self.client.get(reverse('mascotas:lista'), {'estado': 'alergia'})
        nombres = [m.nombre for m in response.context['mascotas']]
        self.assertEqual(nombres, ['Copito'])

    def test_total_pendientes_no_cuenta_alergicos(self):
        Mascota.objects.create(nombre='Copito', especie='Conejo', edad=1, alergico=True)
        self.client.login(username='vet', password='clave12345')
        response = self.client.get(reverse('mascotas:lista'))
        # Pendientes sin contar a Copito (alérgico, no puede vacunarse)
        self.assertEqual(response.context['total_pendientes'], 2)

    def test_veterinario_sin_permiso_no_ve_boton_crear(self):
        self.client.login(username='vet', password='clave12345')
        response = self.client.get(reverse('mascotas:lista'))
        self.assertNotContains(response, 'Nueva mascota')

    def test_superusuario_sin_grupo_ve_insignia_administrador(self):
        User.objects.create_superuser(username='root', password='clave12345', email='root@x.com')
        self.client.login(username='root', password='clave12345')
        response = self.client.get(reverse('mascotas:lista'))
        self.assertContains(response, 'bg-primary ms-1">Administrador')
        self.assertNotContains(response, 'bg-secondary ms-1">Veterinario')


class MascotaPermisosTest(TestCase):
    def setUp(self):
        self.veterinario = User.objects.create_user(username='vet2', password='clave12345')
        self.administrador = User.objects.create_user(username='admin2', password='clave12345')

        content_type = ContentType.objects.get_for_model(Mascota)
        ver = Permission.objects.get(content_type=content_type, codename='view_mascota')
        crear = Permission.objects.get(content_type=content_type, codename='add_mascota')
        editar = Permission.objects.get(content_type=content_type, codename='change_mascota')

        self.veterinario.user_permissions.add(ver)
        self.administrador.user_permissions.add(ver, crear, editar)

        self.mascota = Mascota.objects.create(
            nombre='Rocky', especie='Perro', edad=4, vacunado=False
        )

    def test_veterinario_no_puede_crear(self):
        self.client.login(username='vet2', password='clave12345')
        response = self.client.get(reverse('mascotas:crear'))
        self.assertEqual(response.status_code, 403)

    def test_administrador_puede_crear(self):
        self.client.login(username='admin2', password='clave12345')
        response = self.client.post(reverse('mascotas:crear'), {
            'nombre': 'Nueva Mascota',
            'especie': 'Conejo',
            'edad': 1,
            'vacunado': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Mascota.objects.filter(nombre='Nueva Mascota').exists())

    def test_administrador_puede_editar_estado_vacunacion(self):
        self.client.login(username='admin2', password='clave12345')
        response = self.client.post(
            reverse('mascotas:editar', args=[self.mascota.pk]),
            {'nombre': 'Rocky', 'especie': 'Perro', 'edad': 4, 'vacunado': True},
        )
        self.assertEqual(response.status_code, 302)
        self.mascota.refresh_from_db()
        self.assertTrue(self.mascota.vacunado)


class SetupGruposCommandTest(TestCase):
    def test_comando_crea_grupos_con_permisos_correctos(self):
        from django.core.management import call_command

        call_command('setup_grupos')

        veterinarios = Group.objects.get(name='Veterinarios')
        administradores = Group.objects.get(name='Administradores')

        self.assertEqual(
            set(veterinarios.permissions.values_list('codename', flat=True)),
            {'view_mascota'},
        )
        self.assertEqual(
            set(administradores.permissions.values_list('codename', flat=True)),
            {'view_mascota', 'add_mascota', 'change_mascota', 'delete_mascota'},
        )
