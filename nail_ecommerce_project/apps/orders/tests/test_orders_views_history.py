import pytest
from django.urls import reverse
from nail_ecommerce_project.apps.users.models import CustomUser
from nail_ecommerce_project.apps.orders.models import Order


@pytest.mark.django_db
def test_customer_order_list_view_shows_orders(client, test_user):
    client.login(username=test_user.username, password="testpass123")

    # Create two orders for this user
    Order.objects.create(user=test_user, full_name='Test User 1', phone='1234567890', address_line1='Line1', city='City', postal_code='12345', country='Country')
    Order.objects.create(user=test_user, full_name='Test User 2', phone='1234567890', address_line1='Line2', city='City', postal_code='12345', country='Country')

    response = client.get(reverse('orders:order_list'))

    assert response.status_code == 200
    assert len(response.context['orders']) == 2


@pytest.mark.django_db
def test_customer_order_list_shows_user_orders(client, test_user):
    Order.objects.create(
        user=test_user,
        full_name="Test User",
        phone="1234567890",
        address_line1="123 Main St",
        city="Testville",
        postal_code="123456",
        country="India",
        status="PROCESSING"
    )

    client.login(username=test_user.username, password="testpass123")
    response = client.get(reverse('orders:order_list'))

    assert response.status_code == 200
    assert "orders" in response.context
    assert len(response.context["orders"]) == 1
    assert response.context["orders"][0].user == test_user


def test_customer_order_list_requires_login(client):
    response = client.get(reverse('orders:order_list'))

    assert response.status_code == 302  # Should redirect to login
    assert "/users/login/" in response.url


@pytest.mark.django_db
def test_order_list_allows_non_customer(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="staffuser",
        email="staff@example.com",
        password="pass123",
        role="staff"
    )

    Order.objects.create(
        user=user,
        full_name="Staff User",
        phone="9876543210",
        address_line1="456 Market St",
        city="Metrocity",
        postal_code="654321",
        country="India",
        status="PLACED"
    )

    client.login(username="staffuser", password="pass123")
    response = client.get(reverse('orders:order_list'))

    assert response.status_code == 200
    assert len(response.context["orders"]) == 1
    assert response.context["orders"][0].user == user


@pytest.mark.django_db
def test_customer_order_list_empty_for_user(client, test_user):
    client.login(username=test_user.username, password='testpass123')
    response = client.get(reverse('orders:order_list'))
    assert response.status_code == 200
    assert 'orders' in response.context
    assert len(response.context['orders']) == 0