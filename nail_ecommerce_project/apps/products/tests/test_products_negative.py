import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth import get_user_model
from nail_ecommerce_project.apps.products.models import Product, ProductVariant

User = get_user_model()


@pytest.mark.django_db
def test_gallery_upload_invalid_image_fails(client):
    # Arrange: login as admin
    admin = User.objects.create_user(
        username="admin", email="admin@example.com", password="adminpass", is_superuser=True
    )
    client.force_login(admin)

    # Create test product
    product = Product.objects.create(name="Test Product", slug="test-product")

    # Upload invalid "text" file pretending to be an image
    invalid_file = SimpleUploadedFile("test.txt", b"not an image", content_type="text/plain")
    url = reverse("products:manage_gallery", kwargs={"slug": product.slug})

    # Act
    response = client.post(url, {"image": invalid_file})

    # Assert: Status code should be 200 (form re-rendered with errors)
    assert response.status_code == 200

    # Strong match: error message present in content
    assert (
        b"The file you uploaded was either not an image or a corrupted image" in response.content or
        b"Upload a valid image" in response.content
    )



@pytest.mark.django_db
def test_manage_gallery_access_denied_for_non_admin(client):
    user = User.objects.create_user(username='user', email='user@example.com', password='testpass', is_superuser=False)
    client.force_login(user)

    product = Product.objects.create(name="NonAdmin Product", slug="nonadmin-product")

    url = reverse("products:manage_gallery", kwargs={"slug": product.slug})

    response = client.get(url)

    assert response.status_code in (302, 403)  # Redirect or Forbidden



@pytest.mark.django_db
def test_product_detail_view_404_invalid_slug(client):
    url = reverse("products:product_detail", kwargs={"slug": "non-existent-product"})

    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_product_list_view_shows_only_available_products(client):
    Product.objects.create(name="Visible Product", slug="visible", is_available=True)
    Product.objects.create(name="Hidden Product", slug="hidden", is_available=False)

    url = reverse("products:product_list")

    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()

    assert "Visible Product" in content
    assert "Hidden Product" not in content  # Negative check
