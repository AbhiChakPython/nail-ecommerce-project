import pytest
from io import BytesIO
from datetime import timedelta
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from nail_ecommerce_project.apps.products.models import (
    Product, ProductVariant, ProductCategory
)
from django.contrib.auth import get_user_model


pytestmark = pytest.mark.django_db
User = get_user_model()

# -------------------- Fixtures --------------------

@pytest.fixture
def superuser():
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="adminpass"
    )

@pytest.fixture
def customer_user():
    return User.objects.create_user(
        username="customer", email="customer@example.com", password="custpass", role="CUSTOMER"
    )

@pytest.fixture
def uploaded_image():
    image_io = BytesIO()
    image = Image.new("RGB", (100, 100), color="blue")
    image.save(image_io, format="JPEG")
    image_io.seek(0)
    return SimpleUploadedFile("test.jpg", image_io.read(), content_type="image/jpeg")

@pytest.fixture
def category():
    return ProductCategory.objects.create(name="Test Category", slug="test-category")

@pytest.fixture
def product(uploaded_image, category):
    p = Product.objects.create(
        name="Old Product",
        description="Old Desc",
        thumbnail=uploaded_image,
        is_available=True,
        slug=slugify("Old Product"),
    )
    p.categories.add(category)
    variant = ProductVariant.objects.create(
        product=p,
        color="Blue",
        size="M",
        price="9.99",
        stock_quantity=10,
    )
    return p, variant, category

# -------------------- Basic Views --------------------

def test_product_list_view_shows_available_products(client):
    category = ProductCategory.objects.create(name="Nails")
    p1 = Product.objects.create(name="Red", is_available=True)
    p1.categories.add(category)
    Product.objects.create(name="Hidden", is_available=False)

    response = client.get(reverse("products:product_list"))
    assert response.status_code == 200
    assert "Red" in response.content.decode()
    assert "Hidden" not in response.content.decode()


def test_product_detail_view_displays_correct_data(client):
    product = Product.objects.create(name="Glossy Pink", is_available=True)
    url = reverse("products:product_detail", kwargs={"slug": product.slug})
    response = client.get(url)
    assert response.status_code == 200
    assert "Glossy Pink" in response.content.decode()


# -------------------- Create Product --------------------

def test_product_create_view_accessible_by_superuser(client, superuser):
    client.force_login(superuser)
    url = reverse("products:product_create")
    response = client.get(url)
    assert response.status_code == 200
    assert "Add New Product" in response.content.decode()


def test_product_create_view_creates_product_and_variant(client, superuser, uploaded_image, category):
    client.force_login(superuser)
    url = reverse("products:product_create")

    # STEP 1: Product data
    post_data = {
        "name": "Test Product",
        "description": "Test Description",
        "is_available": True,
        "discount_percent": 10,
        "lto_discount_percent": 5,
        "lto_start_date": timezone.now().strftime('%Y-%m-%d'),
        "lto_end_date": (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
        "categories": str(category.id),
    }

    # STEP 2: Formset data (IMPORTANT - must be merged with post_data)
    formset_data = {
        "variants-TOTAL_FORMS": "1",
        "variants-INITIAL_FORMS": "0",
        "variants-MIN_NUM_FORMS": "0",
        "variants-MAX_NUM_FORMS": "1000",

        "variants-0-id": "",
        "variants-0-color": "Red",
        "variants-0-size": "M",
        "variants-0-price": "19.99",
        "variants-0-stock_quantity": "5",
    }

    # STEP 3: Merge post data
    full_post_data = {**post_data, **formset_data}

    # STEP 4: Make POST request
    response = client.post(
        url,
        data=full_post_data,
        files={"thumbnail": uploaded_image},  # only thumbnail goes in files
        follow=True,
    )

    # STEP 5: Debug output (optional)
    print("Product exists:", Product.objects.filter(name="Test Product").exists())
    product_qs = Product.objects.filter(name="Test Product")
    if product_qs.exists():
        product = product_qs.first()
        print("Variants:", list(product.variants.all()))

    # STEP 6: Final assertion
    assert Product.objects.filter(name="Test Product").exists()
    assert ProductVariant.objects.filter(product__name="Test Product").exists()


# -------------------- Update Product --------------------

def test_product_update_view_accessible_by_superuser(client, superuser, product):
    product_instance, _, _ = product
    client.force_login(superuser)
    url = reverse("products:product_update", kwargs={"slug": product_instance.slug})

    response = client.get(url)
    assert response.status_code == 200
    assert "Edit Product" in response.content.decode()

def test_product_update_basic_fields(client, superuser, product, uploaded_image):
    product_instance, _, category = product
    client.force_login(superuser)
    url = reverse("products:product_update", kwargs={"slug": product_instance.slug})

    updated_data = {
        "name": "Updated Name",
        "description": "Updated description",
        "is_available": True,
        "discount_percent": 10,
        "lto_discount_percent": 0,
        "lto_start_date": timezone.now(),
        "lto_end_date": timezone.now() + timedelta(days=10),
        "categories": [category.id],
    }

    response = client.post(url, data=updated_data, files={"thumbnail": uploaded_image})
    assert response.status_code == 302
    product_instance.refresh_from_db()
    assert product_instance.name == "Updated Name"


# -------------------- Manage Variants --------------------

def test_manage_variants_view_get(client, superuser, product):
    product_instance, variant, _ = product
    client.force_login(superuser)
    url = reverse("products:manage_variants", kwargs={"slug": product_instance.slug})
    response = client.get(url)
    assert response.status_code == 200
    assert b"Manage Variants for:" in response.content
    assert variant.color.encode() in response.content


def test_manage_variants_view_post_valid_data(client, superuser, product):
    client.force_login(superuser)
    product, variant, _ = product
    url = reverse("products:manage_variants", args=[product.slug])

    post_data = {
        "variants-TOTAL_FORMS": "1",
        "variants-INITIAL_FORMS": "0",
        "variants-MIN_NUM_FORMS": "0",
        "variants-MAX_NUM_FORMS": "1000",

        "variants-0-id": "",
        "variants-0-color": "Green",
        "variants-0-size": "XL",
        "variants-0-price": "59.99",
        "variants-0-stock_quantity": "10",
    }

    response = client.post(url, data=post_data)

    print("POST keys:", list(post_data.keys()))
    if response.context and 'formset' in response.context:
        print("Formset errors:", response.context['formset'].errors)

    # Assert redirect after successful variant update
    assert response.status_code == 302
    assert response['Location'] == reverse('products:product_detail', args=[product.slug])

    # Assert variant was created
    assert product.variants.filter(color="Green", size="XL").exists()


def test_manage_variants_view_access_denied_for_normal_user(client, customer_user, product):
    product_instance, _, _ = product
    client.force_login(customer_user)
    url = reverse("products:manage_variants", kwargs={"slug": product_instance.slug})
    response = client.get(url)
    assert response.status_code in [403, 302]
