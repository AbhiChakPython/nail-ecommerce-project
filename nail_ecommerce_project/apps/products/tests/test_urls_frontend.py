import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import Client
from nail_ecommerce_project.apps.products.models import Product, ProductGalleryImage

User = get_user_model()

@pytest.fixture
def superuser(db):
    return User.objects.create_user(username="admin", email="admin@example.com", password="adminpass", is_superuser=True)

@pytest.fixture
def customer_user(db):
    return User.objects.create_user(username="customer", email="customer@example.com", password="custpass", is_superuser=False)

@pytest.fixture
def product(db):
    return Product.objects.create(name="Test Product", slug="test-product", is_available=True)


@pytest.mark.django_db
def test_superuser_can_access_all_admin_views(superuser, product):
    client = Client()
    client.force_login(superuser)

    assert client.get(reverse("products:product_create")).status_code == 200
    assert client.get(reverse("products:product_update", kwargs={"slug": product.slug})).status_code == 200
    assert client.get(reverse("products:product_delete", kwargs={"slug": product.slug})).status_code == 200
    assert client.get(reverse("products:manage_variants", kwargs={"slug": product.slug})).status_code == 200
    assert client.get(reverse("products:manage_gallery", kwargs={"slug": product.slug})).status_code == 200


@pytest.mark.django_db
def test_customer_cannot_access_admin_views(customer_user, product):
    client = Client()
    client.force_login(customer_user)

    protected_urls = [
        reverse("products:product_create"),
        reverse("products:product_update", kwargs={"slug": product.slug}),
        reverse("products:product_delete", kwargs={"slug": product.slug}),
        reverse("products:manage_variants", kwargs={"slug": product.slug}),
        reverse("products:manage_gallery", kwargs={"slug": product.slug}),
    ]

    for url in protected_urls:
        response = client.get(url)
        assert response.status_code == 403  # PermissionDenied raised


@pytest.mark.django_db
def test_anonymous_user_redirected_to_login(product):
    client = Client()

    protected_urls = [
        reverse("products:product_create"),
        reverse("products:product_update", kwargs={"slug": product.slug}),
        reverse("products:product_delete", kwargs={"slug": product.slug}),
        reverse("products:manage_variants", kwargs={"slug": product.slug}),
        reverse("products:manage_gallery", kwargs={"slug": product.slug}),
    ]

    for url in protected_urls:
        response = client.get(url)

        # Views using IsSuperUserRequiredMixin return 403 instead of redirecting
        assert response.status_code == 302
        assert "/users/login/" in response.url


@pytest.mark.django_db
def test_public_can_view_list_and_detail(product):
    client = Client()
    list_url = reverse("products:product_list")
    detail_url = reverse("products:product_detail", kwargs={"slug": product.slug})

    assert client.get(list_url).status_code == 200
    assert client.get(detail_url).status_code == 200


@pytest.mark.django_db
def test_invalid_slug_returns_404():
    client = Client()
    response = client.get(reverse("products:product_detail", kwargs={"slug": "non-existent"}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_superuser_can_delete_gallery_image(superuser, product):
    client = Client()
    client.force_login(superuser)

    # Create gallery image
    image_file = SimpleUploadedFile("image.jpg", b"image data", content_type="image/jpeg")
    gallery_image = ProductGalleryImage.objects.create(product=product, image=image_file)

    delete_url = reverse("products:delete_gallery_image", kwargs={"pk": gallery_image.pk})
    response = client.post(delete_url)

    # Should redirect back to gallery page
    assert response.status_code == 302
    assert ProductGalleryImage.objects.filter(pk=gallery_image.pk).count() == 0
