# Punto 2 — Funcionalidades avanzadas (Joel)

Rama: `feature/joel-funcionalidades` (sale de `feature/env-infra`, después de J8).

Resumen: 5 commits (JV1–JV5) que agregan las funcionalidades avanzadas del
Caso 5 sobre los modelos que dejó Jesús. **No se agregan migraciones**: se
usan los modelos `Dueño`, `Mascota`, `Cita`, `HistorialMedico` y `Vacuna`
tal como quedaron en J7/J8.

| Commit | Tema | Tests nuevos |
|---|---|---|
| JV1 | Citas: validación de horario, cancelar e historial por mascota | 13 |
| JV2 | Vacunas: control de dosis, validaciones, editar y eliminar | 9 |
| JV3 | Historial médico: editar/eliminar y ficha clínica | 8 |
| JV4 | Dueños: registro, detalle y "Mis mascotas" | 8 |
| JV5 | Alertas, reportes CSV y recordatorios por correo | 7 |

Total del proyecto: 72 tests (`python manage.py test mascotas`).

---

## JV1 — Citas avanzadas

**Qué hace**
- `CitaForm.clean()` aplica 3 reglas:
  1. No se programa una cita en una fecha pasada.
  2. Un veterinario no puede tener dos citas el mismo día y hora.
  3. Una mascota no puede tener dos citas el mismo día y hora.
  Las citas **canceladas** no ocupan horario.
- Nueva vista `cancelar_cita` (`POST /mascotas/citas/<id>/cancelar/`):
  cambia el estado a *cancelada* sin borrar la cita. No cancela citas ya
  finalizadas o canceladas.
- `listar_citas` filtra por mascota (historial de citas), estado, periodo
  (próximas/pasadas) y rango de fechas. Los filtros mal escritos se ignoran
  (no generan error 500).
- Menú de navegación en `base.html` y botón **Citas** en cada mascota.

**Archivos**: `forms.py`, `models.py` (`puede_cancelarse`), `views.py`,
`urls.py`, `cita_list.html`, `mascota_list.html`, `base.html`, `tests.py`.

## JV2 — Vacunas y control de dosis

**Qué hace**
- `VacunaQuerySet` con `ultimas_dosis()`, `vencidas()` y `por_vencer()`.
  `ultimas_dosis()` deja solo la dosis más reciente de cada tipo por mascota,
  así una dosis antigua que ya tuvo refuerzo no aparece como vencida.
- Propiedades en `Vacuna`: `estado_dosis` (vencida / proxima / al_dia /
  sin_refuerzo), `dias_para_proxima` y `dias_de_atraso`.
- Al registrar una vacuna, la mascota queda marcada como vacunada.
- `VacunaForm`: fecha de aplicación no futura, próxima dosis posterior a la
  aplicación, no se vacuna a una mascota alérgica y se limpia el texto.
- Vistas `editar_vacuna` y `eliminar_vacuna` (antes los botones iban a `#`).
- Lista con filtros por mascota, tipo y estado de la dosis.

**Archivos**: `models.py`, `forms.py`, `views.py`, `urls.py`,
`vacuna_list.html`, `vacuna_form.html`, `vacuna_confirm_delete.html`, `tests.py`.

## JV3 — Historial médico y ficha clínica

**Qué hace**
- `HistorialMedicoForm`: fecha no futura, nombre de veterinario válido, exige
  diagnóstico o tratamiento y limpia HTML.
- Vistas `editar_historial` y `eliminar_historial` (antes los botones iban a `#`).
- Nueva vista `ficha_mascota` (`/mascotas/<id>/ficha/`): datos de la mascota,
  dueño, resumen, próxima cita, dosis vencidas, historial, vacunas y citas.
  Cada sección se muestra según los permisos del usuario.
- Los formularios de cita, historial y vacuna aceptan `?mascota=<id>` para
  dejar la mascota preseleccionada (se usa desde la ficha).

**Archivos**: `forms.py`, `views.py`, `urls.py`, `mascota_ficha.html`,
`historial_list.html`, `historial_form.html`, `historial_confirm_delete.html`,
`mascota_list.html`, `tests.py`.

## JV4 — Dueños asociados a usuarios

**Qué hace**
- `DueñoForm`: usuario del sistema, nombre solo con letras, teléfono/WhatsApp
  validados y al menos un medio de contacto.
- Vistas `listar_duenos` (búsqueda + total de mascotas), `crear_dueno`,
  `editar_dueno` y `detalle_dueno`.
- Vista `mis_mascotas`: un usuario que es dueño ve solo sus mascotas, con la
  próxima cita y las dosis vencidas.
- `MascotaForm` ahora incluye **raza** y **dueño**. La lista de mascotas
  muestra el dueño y filtra con `?dueno=<id>`.

**Archivos**: `forms.py`, `views.py`, `urls.py`, `dueno_list.html`,
`dueno_form.html`, `dueno_detalle.html`, `mis_mascotas.html`,
`mascota_list.html`, `base.html`, `tests.py`.

## JV5 — Alertas, reportes y recordatorios

**Qué hace**
- `mascotas/alertas.py`: calcula dosis vencidas, dosis por vencer (30 días),
  mascotas sin vacunar, citas de hoy y citas de los próximos 7 días.
- Panel `/mascotas/alertas/` con tarjetas de resumen y listas.
- Context processor `mascotas.context_processors.alertas`: contador rojo en el
  menú (dosis vencidas + citas de hoy).
- Reportes `/mascotas/reportes/`: mascotas por estado y especie, citas por
  estado y por veterinario, vacunas por tipo y dueños con más mascotas.
  Botón para descargar las mascotas en **CSV** (se abre bien en Excel).
- Comando `python manage.py enviar_recordatorios [--dias 7] [--simular]`:
  envía correo a los dueños con dosis por vencer y citas para mañana.
- `settings.py` lee `EMAIL_*` desde `.env`. Si no hay contraseña SMTP, usa el
  backend de consola (los correos se ven en la terminal).
- README y este documento.

**Archivos**: `alertas.py`, `context_processors.py`,
`management/commands/enviar_recordatorios.py`, `views.py`, `urls.py`,
`alertas.html`, `reportes.html`, `base.html`, `settings.py`, `README.md`,
`docs/PUNTO2_JOEL.md`, `tests.py`.

---

## Para coordinar con Gabriel (Punto 3)

- `setup_grupos` hoy solo da permisos sobre `Mascota`. Para que el grupo
  **Veterinarios** vea citas, historial, vacunas, dueños y alertas, hay que
  agregar los permisos `view_cita`, `view_historialmedico`, `view_vacuna`,
  `view_dueño` (y los de agregar/editar que correspondan) en ese comando.
- `Dueño` todavía no está registrado en `admin.py`.

## Cómo probarlo en la presentación

1. `python manage.py runserver` y entrar con el superusuario.
2. Crear un dueño en **Dueños** y asignarle una mascota (editar mascota).
3. Registrar una vacuna con próxima dosis en el pasado → aparece en **Alertas**
   y el contador del menú sube.
4. Crear una cita para hoy → aparece en **Alertas**; intentar otra a la misma
   hora con el mismo veterinario → el formulario lo impide.
5. Cancelar la cita desde **Citas** y ver que queda como *Cancelada*.
6. Abrir la **Ficha** de la mascota.
7. Ir a **Reportes** y descargar el CSV.
8. `python manage.py enviar_recordatorios --simular`.
