from pathlib import Path
import os
import sys

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('SECRET_KEY is not set. Copy .env.example to .env and fill it in.')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# Comma-separated, e.g. ALLOWED_HOSTS=prepareyourself.com,www.prepareyourself.com
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h.strip()]

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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.UserLanguageMiddleware',
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
            'libraries': {
                'bn_filters': 'core.templatetags.bn_filters',
            },
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

# Production: set DATABASE_URL (e.g. postgres://user:pass@host:5432/dbname)
if os.getenv('DATABASE_URL'):
    import dj_database_url
    DATABASES['default'] = dj_database_url.config(conn_max_age=600, ssl_require=not DEBUG)

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

# WhiteNoise serves compressed static files directly from the app in production.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
# In dev, re-read static files from source dirs on every request so CSS/JS edits
# show up without restarting the server or running collectstatic.
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_USE_FINDERS = DEBUG

_STATIC_DIR = BASE_DIR / 'static'
STATICFILES_DIRS = [_STATIC_DIR] if _STATIC_DIR.exists() else []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ✅ Test environment fix
if 'test' in sys.argv:
    STATICFILES_DIRS = []
    STATIC_ROOT = str(BASE_DIR / 'staticfiles')
    MEDIA_ROOT = str(BASE_DIR / 'media')
    # Static files dummy directory ensure
    os.makedirs(STATIC_ROOT, exist_ok=True)
    os.makedirs(MEDIA_ROOT, exist_ok=True)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# SAMEORIGIN (not DENY) because study_note_detail.html embeds the site's own
# PDF files in an <iframe>. Deliberate exception to security.W019.
X_FRAME_OPTIONS = 'SAMEORIGIN'

CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]
# Production origins, comma-separated: CSRF_TRUSTED_ORIGINS=https://prepareyourself.com
CSRF_TRUSTED_ORIGINS += [o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]

# -------- PRODUCTION SECURITY (active when DEBUG=False) --------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days; raise once HTTPS is proven stable
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    # Behind a PaaS/proxy (Railway, Render, Heroku) the TLS terminates upstream:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LOGIN_URL = '/login/'

JAZZMIN_SETTINGS = {
    "site_title": "Prepare Yourself Admin",
    "site_header": "Prepare Yourself",
    "site_brand": "PY Admin",
    "welcome_sign": "Welcome to Prepare Yourself",
    "copyright": "Prepare Yourself 2026",
}

# Local-memory cache (per-process). Swap BACKEND for django-redis + REDIS_URL
# when running multiple workers in production.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'prepare-yourself',
    }
}

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'app.log',
            'maxBytes': 1_000_000,
            'backupCount': 3,
            'encoding': 'utf-8',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'core': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'WARNING',
        },
    },
}

# Default is real SMTP; set EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
# in .env to print emails to the terminal during development.
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = f'Prepare Yourself <{EMAIL_HOST_USER}>' if EMAIL_HOST_USER else 'Prepare Yourself <noreply@localhost>'