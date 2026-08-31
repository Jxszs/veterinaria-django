# Sistema de Pacientes - Clínica Veterinaria

Proyecto Django que resuelve el **Caso 5** de la evaluación: un sistema web
para que la clínica gestione a sus mascotas/pacientes.

## Qué implementa

- **Modelo `Mascota`** (`mascotas/models.py`): 4 campos base, con los 4 tipos
  de dato del repaso de conceptos del curso — `nombre` (CharField), `especie`
  (CharField), `edad` (IntegerField) y `vacunado` (BooleanField) — ordenado
  alfabéticamente por nombre. Se suma un 5to campo `alergico` (BooleanField)
  para representar el tercer estado de vacunación que pide el enunciado del
  Caso 5 ("alergia a vacunas") sin romper la combinación de tipos exigida en
  los 4 campos base. La propiedad `estado_vacunacion` combina ambos booleanos
  en `'al_dia'`, `'pendiente'` o `'alergia'`.
- **Lista web** de todas las mascotas, con:
  - Colores según estado: verde (al día), rojo (pendiente de vacuna),
    amarillo (alergia — no se le puede vacunar).
  - Buscador por nombre (para cuando llama el dueño).
  - Filtro por especie.
  - Filtro por estado de vacunación (al día / pendiente / alergia).
  - Aviso/filtro rápido de "mascotas pendientes de vacuna" (no cuenta a las
    alérgicas, porque a esas no corresponde vacunarlas).
- **Alta, edición y eliminación** de mascotas mediante formularios web (sin
  tocar código), disponibles solo para el grupo **Administradores**.
- **Permisos**: el grupo **Veterinarios** solo puede ver la lista; el grupo
  **Administradores** puede ver, crear, editar y eliminar. Se implementa con
  el sistema de permisos y grupos nativo de Django
  (`@login_required` + `@permission_required`).
- **Vistas por función** en `mascotas/views.py` (`listar_mascotas`,
  `crear_mascota`, `editar_mascota`, `eliminar_mascota`): cada una consulta
  con `Mascota.objects.all()`/`.filter()`, arma un diccionario de contexto y
  llama a `render()`.
- **Panel de administración** (`/admin/`) con búsqueda y filtros, además de
  la interfaz pública en `/mascotas/`.

## Cómo correrlo

```bash
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser        # crea tu usuario administrador
python manage.py setup_grupos           # crea los grupos Veterinarios/Administradores
python manage.py seed_mascotas          # carga 6 mascotas de ejemplo, incluida 1 alérgica (la rúbrica pide 5+)

python manage.py runserver
```

Abre `http://127.0.0.1:8000/` (redirige a `/mascotas/`).

## Asignar roles a usuarios

1. Entra a `/admin/` con el superusuario.
2. Ve a **Usuarios** → elige o crea un usuario → sección **Grupos**.
3. Asígnale **Veterinarios** (solo ver) o **Administradores** (control total).
4. Un superusuario siempre tiene acceso completo, sin importar el grupo.

## Pruebas

```bash
python manage.py test mascotas
```

Incluye pruebas del modelo, de la lista (búsqueda, filtros), y de permisos
(quién puede crear/editar y quién no).

## Estructura relevante

```
mascotas/
  models.py          # Modelo Mascota
  forms.py           # Formulario de alta/edición
  views.py           # Listar, crear, editar, eliminar (con permisos)
  urls.py            # Rutas de la app
  admin.py           # Panel de administración
  management/commands/setup_grupos.py   # Crea grupos Veterinarios/Administradores
  management/commands/seed_mascotas.py  # Carga 6 mascotas de ejemplo
  templates/
    base.html
    mascotas/mascota_list.html
    mascotas/mascota_form.html
    mascotas/mascota_confirm_delete.html
    registration/login.html
  tests.py
veterinaria/
  settings.py        # LOGIN_URL, LOGIN_REDIRECT_URL, etc.
  urls.py            # Incluye mascotas.urls y accounts (login/logout)
```
