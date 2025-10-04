from io import BytesIO
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from nail_ecommerce_project.apps.products.forms import ProductForm, ProductGalleryImageForm, ProductVariantFormSet
from nail_ecommerce_project.apps.products.models import Product, ProductCategory

pytestmark = pytest.mark.django_db


def test_product_form_valid():
    category = ProductCategory.objects.create(name="Nail Care")
    form_data = {
        'name': 'Base Coat',
        'description': 'Protective base coat',
        'is_available': True,
        'discount_percent': 10,
        'lto_discount_percent': 15,
        'lto_start_date': '2025-06-01 00:00:00',
        'lto_end_date': '2025-06-30 23:59:59',
        'categories': [category.id],
    }
    form = ProductForm(data=form_data)
    assert form.is_valid()


def test_product_gallery_image_form_valid():
    image_io = BytesIO()
    image = Image.new('RGB', (100, 100), color='red')
    image.save(image_io, format='JPEG')
    image_io.seek(0)

    uploaded_image = SimpleUploadedFile("test.jpg", image_io.read(), content_type="image/jpeg")
    form = ProductGalleryImageForm(files={'image': uploaded_image})
    assert form.is_valid()


def test_variant_formset_valid():
    product = Product.objects.create(name="Gel Polish", description="Long lasting")
    formset_data = {
        'variants-TOTAL_FORMS': '1',
        'variants-INITIAL_FORMS': '0',
        'variants-MIN_NUM_FORMS': '0',
        'variants-MAX_NUM_FORMS': '1000',
        'variants-0-color': 'Red',
        'variants-0-size': 'Small',
        'variants-0-price': '100.00',
        'variants-0-stock_quantity': '10',
    }
    formset = ProductVariantFormSet(data=formset_data, instance=product, prefix='variants')
    assert formset.is_valid()


def test_variant_formset_invalid_missing_fields():
    product = Product.objects.create(name="Top Coat", description="Glossy finish")
    formset_data = {
        'variants-TOTAL_FORMS': '1',
        'variants-INITIAL_FORMS': '0',
        'variants-MIN_NUM_FORMS': '0',
        'variants-MAX_NUM_FORMS': '1000',
        'variants-0-color': '',
        'variants-0-size': '',
        'variants-0-price': '',
        'variants-0-stock_quantity': '',
    }
    formset = ProductVariantFormSet(data=formset_data, instance=product, prefix='variants')
    assert not formset.is_valid()
    assert 'color' in formset.forms[0].errors
    assert 'size' in formset.forms[0].errors
    assert 'price' in formset.forms[0].errors
