from datetime import time, timedelta

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from mascotas.models import Cita, DetalleFactura, Dueño, Factura, HistorialMedico, Mascota, Producto, Vacuna


class Command(BaseCommand):
    """
    Carga datos de demostración para la presentación (GA4):

    - Grupos y 6 mascotas de ejemplo (llama a setup_grupos y seed_mascotas).
    - Usuarios "veterinario_demo" (grupo Veterinarios) y "cliente_demo"
      (grupo Clientes, con perfil de dueño y 2 mascotas).
    - Citas de hoy y mañana, vacunas con refuerzo vencido y próximo,
      historial médico, una factura pagada y otra pendiente.
    - Productos de inventario en rojo, amarillo y verde.

    Uso:
        python manage.py seed_demo --password "UnaClaveSegura123"

    Se puede ejecutar varias veces: no duplica datos.
    No usar en la base de producción con datos reales.
    """
    help = 'Carga usuarios y datos de demostración para probar todas las funcionalidades.'

    def add_arguments(self, parser):
        parser.add_argument('--password', required=True,
                            help='Contraseña para los usuarios veterinario_demo y cliente_demo.')

    @transaction.atomic
    def handle(self, *args, **options):
        call_command('setup_grupos', verbosity=0)
        call_command('seed_mascotas', verbosity=0)
        hoy = timezone.localdate()

        veterinario = self._usuario('veterinario_demo', options['password'], 'Veterinarios')
        cliente = self._usuario('cliente_demo', options['password'], 'Clientes')
        dueno, _ = Dueño.objects.get_or_create(
            user=cliente,
            defaults={'nombre': 'Carolina Muñoz', 'email': 'cliente_demo@example.com', 'telefono': '+56911112222'},
        )
        firulais = Mascota.objects.get(nombre='Firulais')
        michi = Mascota.objects.get(nombre='Michi')
        Mascota.objects.filter(pk__in=[firulais.pk, michi.pk]).update(dueno=dueno)

        Cita.objects.get_or_create(mascota=firulais, fecha=hoy, hora=time(10, 30),
                                   defaults={'veterinario': 'Dra. Rojas', 'motivo': 'Control anual'})
        Cita.objects.get_or_create(mascota=michi, fecha=hoy + timedelta(days=1), hora=time(16, 0),
                                   defaults={'veterinario': 'Dr. Pérez', 'motivo': 'Vacunación'})

        Vacuna.objects.get_or_create(
            mascota=firulais, tipo='antirrabica', fecha_aplicacion=hoy - timedelta(days=380),
            defaults={'proxima_dosis': hoy - timedelta(days=15), 'lote': 'AR-2025-01', 'fabricante': 'Zoetis'},
        )
        Vacuna.objects.get_or_create(
            mascota=Mascota.objects.get(nombre='Luna'), tipo='triple_virus', fecha_aplicacion=hoy - timedelta(days=350),
            defaults={'proxima_dosis': hoy + timedelta(days=15), 'lote': 'TV-88', 'fabricante': 'MSD'},
        )
        HistorialMedico.objects.get_or_create(
            mascota=firulais, fecha=hoy - timedelta(days=20),
            defaults={'veterinario': 'Dra. Rojas', 'diagnostico': 'Otitis leve',
                      'tratamiento': 'Gotas óticas cada 12 horas por 7 días'},
        )

        if not dueno.facturas.exists():
            pagada = Factura.objects.create(dueno=dueno, mascota=firulais, estado='pagada',
                                            metodo_pago='debito', fecha_pago=hoy)
            DetalleFactura.objects.create(factura=pagada, descripcion='Consulta general', precio_unitario=15000)
            DetalleFactura.objects.create(factura=pagada, descripcion='Gotas óticas', cantidad=1, precio_unitario=8500)
            pendiente = Factura.objects.create(dueno=dueno, mascota=michi)
            DetalleFactura.objects.create(factura=pendiente, descripcion='Vacuna triple felina', precio_unitario=12000)

        productos = [
            ('Amoxicilina 250 mg', 'medicamento', 2, 10, None),
            ('Gasas estériles', 'insumo', 8, 10, None),
            ('Vacuna antirrábica', 'vacuna', 30, 10, hoy + timedelta(days=20)),
            ('Alimento renal 2 kg', 'alimento', 25, 5, hoy + timedelta(days=200)),
        ]
        for nombre, categoria, stock, minimo, vence in productos:
            Producto.objects.get_or_create(nombre=nombre, defaults={
                'categoria': categoria, 'stock': stock, 'stock_minimo': minimo,
                'fecha_vencimiento': vence, 'precio_venta': 5000,
            })

        self.stdout.write(self.style.SUCCESS('Datos de demostración listos.'))
        self.stdout.write(f'Usuarios: {veterinario.username} (Veterinarios) y {cliente.username} (Clientes).')

    def _usuario(self, username, password, grupo):
        usuario, creado = User.objects.get_or_create(username=username)
        if creado:
            usuario.set_password(password)
            usuario.save()
        usuario.groups.add(Group.objects.get(name=grupo))
        return usuario
