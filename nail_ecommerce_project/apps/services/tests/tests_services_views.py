import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from nail_ecommerce_project.apps.services.models import Service, ServiceGalleryImage

# -------------------------------
# Public Views
# -------------------------------

@pytest.mark.django_db
def test_service_list_view_renders(client):
    response = client.get(reverse("services:service_list"))
    assert response.status_code == 200
    assert "services" in response.context

@pytest.mark.django_db
def test_service_detail_view_valid_slug(client, service):
    response = client.get(reverse("services:service_detail", args=[service.slug]))
    assert response.status_code == 200
    assert response.context["service"] == service

@pytest.mark.django_db
def test_service_detail_view_invalid_slug(client):
    response = client.get(reverse("services:service_detail", args=["non-existent"]))
    assert response.status_code == 404

# -------------------------------
# Admin Views — Require Superuser
# -------------------------------

@pytest.mark.django_db
def test_service_create_view_requires_login(client):
    url = reverse("services:service_create")
    response = client.get(url)
    assert response.status_code == 302  # redirected to login

@pytest.mark.django_db
def test_service_create_view_superuser_get(superuser_client):
    url = reverse("services:service_create")
    response = superuser_client.get(url)
    assert response.status_code == 200
    assert "form" in response.context

@pytest.mark.django_db
def test_service_create_view_post_valid(superuser_client):
    url = reverse("services:service_create")
    response = superuser_client.post(url, {
        "title": "New Service",
        "price": 500,
        "duration_minutes": 30,
        "is_active": True
    })
    assert response.status_code == 302  # redirect on success
    assert Service.objects.filter(title="New Service").exists()

@pytest.mark.django_db
def test_service_update_view_post_valid(superuser_client, service):
    url = reverse("services:service_update", args=[service.slug])
    response = superuser_client.post(url, {
        "title": "Updated Service",
        "price": 999,
        "duration_minutes": 60,
        "is_active": False
    })
    assert response.status_code == 302
    service.refresh_from_db()
    assert service.title == "Updated Service"

@pytest.mark.django_db
def test_service_delete_view_superuser(superuser_client, service):
    url = reverse("services:service_delete", args=[service.slug])
    response = superuser_client.post(url)
    assert response.status_code == 302
    assert not Service.objects.filter(pk=service.pk).exists()

# -------------------------------
# Gallery View
# -------------------------------

@pytest.mark.django_db
def test_manage_service_gallery_get(superuser_client, service):
    url = reverse("services:service_manage_gallery", args=[service.slug])
    response = superuser_client.get(url)
    assert response.status_code == 200
    assert "gallery_images" in response.context

@pytest.mark.django_db
def test_manage_service_gallery_post_image_upload(superuser_client, service, valid_image_file):
    url = reverse("services:service_manage_gallery", args=[service.slug])

    data = {
        "caption": "Test Image",
        "image_file": valid_image_file,
    }

    response = superuser_client.post(url, data=data)

    if response.status_code == 200:
        print("Form submission failed. Errors:")
        print(response.context["form"].errors.as_json())

    assert response.status_code == 302
    assert service.gallery_images.exists()

@pytest.mark.django_db
def test_service_create_view_superuser_invalid_post(superuser_client):
    url = reverse("services:service_create")
    response = superuser_client.post(url, {
        "title": "",  # missing title
        "price": "",  # missing price
    })
    assert response.status_code == 200  # form re-rendered
    assert "form" in response.context
    assert not Service.objects.filter(title="").exists()


@pytest.mark.django_db
def test_service_create_view_non_superuser_forbidden(client, django_user_model):
    user = django_user_model.objects.create_user(username="normal", email="normal@example.com", password="pass")
    client.force_login(user)
    url = reverse("services:service_create")
    response = client.get(url)
    assert response.status_code == 403  # forbidden


@pytest.mark.django_db
def test_manage_gallery_view_non_superuser_denied(client, django_user_model, service):
    user = django_user_model.objects.create_user(username="user", email="user@example.com", password="pass")
    client.force_login(user)
    url = reverse("services:service_manage_gallery", args=[service.slug])
    response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_service_list_view_search_filtering(client, service):
    url = reverse("services:service_list") + "?q=" + service.title[:4]
    response = client.get(url)
    assert response.status_code == 200
    services = response.context["services"]
    assert service in services


@pytest.mark.django_db
def test_service_update_view_invalid_data(superuser_client, service):
    url = reverse("services:service_update", args=[service.slug])
    response = superuser_client.post(url, {
        "title": "",  # invalid: blank
        "price": 250,
        "duration_minutes": 30,
        "is_active": True,
    })
    assert response.status_code == 200
    assert "form" in response.context
    service.refresh_from_db()
    assert service.title != ""


# -------------------------------
# Missing Edge Case Tests
# -------------------------------

@pytest.mark.django_db
def test_service_list_view_pagination(client):
    # Create 7 services (pagination is 6 per page)
    for i in range(7):
        Service.objects.create(title=f"Service {i}", price=100)

    url = reverse("services:service_list")
    response_page1 = client.get(url)
    assert response_page1.status_code == 200
    assert len(response_page1.context["services"]) == 6  # first page should show only 6

    response_page2 = client.get(url + "?page=2")
    assert response_page2.status_code == 200
    assert len(response_page2.context["services"]) == 1  # remaining 1 on second page


@pytest.mark.django_db
def test_manage_service_gallery_post_invalid_missing_image(superuser_client, service):
    url = reverse("services:service_manage_gallery", args=[service.slug])

    # Missing image_file should cause form errors
    response = superuser_client.post(url, {"caption": "No image"})
    assert response.status_code == 200  # form should re-render
    assert "form" in response.context
    assert "image_file" in response.context["form"].errors


@pytest.mark.django_db
def test_manage_gallery_view_anonymous_redirects_login(client, service):
    url = reverse("services:service_manage_gallery", args=[service.slug])
    response = client.get(url)
    assert response.status_code == 302
    assert "/users/login/" in response.url  # should redirect to login


@pytest.mark.django_db
def test_anonymous_user_redirects_on_update_delete(client, service):
    update_url = reverse("services:service_update", args=[service.slug])
    delete_url = reverse("services:service_delete", args=[service.slug])

    # Both should redirect to login for anonymous users
    update_response = client.get(update_url)
    delete_response = client.get(delete_url)

    assert update_response.status_code == 302
    assert "/users/login/" in update_response.url
    assert delete_response.status_code == 302
    assert "/users/login/" in delete_response.url
