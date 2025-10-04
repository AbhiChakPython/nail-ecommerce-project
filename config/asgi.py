import os
from django.core.asgi import get_asgi_application


# Dynamically choose settings based on DJANGO_ENV environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.environ.get('DJANGO_ENV', 'config.settings.dev'))

application = get_asgi_application()
