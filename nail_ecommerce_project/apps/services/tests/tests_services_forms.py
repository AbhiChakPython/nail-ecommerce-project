import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from nail_ecommerce_project.apps.services.form import ServiceForm, ServiceGalleryImageForm

# ---------- ServiceForm Tests ----------

@pytest.mark.django_db
def test_service_form_valid_data():
    form_data = {
        'title': 'Hair Spa',
        'short_description': 'Relaxing scalp treatment',
        'duration_minutes': 45,
        'price': 999.99,
        'is_active': True,
    }
    form = ServiceForm(data=form_data)
    assert form.is_valid()

@pytest.mark.django_db
def test_service_form_missing_required_fields():
    form = ServiceForm(data={})  # empty form
    assert not form.is_valid()
    assert 'title' in form.errors
    assert 'price' in form.errors

@pytest.mark.django_db
def test_service_form_negative_price_invalid():
    form_data = {
        'title': 'Massage',
        'price': -100,
        'duration_minutes': 30
    }
    form = ServiceForm(data=form_data)
    assert not form.is_valid()
    assert 'price' in form.errors

@pytest.mark.django_db
def test_service_form_excludes_slug_field():
    form = ServiceForm()
    assert 'slug' not in form.fields

# ---------- ServiceGalleryImageForm Tests ----------

@pytest.mark.django_db
def test_gallery_image_form_valid_data(service, valid_image_file):
    form = ServiceGalleryImageForm(data={'caption': 'Sample image'}, files={'image_file': valid_image_file})
    form.instance.service = service
    assert form.is_valid()


@pytest.mark.django_db
def test_gallery_image_form_caption_optional(service, valid_image_file):
    form = ServiceGalleryImageForm(data={}, files={'image_file': valid_image_file})
    form.instance.service = service
    assert form.is_valid()

@pytest.mark.django_db
def test_gallery_image_form_missing_image_invalid():
    form = ServiceGalleryImageForm(data={'caption': 'No image'})
    assert not form.is_valid()
    assert 'image_file' in form.errors

