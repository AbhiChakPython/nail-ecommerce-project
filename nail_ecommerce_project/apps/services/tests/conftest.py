import pytest
from io import BytesIO
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from nail_ecommerce_project.apps.services.models import Service


@pytest.fixture
def service():
    return Service.objects.create(title="Test Service", price=499, duration_minutes=30)


@pytest.fixture
def valid_image_file():
    image = Image.new("RGB", (100, 100), color="white")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile("test.jpg", buffer.read(), content_type="image/jpeg")


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        username="admin", email="admin@example.com", password="adminpass"
    )

@pytest.fixture
def superuser_client(client, superuser):
    client.force_login(superuser)
    return client