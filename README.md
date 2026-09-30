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

## Funcionalidades avanzadas — Joel (PUNTO 2)

### JO1 — Dueños y CRUD completo

- **CRUD de dueños** (`/mascotas/duenos/`): listar con buscador (nombre, correo
  o usuario), crear, editar y eliminar. Cada dueño se asocia a un `User`.
  - `DuenoForm` valida: un usuario solo puede tener un perfil de dueño, nombre
    solo con letras, teléfonos de 8 a 15 dígitos (con `+` opcional) y que exista
    al menos un medio de contacto (correo, teléfono o WhatsApp).
  - Al eliminar un dueño sus mascotas no se borran (quedan sin dueño, `SET_NULL`).
- **Mascota con dueño y raza** en el formulario web (antes solo existían en el modelo).
- **Historial médico y vacunas con CRUD completo**: se agregaron editar y
  eliminar (los botones antes apuntaban a `#`). El historial no acepta fechas
  futuras y exige al menos diagnóstico o tratamiento.
- **`mascotas/permisos.py`**: una sola regla de acceso por objeto para toda la app.
  El personal (superusuario, grupos Veterinarios/Administradores) ve todo; un
  cliente (usuario con perfil de dueño) ve solo lo de sus mascotas. Editar o
  eliminar un registro ajeno devuelve 404.
- **Ayudantes `_guardar_formulario` y `_confirmar_eliminacion`** en `views.py`:
  aplican el mismo `try/except DatabaseError` + mensajes claros en todas las
  vistas nuevas, sin repetir código.
- **Plantillas**: barra de navegación con enlaces según permisos, include
  `_campos_form.html` que ahora también muestra errores generales del
  formulario, y se quitó el doble mensaje que salía en las listas.

### JO2 — Citas avanzadas y ficha con línea de tiempo

- **Validaciones de `CitaForm`**:
  - No se puede programar ni reprogramar una cita en una fecha u hora pasada
    (editar una cita antigua sin mover la fecha sí se permite, por ejemplo para
    marcarla como finalizada).
  - Solo dentro del horario de atención (`HORA_APERTURA`–`HORA_CIERRE`, 09:00–20:00).
  - Sin choques: el mismo veterinario o la misma mascota no pueden tener dos
    citas a la misma fecha y hora (las canceladas no ocupan horario).
- **Cancelar cita** (`POST /mascotas/citas/<id>/cancelar/`): cambia el estado a
  "cancelada" en vez de borrarla, así queda en el historial. Solo acepta POST
  con token CSRF y solo cancela citas programadas o en curso.
- **Filtros en la lista de citas**: por mascota, por estado y por momento
  (hoy, próximas, pasadas).
- **Ficha de la mascota** (`/mascotas/<id>/`): datos, dueño, estado de
  vacunación, próximas citas y una **línea de tiempo** que junta citas,
  vacunas e historial médico en orden cronológico. Desde la ficha se puede
  agregar una cita, vacuna o registro con la mascota ya elegida (`?mascota=<id>`).
  Un cliente solo puede abrir la ficha de sus mascotas (otra da 404).
- Los campos de fecha ahora usan formato `AAAA-MM-DD`, para que al **editar**
  el navegador muestre la fecha guardada (antes el campo quedaba vacío).

### JO3 — Alertas de vacunación por correo y carnet PDF

- **Estado de la dosis** en el modelo `Vacuna` (`estado_dosis`,
  `dias_para_refuerzo`, `plazo_refuerzo`): vencida, próxima (dentro de
  `DIAS_AVISO_VACUNA` = 30 días), al día o sin refuerzo. La lista de vacunas
  lo muestra con etiquetas de color.
- **Página de alertas** (`/mascotas/vacunas/alertas/`): refuerzos vencidos,
  refuerzos próximos y mascotas pendientes sin ninguna vacuna. Solo cuenta la
  dosis más reciente de cada tipo (si ya se puso el refuerzo, no alerta) y
  excluye mascotas alérgicas. Un cliente solo ve las alertas de sus mascotas.
