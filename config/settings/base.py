import os
import platform
from pathlib import Path
from datetime import timedelta
import dj_database_url
from dotenv import load_dotenv

# ===============================
# Base Directory
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ===============================
# Load Development Environment Variables
# ===============================
# By default, load .env.dev for local development
# Production variables are expected from the system (or Docker)
if os.getenv("DJANGO_ENV", "dev").lower() == "dev":
    load_dotenv(BASE_DIR / ".env.dev")

# ===============================
# Core Django Settings
# ===============================
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")
DEBUG = os.getenv("DEBUG", "False").lower() in ["true", "1", "yes"]
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ===============================
# Installed Apps
# ===============================
INSTALLED_APPS = [
    # Default Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'tailwind',
    'django_browser_reload',
    'widget_tweaks',

    # Local apps
    'theme',
    'nail_ecommerce_project.apps.users',
    'nail_ecommerce_project.apps.services',
    'nail_ecommerce_project.apps.products',
    'nail_ecommerce_project.apps.orders',
    'nail_ecommerce_project.apps.bookings',
    'nail_ecommerce_project.apps.analytics',
    'nail_ecommerce_project.apps.core',
]

# ===============================
# Middleware
# ===============================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]

# ===============================
# URL & WSGI
# ===============================
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

# ===============================
# Database (Environment Driven)
# ===============================
DB_SSL_REQUIRED = os.getenv("DB_SSL_REQUIRED", "False").lower() in ["true", "1", "yes"]

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", 600)),
        ssl_require=DB_SSL_REQUIRED
    )
}

# ===============================
# Templates
# ===============================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'nail_ecommerce_project' / 'templates'],
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

# ===============================
# Authentication
# ===============================
AUTH_USER_MODEL = 'users.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===============================
# REST Framework & JWT
# ===============================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_LIFETIME_MIN", 60))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_LIFETIME_DAYS", 1))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# ===============================
# Localization
# ===============================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ===============================
# Static & Media
# ===============================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "nail_ecommerce_project" / "static"]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ===============================
# Tailwind / NPM
# ===============================
TAILWIND_APP_NAME = "theme"
INTERNAL_IPS = ["127.0.0.1"]
NPM_BIN_PATH = os.getenv(
    "NPM_BIN_PATH",
    r"C:\Program Files\nodejs\npm.cmd" if platform.system() == "Windows" else "/usr/bin/npm"
)

# ===============================
# Logging
# ===============================
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
        'colored': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(log_color)s[%(asctime)s] %(levelname)s %(name)s: %(message)s',
            'log_colors': {
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            },
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': LOG_DIR / 'application.log',
            'when': 'midnight',
            'backupCount': 7,
            'formatter': 'verbose',
            'encoding': 'utf-8',
            'delay': True,
        },
        'console': {'level': 'WARNING', 'class': 'logging.StreamHandler', 'formatter': 'colored'},
    },
    'root': {'handlers': ['file', 'console'], 'level': 'WARNING'},
}

# ===============================
# Third-Party Integrations
# ===============================
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# ===============================
# Auth URLs & Error Handlers
# ===============================
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'
CSRF_FAILURE_VIEW = 'nail_ecommerce_project.apps.users.views_frontend.custom_csrf_failure_view'
handler400 = 'nail_ecommerce_project.apps.core.views_frontend.custom_bad_request_view'
