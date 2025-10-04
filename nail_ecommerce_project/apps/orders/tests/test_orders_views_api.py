import pytest
from decimal import Decimal
from django.urls import reverse
from nail_ecommerce_project.apps.orders.models import Order

pytestmark = pytest.mark.django_db  # all tests use DB

# --------------------------
# ORDER CREATE TESTS
# --------------------------
def test_order_create_authenticated(auth_api_client_user, multiple_product_variants):
    """✅ Authenticated user can create a valid order"""
    url = reverse("orders_api:order_create")
    payload = {
        "full_name": "Test API User",
        "phone": "1234567890",
        "address_line1": "Line 1",
        "address_line2": "Line 2",
        "city": "City",
        "postal_code": "12345",
        "state": "State",
        "order_items": [
            {"product_variant_id": multiple_product_variants[0].id, "quantity": 1},
            {"product_variant_id": multiple_product_variants[1].id, "quantity": 2},
        ]
    }

    response = auth_api_client_user.post(url, payload, format="json")

    print("Response status:", response.status_code)
    print("Response data:", response.data)

    # ✅ Only fetch order if creation succeeded
    assert response.status_code == 201
    assert Order.objects.count() == 1

    order = Order.objects.first()
    assert order.items.count() == 2

    # ✅ Compute expected dynamically
    expected_total = (
        multiple_product_variants[0].price * 1 +
        multiple_product_variants[1].price * 2
    )
    assert order.total_price == expected_total


def test_order_create_missing_fields(auth_api_client_user):
    """❌ Missing required fields → 400"""
    url = reverse("orders_api:order_create")
    response = auth_api_client_user.post(url, {}, format="json")
    assert response.status_code == 400
    assert "full_name" in response.data  # should list validation errors


def test_order_create_unauthenticated(api_client, multiple_product_variants):
    """❌ Unauthenticated user → 401"""
    url = reverse("orders_api:order_create")
    payload = {
        "full_name": "Test User",
        "phone": "12345",
        "address_line1": "Line1",
        "city": "City",
        "postal_code": "111",
        "state": "State",
        "order_items": [
            {"product_variant_id": multiple_product_variants[0].id, "quantity": 1},
        ]
    }
    response = api_client.post(url, payload, format="json")
    assert response.status_code == 403

# --------------------------
# ORDER LIST TESTS
# --------------------------
def test_order_list_user_sees_only_own_orders(auth_api_client_user, api_user):
    """✅ Normal user only sees their own orders"""
    # create orders for two users
    Order.objects.create(
        user=api_user, full_name="User A", phone="111", address_line1="L1", city="C", postal_code="123", state="S"
    )
    other_user_order = Order.objects.create(
        user=None, full_name="Other", phone="222", address_line1="L2", city="C2", postal_code="456", state="S2"
    )

    url = reverse("orders_api:order_list")
    response = auth_api_client_user.get(url)

    assert response.status_code == 200
    # should only return 1 order
    assert len(response.data) == 1
    assert response.data[0]["full_name"] == "User A"


def test_order_list_admin_sees_all(auth_api_client_admin, api_user):
    """✅ Admin sees all orders"""
    Order.objects.create(user=api_user, full_name="User A", phone="111", address_line1="L1", city="C", postal_code="123", state="S")
    Order.objects.create(user=api_user, full_name="User B", phone="222", address_line1="L2", city="C2", postal_code="456", state="S2")

    url = reverse("orders_api:order_list")
    response = auth_api_client_admin.get(url)

    assert response.status_code == 200
    assert len(response.data) == 2  # admin sees all


def test_order_list_unauthenticated(api_client):
    """❌ Unauthenticated → 401"""
    url = reverse("orders_api:order_list")
    response = api_client.get(url)
    assert response.status_code == 401

# --------------------------
# ORDER DETAIL TESTS
# --------------------------
def test_order_detail_owner_can_access(auth_api_client_user, api_user):
    """✅ Owner can retrieve their order"""
    order = Order.objects.create(
        user=api_user, full_name="User A", phone="111", address_line1="L1", city="C", postal_code="123", state="S"
    )
    url = reverse("orders_api:order_detail", args=[order.id])
    response = auth_api_client_user.get(url)
    assert response.status_code == 200
    assert response.data["full_name"] == "User A"


def test_order_detail_admin_can_access(auth_api_client_admin, api_user):
    """✅ Admin can access any order"""
    order = Order.objects.create(
        user=api_user, full_name="User A", phone="111", address_line1="L1", city="C", postal_code="123", state="S"
    )
    url = reverse("orders_api:order_detail", args=[order.id])
    response = auth_api_client_admin.get(url)
    assert response.status_code == 200
    assert response.data["full_name"] == "User A"


def test_order_detail_forbidden_for_other_user(auth_api_client_user, api_user, django_user_model):
    """❌ Other user cannot access → 403"""
    # another user
    another_user = django_user_model.objects.create_user(username="other", email="other@example.com", password="otherpass", role="customer")
    order = Order.objects.create(
        user=another_user, full_name="Other User", phone="999", address_line1="Lx", city="Cx", postal_code="999", state="Sx"
    )
    url = reverse("orders_api:order_detail", args=[order.id])
    response = auth_api_client_user.get(url)
    assert response.status_code == 403


def test_order_detail_unauthenticated(api_client, api_user):
    """❌ Unauthenticated → 401"""
    order = Order.objects.create(
        user=api_user, full_name="User A", phone="111", address_line1="L1", city="C", postal_code="123", state="S"
    )
    url = reverse("orders_api:order_detail", args=[order.id])
    response = api_client.get(url)
    assert response.status_code == 401
