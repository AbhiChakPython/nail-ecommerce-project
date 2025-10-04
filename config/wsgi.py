import os
from django.core.wsgi import get_wsgi_application

# Dynamically choose settings based on DJANGO_ENV environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.environ.get('DJANGO_ENV', 'config.settings.dev'))

application = get_wsgi_application()
