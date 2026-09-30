"""Verifica el servidor real (runserver) recorriendo las rutas con la sesion
de un superusuario ya existente. Solo hace GET: no modifica la base de datos.
Usa urllib de la libreria estandar, sin instalar nada.
"""
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = 'http://127.0.0.1:8009'

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinaria.settings')
import django

django.setup()
from django.contrib.auth import (
    BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY,
)
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore

fallos = []


def check(nombre, ok, detalle=''):
    print(('  OK   ' if ok else '  FALLA') + f' {nombre}' + (f' -> {detalle}' if detalle else ''))
    if not ok:
        fallos.append(nombre)


# Sesion real en la base, como la que crea el login.
usuario = User.objects.get(username='jesus')
s = SessionStore()
s[SESSION_KEY] = str(usuario.pk)
s[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
s[HASH_SESSION_KEY] = usuario.get_session_auth_hash()
s.create()
COOKIE = f'sessionid={s.session_key}'


def pedir(ruta, con_sesion=True):
    # Las rutas con "ñ" (dueño) se codifican: HTTP solo admite ASCII.
    destino = urllib.parse.quote(ruta, safe='/?=&')
    req = urllib.request.Request(BASE + destino)
    if con_sesion:
        req.add_header('Cookie', COOKIE)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


print('\n1. Servidor y login')
status, cuerpo, _ = pedir('/accounts/login/', con_sesion=False)
check('pagina de login responde 200', status == 200, f'HTTP {status}')
check('el login trae token CSRF', b'csrfmiddlewaretoken' in cuerpo)

print('\n2. Rutas de la aplicacion')
rutas = [
    '/mascotas/panel/', '/mascotas/', '/mascotas/?pagina=2', '/mascotas/duenos/',
    '/mascotas/citas/', '/mascotas/historial/', '/mascotas/vacunas/',
    '/mascotas/vacunas/alertas/', '/mascotas/facturas/', '/mascotas/inventario/',
    '/mascotas/recetas/', '/mascotas/nueva/', '/mascotas/citas/nueva/',
    '/mascotas/facturas/nueva/', '/mascotas/inventario/nuevo/', '/mascotas/recetas/nueva/',
    '/mascotas/duenos/nuevo/', '/mascotas/vacunas/nueva/', '/mascotas/1/',
    '/admin/', '/admin/mascotas/mascota/', '/admin/mascotas/receta/',
    '/admin/mascotas/cita/', '/admin/mascotas/dueño/', '/admin/mascotas/factura/',
    '/admin/mascotas/producto/', '/admin/mascotas/vacuna/', '/admin/mascotas/historialmedico/',
]
mal = []
for u in rutas:
    status, _, _ = pedir(u)
    if status != 200:
        mal.append((u, status))
check(f'{len(rutas)} rutas responden 200', not mal, f'{len(rutas) - len(mal)}/{len(rutas)}')
for u, code in mal:
    print('     FALLA', code, u)

print('\n3. Descargas')
status, cuerpo, cabeceras = pedir('/mascotas/1/carnet.pdf')
check('carnet PDF',
      status == 200 and cabeceras.get('Content-Type') == 'application/pdf'
      and cuerpo[:4] == b'%PDF',
      f"{cabeceras.get('Content-Type')} / {cuerpo[:4]}")
for nombre in ('facturas', 'mascotas'):
    status, _, cabeceras = pedir(f'/mascotas/reportes/{nombre}.csv')
    check(f'reporte CSV de {nombre}',
          status == 200 and cabeceras.get('Content-Type', '').startswith('text/csv'),
          cabeceras.get('Content-Type'))

print('\n4. Sin sesion cae al login')
# urlopen sigue el 302 hasta el login y devuelve 200, asi que se bloquean las
# redirecciones para comprobar que la ruta protegida NO se sirve sin sesion.
class SinRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = urllib.request.build_opener(SinRedirecciones)
try:
    with opener.open(urllib.request.Request(BASE + '/mascotas/panel/'), timeout=25) as r:
        status, cabeceras = r.status, dict(r.headers)
except urllib.error.HTTPError as e:
    status, cabeceras = e.code, dict(e.headers)

destino = cabeceras.get('Location', '')
check('ruta protegida redirige al login sin sesion',
      status == 302 and 'login' in destino, f'HTTP {status} -> {destino}')

s.delete()

print('\n' + '=' * 52)
print('RESULTADO: TODO FUNCIONA' if not fallos else f'RESULTADO: {len(fallos)} FALLOS')
for x in fallos:
    print('  -', x)
sys.exit(1 if fallos else 0)
