from pathlib import Path
import os
import sys
import logging

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-c!s1zjij8*lyj2g#6+r+u_r3$%o@ddp)%(gv4y!z(a$a(q*$=r'
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
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

ROOT_URLCONF = 'prepare_yourself.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.user_role',
            ],
        },
    },
]

WSGI_APPLICATION = 'prepare_yourself.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

_STATIC_DIR = BASE_DIR / 'static'
STATICFILES_DIRS = [_STATIC_DIR] if _STATIC_DIR.exists() else []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ✅ Test environment fix
if 'test' in sys.argv:
    STATICFILES_DIRS = []
    STATIC_ROOT = BASE_DIR / 'staticfiles'
    MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

X_FRAME_OPTIONS = 'SAMEORIGIN'

CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

LOGIN_URL = '/login/'

JAZZMIN_SETTINGS = {
    "site_title": "Prepare Yourself Admin",
    "site_header": "Prepare Yourself",
    "site_brand": "PY Admin",
    "welcome_sign": "Welcome to Prepare Yourself",
    "copyright": "Prepare Yourself 2026",
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'prepareyourselfsupport20226@gmail.com'
EMAIL_HOST_PASSWORD = 'rtwf qmrd lacl vbeu'
DEFAULT_FROM_EMAIL = 'Prepare Yourself <prepareyourselfsupport20226@gmail.com>'

if 'test' in sys.argv:

    logging.disable(logging.CRITICAL)


    logging.getLogger('django.server').setLevel(logging.ERROR)
    logging.getLogger('selenium').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('webdriver_manager').setLevel(logging.CRITICAL)


    logging.getLogger('django.db.backends').setLevel(logging.ERROR)


    DEBUG = False
    TEMPLATES[0]['OPTIONS']['debug'] = False


    if '--fast' in sys.argv:
        DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }


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
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'ERROR' if 'test' in sys.argv else 'INFO',
            'propagate': False,
        },
        'selenium': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
        'urllib3': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
    },
}