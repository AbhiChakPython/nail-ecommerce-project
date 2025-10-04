import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

@pytest.fixture
def admin_user(django_user_model):
    # Create a superuser for admin access
    return django_user_model.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password123"
    )

def test_products_admin_pages_load(client, admin_user):
    # Login as admin
    client.force_login(admin_user)

    # All admin changelist pages we want to check
    urls = [
        reverse('admin:products_product_changelist'),
        reverse('admin:products_productcategory_changelist'),
        reverse('admin:products_productvariant_changelist'),
        reverse('admin:products_productgalleryimage_changelist'),
    ]

    # Visit each page → should return 200 OK
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200, f"Admin page {url} failed to load"
