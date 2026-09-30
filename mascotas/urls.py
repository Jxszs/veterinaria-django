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
    path('vacunas/<int:pk>/editar/', views.editar_vacuna, name='editar_vacuna'),
    path('vacunas/<int:pk>/eliminar/', views.eliminar_vacuna, name='eliminar_vacuna'),
]
