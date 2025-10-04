from io import BytesIO
import pytest
from PIL import Image
from django.urls import reverse
from nail_ecommerce_project.apps.products.models import Product
from nail_ecommerce_project.apps.products.forms import ProductGalleryImageForm
import os
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


def test_product_delete_view_get_confirmation(client, superuser, product_instance):
    client.force_login(superuser)
    url = reverse("products:product_delete", kwargs={"slug": product_instance.slug})
    response = client.get(url)
    assert response.status_code == 200
    assert "Are you sure you want to delete" in response.content.decode()


def test_product_delete_view_post_deletes_product(client, superuser, product_instance):
    client.force_login(superuser)
    url = reverse("products:product_delete", kwargs={"slug": product_instance.slug})
    response = client.post(url, follow=True)

    assert response.status_code == 200
    assert not Product.objects.filter(slug=product_instance.slug).exists()


def test_manage_gallery_view_get_superuser_access(client, superuser, product_instance):
    client.force_login(superuser)
    url = reverse("products:manage_gallery", kwargs={"slug": product_instance.slug})
    response = client.get(url)
    assert response.status_code == 200
    assert "Gallery image" in response.content.decode() or "Upload" in response.content.decode()


def test_product_gallery_image_form_valid(uploaded_image):
    form = ProductGalleryImageForm(files={'image': uploaded_image})
    assert form.is_valid(), form.errors


def test_gallery_upload_real_image(client, superuser, product_instance, django_user_model):
    client.force_login(superuser)

    # Provide full path to an actual image
    image_path = os.path.join(
        "D:/E-Commerce Project/media/products/gallery", "Ultra_Gloss_Gel_Polish1.jpg"
    )

    with open(image_path, "rb") as img_file:
        image = SimpleUploadedFile(
            name="Ultra_Gloss_Gel_Polish1.jpg",
            content=img_file.read(),
            content_type="image/jpeg"
        )

        response = client.post(
            reverse("products:manage_gallery", kwargs={"slug": product_instance.slug}),
            data={"image": image},
            follow=True
        )

    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    assert product_instance.gallery_images.exists(), "Image not saved to gallery"


def test_delete_gallery_image_view_deletes_image(client, superuser, product_instance, uploaded_image):
    from nail_ecommerce_project.apps.products.models import ProductGalleryImage

    # Step 1: Create image entry
    gallery_image = ProductGalleryImage.objects.create(product=product_instance, image=uploaded_image)

    # Step 2: Make POST request
    client.force_login(superuser)
    url = reverse("products:delete_gallery_image", kwargs={"pk": gallery_image.pk})
    response = client.post(url, follow=True)

    # Step 3: Assert deletion
    assert response.status_code == 200
    assert not ProductGalleryImage.objects.filter(pk=gallery_image.pk).exists()
