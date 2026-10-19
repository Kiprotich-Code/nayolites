"""
Django settings for the Nayolites Compute and Media College platform.
"""

from pathlib import Path
from decouple import config, Csv
from django.core.exceptions import ImproperlyConfigured

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

SECRET_KEY = config(
    'SECRET_KEY',
    default='',
)
if not SECRET_KEY:
    raise ImproperlyConfigured('Set SECRET_KEY in your environment or .env file.')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
    cast=Csv(),
)
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='',
    cast=Csv(),
)

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    # Django built-ins
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    # Local applications
    'apps.accounts',
    'apps.core',
    'apps.students',
    'apps.courses',
    'apps.enrollments',
    'apps.finance',
    'apps.results',
    'apps.content',
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.accounts.middleware.ForcePasswordChangeMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nayolites.urls'

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

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
                'apps.core.context_processors.college_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'nayolites.wsgi.application'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_ENGINE = config(
    'DB_ENGINE',
    default='django.db.backends.sqlite3',
)
DATABASES = {
    'default': {
        'ENGINE': DATABASE_ENGINE,
        'NAME': config('DB_NAME', default=str(BASE_DIR / 'db.sqlite3')),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default=''),
    }
}
if DATABASE_ENGINE == 'django.db.backends.postgresql':
    sslmode = config(
        'DB_SSLMODE',
        default='prefer' if DEBUG else 'require',
    )
    if not sslmode and not DEBUG:
        sslmode = 'require'
    if sslmode:
        DATABASES['default']['OPTIONS'] = {'sslmode': sslmode}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

# Custom User model — must be declared before any migration that references it.
# apps.accounts must appear in INSTALLED_APPS before any app that has a FK to User.
AUTH_USER_MODEL = 'accounts.User'

# Custom authentication backend that enforces account_status (Req 1.6, 2.3, 2.4).
# Replaces ModelBackend — handles email-based login and blocks SUSPENDED/INACTIVE accounts.
AUTHENTICATION_BACKENDS = ['apps.accounts.backends.AccountStatusBackend']

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ---------------------------------------------------------------------------
# Media files
# ---------------------------------------------------------------------------

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# Authentication redirects
# ---------------------------------------------------------------------------

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/auth/redirect/'
LOGOUT_REDIRECT_URL = '/'

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL',
    default='webmaster@localhost',
)

# ---------------------------------------------------------------------------
# Institution profile
# ---------------------------------------------------------------------------

COLLEGE_NAME = config('COLLEGE_NAME', default='Nayolites Compute and Media College')
COLLEGE_SHORT_NAME = config('COLLEGE_SHORT_NAME', default='Nayolites')
COLLEGE_TAGLINE = config('COLLEGE_TAGLINE', default='Computing. Creating. Leading.')
COLLEGE_ADDRESS = config('COLLEGE_ADDRESS', default='Kimathi Street, Nairobi, Kenya')
COLLEGE_PHONE = config('COLLEGE_PHONE', default='+254 700 123 456')
COLLEGE_EMAIL = config('COLLEGE_EMAIL', default='info@nayolites.ac.ke')
COLLEGE_WEBSITE = config('COLLEGE_WEBSITE', default='www.nayolites.ac.ke')
COLLEGE_CURRENCY = config('COLLEGE_CURRENCY', default='KES')
COLLEGE_CURRENCY_SYMBOL = config('COLLEGE_CURRENCY_SYMBOL', default='Ksh')

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

# DRF defaults enforce authentication on all API endpoints (Req 21.1, 21.2)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

# ---------------------------------------------------------------------------
# Default primary key
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Session security (Req 18)
# ---------------------------------------------------------------------------

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 28800  # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
CSRF_COOKIE_HTTPONLY = False  # Must be False for AJAX CSRF token reads

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = config(
    'SECURE_SSL_REDIRECT',
    default=not DEBUG,
    cast=bool,
)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    'SECURE_HSTS_INCLUDE_SUBDOMAINS',
    default=False,
    cast=bool,
)
SECURE_HSTS_PRELOAD = config(
    'SECURE_HSTS_PRELOAD',
    default=False,
    cast=bool,
)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
if config('TRUST_X_FORWARDED_PROTO', default=False, cast=bool):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------------------------
# Finance
# ---------------------------------------------------------------------------

from decimal import Decimal as _Decimal
FINANCE_MINIMUM_PAYMENT_FLOOR = _Decimal('500.00')
PAYHERO_API_KEY = config('PAYHERO_API_KEY', default='')
PAYHERO_CHANNEL_ID = config('PAYHERO_CHANNEL_ID', default='')
PAYHERO_WEBHOOK_SECRET = config('PAYHERO_WEBHOOK_SECRET', default='')
PAYHERO_CALLBACK_URL = config('PAYHERO_CALLBACK_URL', default='')
