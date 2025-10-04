import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils.text import slugify
from nail_ecommerce_project.apps.services.models import Service, ServiceGalleryImage

@pytest.mark.django_db
def test_service_str_representation():
    service = Service.objects.create(title="Nail Art", price=500.00)
    assert str(service) == "Nail Art"

@pytest.mark.django_db
def test_service_slug_auto_generation():
    service = Service.objects.create(title="Spa & Relaxation", price=1000.00)
    assert service.slug == slugify("Spa & Relaxation")

@pytest.mark.django_db
def test_service_ordering():
    Service.objects.create(title="B", price=500)
    Service.objects.create(title="A", price=500)
    services = Service.objects.all()
    assert list(services.values_list('title', flat=True)) == ["A", "B"]

@pytest.mark.django_db
def test_gallery_image_links_to_service():
    service = Service.objects.create(title="Hair Wash", price=300.00)
    gallery = ServiceGalleryImage.objects.create(service=service, image_file="dummy.jpg", caption="Before shot")
    assert gallery.service == service
    assert str(gallery) == f"Gallery image for {service.title}"

# --- Negative & Edge Case Tests ---

@pytest.mark.django_db
def test_service_title_must_be_unique():
    Service.objects.create(title="Manicure", price=300)
    with pytest.raises(IntegrityError):
        Service.objects.create(title="Manicure", price=400)  # same title

@pytest.mark.django_db
def test_service_requires_title_and_price():
    service = Service(price=250)
    with pytest.raises(ValidationError):
        service.full_clean()

    service = Service(title="Pedicure")
    with pytest.raises(ValidationError):
        service.full_clean()

@pytest.mark.django_db
def test_service_duration_cannot_be_negative():
    service = Service(title="Face Clean-up", price=500, duration_minutes=-30)
    with pytest.raises(ValidationError):
        service.full_clean()  # triggers model field validators

@pytest.mark.django_db
def test_service_price_cannot_be_negative():
    service = Service(title="Waxing", price=-150)
    with pytest.raises(ValidationError):
        service.full_clean()

@pytest.mark.django_db
def test_servicegalleryimage_requires_service():
    with pytest.raises(IntegrityError):
        ServiceGalleryImage.objects.create(image_file="invalid.jpg")  # service FK is required
