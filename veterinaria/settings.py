"""
Django settings for veterinaria project.

Generado con 'django-admin startproject' usando Django 4.2.

Para más información sobre este archivo, ver:
https://docs.djangoproject.com/en/4.2/topics/settings/
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from django.contrib.messages import constants as message_constants
from dotenv import load_dotenv

import dj_database_url
import sys

# Cargar variables desde .env (si existe)
# .env NO se sube a GitHub (ver .gitignore)
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# -------------------------------------------------------------------
# Configuración sensible — leída desde .env
# -------------------------------------------------------------------

# SECRET_KEY es obligatorio. Si no está definido, el servidor no arranca.
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured(
        'Falta SECRET_KEY. Copia .env.example como .env y completa sus valores.'
    )

# DEBUG: True para desarrollo, False para producción. Por defecto True.
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'si', 'yes')

# ALLOWED_HOSTS: lista de hosts permitidos. Por defecto localhost y 127.0.0.1.
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
    if host.strip()
]


# -------------------------------------------------------------------
# Application definition
# -------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mascotas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'veterinaria.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'veterinaria.wsgi.application'


# -------------------------------------------------------------------
# Database — PostgreSQL (Supabase) o SQLite para desarrollo local
# -------------------------------------------------------------------

# Si DATABASE_URL está definida (producción / Supabase), usarla.
# Si no, usar SQLite local para desarrollo.
database_url = os.getenv('DATABASE_URL', '').strip()

if database_url:
    db_config = dj_database_url.parse(database_url)
    DATABASES = {
        'default': db_config
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
            'NAME': str(BASE_DIR / os.getenv('DB_NAME', 'db.sqlite3')),
        }
    }

# ✅ Forzar SQLite para los tests (independiente de Supabase/Postgres)
DATABASES['default']['TEST'] = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': str(BASE_DIR / 'test_db.sqlite3'),
}


# -------------------------------------------------------------------
# Password validation
# -------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# -------------------------------------------------------------------
# Internationalization
# -------------------------------------------------------------------

LANGUAGE_CODE = 'es-cl'

TIME_ZONE = 'America/Santiago'

USE_I18N = True

USE_TZ = True


# -------------------------------------------------------------------
# Static files (CSS, JavaScript, Images)
# -------------------------------------------------------------------

STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# -------------------------------------------------------------------
# Authentication: redirecciones tras login/logout
# -------------------------------------------------------------------

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'mascotas:lista'
LOGOUT_REDIRECT_URL = 'login'


# -------------------------------------------------------------------
# Messages: "error" usa la clase "danger" de Bootstrap (rojo)
# -------------------------------------------------------------------

MESSAGE_TAGS = {
    message_constants.ERROR: 'danger',
}


# -------------------------------------------------------------------
# Seguridad de cookies y sesión
# -------------------------------------------------------------------

SESSION_COOKIE_HTTPONLY = True          # JavaScript no puede leer la cookie de sesión
CSRF_COOKIE_HTTPONLY = True             # JavaScript no puede leer la cookie CSRF
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # La sesión se cierra al cerrar el navegador
X_FRAME_OPTIONS = 'DENY'                # Evita que la página se cargue dentro de un iframe

# Cuando DEBUG está desactivado (producción), las cookies solo viajan por HTTPS.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# -------------------------------------------------------------------
# Login y logout
# -------------------------------------------------------------------

# Logger por defecto para el proyecto
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# -------------------------------------------------------------------
# Forzar SQLite en pruebas (independiente de Supabase/Postgres)
# -------------------------------------------------------------------
if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'test_db.sqlite3'),
    }
