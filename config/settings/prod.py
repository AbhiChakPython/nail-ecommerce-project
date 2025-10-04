from .base import *
from dotenv import load_dotenv


# ===============================
# Base Directory (already defined in base.py, can be reused if needed)
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ===============================
# Optional: Load Production Environment Variables
# ===============================
# Only needed if you want to load .env.prod inside Docker (optional)
# load_dotenv(BASE_DIR / ".env.prod")

# ===============================
# Core Production Settings
# ===============================
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("Missing SECRET_KEY in production environment!")

DEBUG = os.getenv("DEBUG", "False").lower() in ["true", "1", "yes"]

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# ===============================
# Database (override base if needed)
# ===============================
DB_SSL_REQUIRED = os.getenv("DB_SSL_REQUIRED", "True").lower() in ["true", "1", "yes"]

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", 600)),
        ssl_require=DB_SSL_REQUIRED
    )
}

# ===============================
# Static & Media
# ===============================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ===============================
# Third-Party Integrations
# ===============================
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# ===============================
# Email Configuration
# ===============================
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ["true", "1", "yes"]
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

# ===============================
# Security Settings
# ===============================
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in ["true", "1", "yes"]
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True").lower() in ["true", "1", "yes"]
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "True").lower() in ["true", "1", "yes"]

# ===============================
# WSGI
# ===============================
WSGI_APPLICATION = 'config.wsgi.application'


# ===============================
# Optional Logging (file logging still works if needed)
# ===============================
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
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
        },
    },
    'root': {'handlers': ['file'], 'level': 'WARNING'},
}

# ===============================
# Auth URLs
# ===============================
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'