- **Recordatorios por correo**, con la misma lógica en `mascotas/alertas.py`:
  - Botón "Enviar recordatorios por correo" (solo POST + CSRF, requiere el
    permiso personalizado `mascotas.manage_vacunas`).
  - Comando `python manage.py enviar_alertas_vacunas [--simular] [--dias N]`,
    pensado para programarse una vez al día.
  - Campo nuevo `Vacuna.alerta_enviada_el` (migración `0007`) para no repetir
    el correo; si se cambia la próxima dosis, el aviso se vuelve a enviar.
  - La configuración SMTP se lee desde `.env` (`EMAIL_HOST`, `EMAIL_PORT`,
    `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`,
    `DEFAULT_FROM_EMAIL`). **Sin `EMAIL_HOST_PASSWORD` los correos se muestran
    en la consola**, así se puede probar sin cuenta de correo. Los fallos de
    envío se capturan con `try/except` y se informan con un mensaje claro.
- **Validaciones de `VacunaForm`**: sin fechas futuras, la próxima dosis debe
  ser posterior a la aplicación, no se puede vacunar a una mascota marcada
  como alérgica, y el lote se guarda en mayúsculas. Al registrar una vacuna la
  mascota queda marcada como vacunada.
- **Carnet de vacunación en PDF** (`/mascotas/<id>/carnet.pdf`, botón en la
  ficha) generado con ReportLab (`mascotas/reportes.py`). Se agregó
  `reportlab` a `requirements.txt`.

### JO4 — Facturación

- **Modelos nuevos** (migración `0008`):
  - `Factura`: dueño (FK, `PROTECT`: no se puede borrar un dueño con facturas),
    mascota y cita opcionales (FK), fecha, estado (pendiente / pagada /
    anulada), método de pago, fecha de pago y observaciones. El número se
    muestra como `F-000123`.
  - `DetalleFactura`: líneas de la factura (descripción, cantidad 1–999,
    precio unitario neto en pesos). El neto, el IVA (19 %) y el total se
    **calculan** a partir de las líneas; no se escriben a mano.
- **Formulario con varias líneas** (`inlineformset_factory`): mínimo una línea,
  las filas vacías se ignoran, y la factura con sus líneas se guarda dentro de
  `transaction.atomic()` (si algo falla no queda una factura a medias).
- **Validaciones**: la mascota debe ser del dueño elegido, la cita debe ser de
  esa mascota, sin fecha futura y una factura pagada exige método de pago.
- **Flujo de estados**: "Registrar pago" y "Anular" (solo POST + CSRF). Una
  factura anulada no se edita, y solo se pueden eliminar facturas anuladas.
- **Vistas**: lista con filtros (dueño/mascota, estado, mes) y totales por cobrar
  y pagados, detalle imprimible, crear/editar. Un cliente solo ve sus facturas.
- **Filtro de plantilla `clp`** (`mascotas/templatetags/veterinaria_extras.py`):
  muestra los montos como `$15.000`.
- **Admin** de `Factura` con las líneas de detalle en la misma pantalla.

### JO5 — Dashboard y reportes

- **Panel de inicio** (`/mascotas/panel/`, ahora es la página que se abre al
  iniciar sesión): total de mascotas, pendientes de vacuna, citas de hoy y
  próximas, refuerzos vencidos/próximos, agenda del día, gráfico de barras
  del estado de vacunación y de mascotas por especie.
- **Ingresos**: pagado en el mes, total por cobrar y barras de los últimos 6
  meses. Este bloque solo aparece a quien tiene el permiso `view_factura`.
- Todo el panel usa `filtrar_por_dueno`: un cliente ve solo sus números.
- **Reportes CSV para Excel** (separador `;` y BOM UTF-8 para tildes y ñ):
  - `/mascotas/reportes/mascotas.csv`: respeta los filtros de la lista
    (nombre, especie, estado) e incluye dueño, correo, n° de vacunas y citas.
  - `/mascotas/reportes/facturas.csv?mes=AAAA-MM`: número, fecha, dueño,
    estado, método de pago, neto, IVA y total.

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
