from django.urls import path

from . import views

app_name = 'mascotas'

urlpatterns = [
    path('', views.listar_mascotas, name='lista'),
    path('nueva/', views.crear_mascota, name='crear'),
    path('<int:pk>/editar/', views.editar_mascota, name='editar'),
    path('<int:pk>/eliminar/', views.eliminar_mascota, name='eliminar'),
]
