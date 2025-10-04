from .base import *

# ===============================
# Development Overrides
# ===============================

# Secret key & Debug
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-dev-key")
DEBUG = os.getenv("DEBUG", "True").lower() in ["true", "1", "yes"]

# Allowed hosts
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# Database (force SQLite for local dev, unless explicitly overridden)
DATABASES["default"].update({
    "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
    "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
})

# Razorpay keys (optional in dev)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# Email settings for development (console backend)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@rupasnails.dev")
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")

# Logging override (more verbose for development)
LOGGING["root"]["level"] = "DEBUG"
LOGGING["handlers"]["console"]["level"] = "DEBUG"

# Development notes:
# Run server with:
#   python manage.py runserver --settings=config.settings.dev
