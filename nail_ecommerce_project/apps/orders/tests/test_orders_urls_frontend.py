import pytest
from django.urls import reverse
from django.test import Client
from nail_ecommerce_project.apps.orders.models import Order

@pytest.mark.django_db
def test_cart_detail_view_accessible(client, test_user):
    client.login(username=test_user.username, password="testpass123")
    response = client.get(reverse('orders:cart_detail'))
    assert response.status_code == 200

@pytest.mark.django_db
def test_add_to_cart_requires_post(client, test_user):
    client.login(username=test_user.username, password="testpass123")
    response = client.get(reverse("orders:add_to_cart"))
    assert response.status_code == 405  # Method Not Allowed

@pytest.mark.django_db
def test_remove_from_cart_requires_login(client, product_variant):
    url = reverse('orders:cart_remove', args=[product_variant.id])
    response = client.get(url)
    assert response.status_code in [302, 403]  # redirect to login or forbidden

@pytest.mark.django_db
def test_checkout_redirects_for_unauthenticated_user(client):
    url = reverse('orders:checkout')
    response = client.get(url)
    assert response.status_code == 403

@pytest.mark.django_db
def test_buy_now_requires_login(client, product_variant):
    response = client.post(reverse("orders:buy_now"), {
        "variant_id": product_variant.id,
        "quantity": 1
    })
    assert response.status_code in [302, 403]

@pytest.mark.django_db
def test_payment_callback_url_exists(client):
    response = client.post(reverse('orders:payment_callback'))
    # 200/302/403/404 depending on data, just check endpoint is hooked
    assert response.status_code in [302, 403, 404]

@pytest.mark.django_db
def test_order_success_redirects_invalid_user(client, order):
    # Not logged in
    response = client.get(reverse('orders:order_success', args=[order.id]))
    assert response.status_code == 302

@pytest.mark.django_db
def test_order_failed_page_loads(client):
    response = client.get(reverse('orders:order_failed'))
    assert response.status_code == 200

@pytest.mark.django_db
def test_order_list_requires_login(client):
    response = client.get(reverse('orders:order_list'))
    assert response.status_code == 302

@pytest.mark.django_db
def test_order_list_authenticated(client, test_user):
    client.login(username=test_user.username, password="testpass123")
    response = client.get(reverse('orders:order_list'))
    assert response.status_code == 200