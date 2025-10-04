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
load_dotenv(BASE_DIR / ".env.prod")

# ===============================
# Core Production Settings
# ===============================
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("Missing SECRET_KEY in production environment!")

DEBUG = os.getenv("DEBUG", "False").lower() in ["true", "1", "yes"]
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

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
