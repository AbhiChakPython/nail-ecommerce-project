from django.urls import reverse
from django.utils.text import slugify
from nail_ecommerce_project.apps.products.models import (
    Product, ProductVariant, ProductCategory
)
from io import BytesIO
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def superuser():
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="adminpass"
    )

@pytest.fixture
def uploaded_image():
    img_io = BytesIO()
    image = Image.new("RGB", (100, 100), color="blue")
    image.save(img_io, format="JPEG")
    img_io.seek(0)

    return SimpleUploadedFile("test_image.jpg", img_io.getvalue(), "image/jpeg")

@pytest.fixture
def product_instance(uploaded_image):
    return Product.objects.create(
        name="DeleteMe",
        description="To be deleted",
        thumbnail=uploaded_image,
        is_available=True,
        slug="deleteme"
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


def test_product_list_view_search_query_filters_results(client):
    category = ProductCategory.objects.create(name="Nails")
    p1 = Product.objects.create(name="Red Polish", description="Beautiful red shade", is_available=True)
    p1.categories.add(category)
    p2 = Product.objects.create(name="Blue Polish", description="Cool blue tone", is_available=True)
    p2.categories.add(category)

    # Perform search for "red"
    url = reverse("products:product_list") + "?q=red"
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    # ✅ "Red Polish" should appear
    assert "Red Polish" in content
    # ✅ "Blue Polish" should NOT appear
    assert "Blue Polish" not in content


def test_product_list_view_category_filter(client):
    # Create two categories
    cat1 = ProductCategory.objects.create(name="Category One", slug="cat-one")
    cat2 = ProductCategory.objects.create(name="Category Two", slug="cat-two")

    # Product in cat-one
    p1 = Product.objects.create(name="CatOne Product", is_available=True)
    p1.categories.add(cat1)

    # Product in cat-two
    p2 = Product.objects.create(name="CatTwo Product", is_available=True)
    p2.categories.add(cat2)

    # Filter by cat-one
    url = reverse("products:product_list") + "?category=cat-one"
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()

    # ✅ Only CatOne Product should appear
    assert "CatOne Product" in content
    # ✅ CatTwo Product should NOT appear
    assert "CatTwo Product" not in content


def test_product_create_view_denied_for_non_superuser(client, customer_user):
    # Force login as a normal customer
    client.force_login(customer_user)
    url = reverse("products:product_create")
    response = client.get(url)

    # Should be forbidden (403)
    assert response.status_code == 403


def test_product_create_view_redirects_anonymous_user(client):
    url = reverse("products:product_create")
    response = client.get(url)

    # Anonymous users should redirect to login
    assert response.status_code == 302
    assert "/login" in response.url


def test_product_update_view_denied_for_non_superuser(client, customer_user, product):
    product_instance, _, _ = product
    client.force_login(customer_user)
    url = reverse("products:product_update", kwargs={"slug": product_instance.slug})
    response = client.get(url)

    # Normal user should be forbidden
    assert response.status_code == 403


def test_product_update_view_redirects_anonymous_user(client, product):
    product_instance, _, _ = product
    url = reverse("products:product_update", kwargs={"slug": product_instance.slug})
    response = client.get(url)

    # Anonymous should be redirected to login
    assert response.status_code == 302
    assert "/login" in response.url


def test_manage_variants_view_post_invalid_data(client, superuser, product):
    client.force_login(superuser)
    product_instance, variant, _ = product
    url = reverse("products:manage_variants", args=[product_instance.slug])

    # Invalid (missing required fields)
    post_data = {
        "variants-TOTAL_FORMS": "1",
        "variants-INITIAL_FORMS": "0",
        "variants-MIN_NUM_FORMS": "0",
        "variants-MAX_NUM_FORMS": "1000",

        "variants-0-id": "",
        "variants-0-color": "",
        "variants-0-size": "",
        "variants-0-price": "",
        "variants-0-stock_quantity": "",
    }

    response = client.post(url, data=post_data)

    # Should NOT redirect (stay on page with errors)
    assert response.status_code == 200
    assert b"This field is required" in response.content

    # Ensure no new variants created
    assert product_instance.variants.count() == 1  # only the original one exists


def test_manage_gallery_view_post_invalid_file(client, superuser, product_instance):
    client.force_login(superuser)
    url = reverse("products:manage_gallery", kwargs={"slug": product_instance.slug})

    # Send empty data (no image)
    response = client.post(url, data={}, follow=True)

    # Should return 200 and NOT save
    assert response.status_code == 200
    assert b"This field is required" in response.content

    # Ensure no gallery images created
    assert not product_instance.gallery_images.exists()


def test_delete_gallery_image_denied_for_non_superuser(client, customer_user, product_instance, uploaded_image):
    from nail_ecommerce_project.apps.products.models import ProductGalleryImage

    # Step 1: Create gallery image
    gallery_image = ProductGalleryImage.objects.create(product=product_instance, image=uploaded_image)

    # Step 2: Login as a normal customer (not superuser)
    client.force_login(customer_user)
    url = reverse("products:delete_gallery_image", kwargs={"pk": gallery_image.pk})

    # Step 3: Try deleting
    response = client.post(url)

    # Should be forbidden or redirect
    assert response.status_code in [302, 403]

    # Image should still exist
    assert ProductGalleryImage.objects.filter(pk=gallery_image.pk).exists()
