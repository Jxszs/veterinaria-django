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
- **Modelo `Dueño`** (`mascotas/models.py`): incluye FK a `User` (el usuario
  registrado del sistema) y datos de contacto del dueño (nombre, whatsapp,
  teléfono, dirección, email). Permite vincular cada mascota a un dueño
  registrado.
- **Mascota mejorada (J7)**: ahora cada mascota tiene FK a `Dueño` (`dueno`,
  nullable) y campo `raza` (nullable). Así se puede registrar al dueño de la
  mascota y su raza sin romper registros existentes.
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
- **Manejo de errores (J5)**: las vistas de mascotas manejan `DatabaseError`
  con `try/except`, registrando con `logger` y mostrando mensaje claro al
  usuario en vez de un error 500.
- **Validaciones y sanitización (J4)**: `MascotaForm` limpia HTML, valida que
  nombre y especie sean solo letras (con regex `SOLO_LETRAS`), valida longitud
  mínima, y el modelo rechaza que una mascota sea vacunada y alérgica a la vez.
- **Panel de administración** (`/admin/`) con búsqueda y filtros, además de
  la interfaz pública en `/mascotas/`.

### Nuevos modelos (J7 + J8)

- **`Cita`** (`mascotas/models.py`): cita programada en la clínica. Campos:
  mascota (FK), veterinario (CharField), fecha (DateField), hora (TimeField),
  motivo (CharField), observaciones (TextField), estado (CharField con
  choices: programada / en_curso / finalizada / cancelada). Se pueden listar,
  crear, editar y eliminar citas.
- **`HistorialMedico`** (`mascotas/models.py`): registro del historial médico
  de una mascota. Campos: mascota (FK), fecha (DateField), diagnóstico
  (CharField), tratamiento (TextField), veterinario (CharField), notas
  (TextField). Permite registrar el historial clínico de cada mascota.
- **`Vacuna`** (`mascotas/models.py`): registro de vacunación de una mascota.
  Campos: mascota (FK), tipo (CharField con choices: multivitamínica,
  antirrábica, triple virus, COVID canino, rabia, otra), fecha_aplicacion
  (DateField), proxima_dosis (DateField nullable), lote (CharField nullable),
  fabricante (CharField nullable), observaciones (TextField nullable).

### Vistas para los nuevos modelos (J8)

- **Citas**: `listar_citas`, `crear_cita`, `editar_cita`, `eliminar_cita`
  (con permisos `@permission_required` para cada acción).
- **Historial médico**: `listar_historial`, `crear_historial`.
- **Vacunas**: `listar_vacunas`, `crear_vacuna`.

### Plantillas nuevas (J8)

- `cita_list.html`, `cita_form.html`, `cita_confirm_delete.html`
- `historial_list.html`, `historial_form.html`
- `vacuna_list.html`, `vacuna_form.html`

### Admin nuevos (J8)

- `CitaAdmin`, `HistorialMedicoAdmin`, `VacunaAdmin` registrados en
  `mascotas/admin.py` con búsqueda, filtros, ordering y date_hierarchy.

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

Incluye pruebas del modelo, de la lista (búsqueda, filtros), de permisos
(quién puede crear/editar y quién no), de validación y sanitización del
formulario, y de manejo de errores de base de datos. Se ejecutan 27 tests.

## Estructura relevante

```
mascotas/
  models.py          # Modelos: Mascota, Dueño, Cita, HistorialMedico, Vacuna
  forms.py           # Formularios: MascotaForm, CitaForm, HistorialMedicoForm, VacunaForm
  views.py           # Vistas: mascotas, citas, historial, vacunas (con permisos y manejo de errores)
  urls.py            # Rutas de la app (mascotas, citas, historial, vacunas)
  admin.py           # Panel de administración (MascotaAdmin, CitaAdmin, HistorialMedicoAdmin, VacunaAdmin)
  management/commands/setup_grupos.py   # Crea grupos Veterinarios/Administradores
  management/commands/seed_mascotas.py  # Carga 6 mascotas de ejemplo
  templates/
    base.html
    mascotas/
      mascota_list.html
      mascota_form.html
      mascota_confirm_delete.html
      cita_list.html
      cita_form.html
      cita_confirm_delete.html
      historial_list.html
      historial_form.html
      vacuna_list.html
      vacuna_form.html
    registration/login.html
  tests.py           # Tests: modelo, lista, permisos, validación, manejo de errores
veterinaria/
  settings.py        # LOGIN_URL, LOGIN_REDIRECT_URL, carga .env, DATABASE_URL, config TEST SQLite para tests
  urls.py            # Incluye mascotas.urls y accounts (login/logout)
```

## Contribuciones

Proyecto desarrollado por:
- Jesús Torres
- Joel
- Gabriel

Se dividió el trabajo en commits según acordado:
- **J1**: `.gitignore` + `requirements.txt` con python-dotenv
- **J2**: `settings.py` con carga desde `.env` + `.env.example`
- **J3**: Modelos centrales del Caso 5 (`Mascota` con validadores, `estado_vacunacion`) + migraciones + configuración Supabase
- **J4**: Sanitización y validaciones en `MascotaForm` (clean_nombre, clean_especie, regex SOLO_LETRAS, widgets, mensajes de error)
- **J5**: Manejo de errores en vistas con `DatabaseError` y `logger` (listar, crear, editar, eliminar)
- **J6**: Tests nuevos (`MascotaValidacionTest`, `ManejoErroresBDTest`) + configuración TEST SQLite para tests
- **J7**: Modelo `Dueño` (FK a User) y `Mascota` mejorada (FK `dueno`, campo `raza`)
- **J8**: Modelos `Cita`, `HistorialMedico` y `Vacuna` + vistas + templates + admin + README actualizado
