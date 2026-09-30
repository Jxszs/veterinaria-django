from django.urls import path

from . import views

app_name = 'mascotas'

urlpatterns = [
    # ── Mascotas ──
    path('', views.listar_mascotas, name='lista'),
    path('nueva/', views.crear_mascota, name='crear'),
    path('<int:pk>/editar/', views.editar_mascota, name='editar'),
    path('<int:pk>/eliminar/', views.eliminar_mascota, name='eliminar'),
    path('<int:pk>/', views.ficha_mascota, name='ficha'),
    path('<int:pk>/carnet.pdf', views.carnet_vacunas, name='carnet_vacunas'),

    # ── Dueños (JO1) ──
    path('duenos/', views.listar_duenos, name='lista_duenos'),
    path('duenos/nuevo/', views.crear_dueno, name='crear_dueno'),
    path('duenos/<int:pk>/editar/', views.editar_dueno, name='editar_dueno'),
    path('duenos/<int:pk>/eliminar/', views.eliminar_dueno, name='eliminar_dueno'),

    # ── Citas ──
    path('citas/', views.listar_citas, name='lista_citas'),
    path('citas/nueva/', views.crear_cita, name='crear_cita'),
    path('citas/<int:pk>/editar/', views.editar_cita, name='editar_cita'),
    path('citas/<int:pk>/eliminar/', views.eliminar_cita, name='eliminar_cita'),
    path('citas/<int:pk>/cancelar/', views.cancelar_cita, name='cancelar_cita'),

    # ── Historial Médico ──
    path('historial/', views.listar_historial, name='lista_historial'),
    path('historial/nuevo/', views.crear_historial, name='crear_historial'),
    path('historial/<int:pk>/editar/', views.editar_historial, name='editar_historial'),
    path('historial/<int:pk>/eliminar/', views.eliminar_historial, name='eliminar_historial'),

    # ── Vacunas ──
    path('vacunas/', views.listar_vacunas, name='lista_vacunas'),
    path('vacunas/nueva/', views.crear_vacuna, name='crear_vacuna'),
    path('vacunas/alertas/', views.alertas_vacunas, name='alertas_vacunas'),
    path('vacunas/alertas/enviar/', views.enviar_alertas_vacunas, name='enviar_alertas_vacunas'),
    path('vacunas/<int:pk>/editar/', views.editar_vacuna, name='editar_vacuna'),
    path('vacunas/<int:pk>/eliminar/', views.eliminar_vacuna, name='eliminar_vacuna'),

    # ── Facturación (JO4) ──
    path('facturas/', views.listar_facturas, name='lista_facturas'),
    path('facturas/nueva/', views.crear_factura, name='crear_factura'),
    path('facturas/<int:pk>/', views.detalle_factura, name='detalle_factura'),
    path('facturas/<int:pk>/editar/', views.editar_factura, name='editar_factura'),
    path('facturas/<int:pk>/estado/', views.cambiar_estado_factura, name='estado_factura'),
    path('facturas/<int:pk>/eliminar/', views.eliminar_factura, name='eliminar_factura'),

    # ── Recetas ──
    path('recetas/', views.listar_recetas, name='recetas'),
    path('recetas/nueva/', views.crear_receta, name='crear_receta'),
    path('recetas/<int:pk>/editar/', views.editar_receta, name='editar_receta'),
    path('recetas/<int:pk>/eliminar/', views.eliminar_receta, name='eliminar_receta'),
    path('recetas/<int:pk>/avisar/', views.avisar_receta_lista, name='avisar_receta'),

    # ── Dashboard y reportes (JO5) ──
    path('panel/', views.dashboard, name='dashboard'),
    path('reportes/mascotas.csv', views.reporte_mascotas_csv, name='reporte_mascotas'),
    path('reportes/facturas.csv', views.reporte_facturas_csv, name='reporte_facturas'),

    # ── Inventario con semáforo (GA3) ──
    path('inventario/', views.listar_inventario, name='inventario'),
    path('inventario/nuevo/', views.crear_producto, name='crear_producto'),
    path('inventario/<int:pk>/editar/', views.editar_producto, name='editar_producto'),
    path('inventario/<int:pk>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('inventario/<int:pk>/stock/', views.ajustar_stock, name='ajustar_stock'),
]
