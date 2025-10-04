import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from nail_ecommerce_project.apps.orders.models import Order

User = get_user_model()


@pytest.mark.django_db
def test_order_success_view_valid_user(client, test_user):
    client.login(username=test_user.username, password="testpass123")

    # Create an order for the logged-in user
    order = Order.objects.create(
        user=test_user,
        full_name="John Doe",
        phone="1234567890",
        address_line1="123 Main St",
        city="City",
        postal_code="12345",
        country="Country",
        status="PLACED",
    )

    url = reverse("orders:order_success", kwargs={"order_id": order.id})
    response = client.get(url)

    assert response.status_code == 200
    assert "Order" in response.content.decode()


@pytest.mark.django_db
def test_order_success_view_other_user_forbidden(client, django_user_model, test_user):
    other_user = django_user_model.objects.create_user(
        username="hacker", email="hacker@example.com", password="hackerpass", role="customer"
    )

    order = Order.objects.create(
        user=other_user,
        full_name="Jane Hacker",
        phone="9999999999",
        address_line1="Secret Lane",
        city="Cyber City",
        postal_code="66666",
        country="Nowhere",
        status="PLACED",
    )

    client.login(username=test_user.username, password="testpass123")

    url = reverse("orders:order_success", kwargs={"order_id": order.id})
    response = client.get(url)

    # Expect a redirect to failed view if not owner
    assert response.status_code == 302
    assert reverse("orders:order_failed") in response.url


@pytest.mark.django_db
def test_order_success_view_unauthenticated_redirects(client):
    url = reverse("orders:order_success", kwargs={"order_id": 1})
    response = client.get(url)

    assert response.status_code == 302
    assert "/users/login/" in response.url


@pytest.mark.django_db
def test_order_failed_view_returns_200(client):
    url = reverse("orders:order_failed")
    response = client.get(url)

    assert response.status_code == 200
    assert "Failed" in response.content.decode()


@pytest.mark.django_db
def test_order_success_view_nonexistent_order(client, test_user):
    client.login(username=test_user.username, password="testpass123")

    # Pass a non-existent order_id
    url = reverse("orders:order_success", kwargs={"order_id": 99999})
    response = client.get(url)

    assert response.status_code == 302
    assert reverse("orders:order_failed") in response.url