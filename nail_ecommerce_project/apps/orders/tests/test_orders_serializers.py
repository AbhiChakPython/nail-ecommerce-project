import pytest
from rest_framework.exceptions import ValidationError
from nail_ecommerce_project.apps.orders.serializers import OrderSerializer
from nail_ecommerce_project.apps.orders.models import Order, OrderItem


@pytest.mark.django_db
def test_order_serializer_creates_valid_order(client, test_user_with_address, multiple_product_variants):
    """✅ Positive Case: Should create a valid order with multiple items"""
    user = test_user_with_address
    variants = multiple_product_variants

    # Prepare request-like context
    request = type("DummyRequest", (), {"user": user})

    # ✅ Valid payload
    payload = {
        "full_name": "Test User",
        "phone": "1234567890",
        "address_line1": "Line 1",
        "address_line2": "Line 2",
        "city": "Test City",
        "postal_code": "123456",
        "state": "Test State",
        "order_items": [
            {"product_variant_id": variants[0].id, "quantity": 1},
            {"product_variant_id": variants[1].id, "quantity": 2}
        ]
    }

    serializer = OrderSerializer(data=payload, context={"request": request})
    assert serializer.is_valid(), serializer.errors

    order = serializer.save()

    # ✅ Assertions
    assert Order.objects.count() == 1
    assert OrderItem.objects.count() == 2
    assert order.user == user
    assert order.items.count() == 2
    assert order.total_price == (variants[0].price * 1 + variants[1].price * 2)


@pytest.mark.django_db
def test_order_serializer_insufficient_stock(client, test_user_with_address, product_variant):
    """❌ Negative Case: Should fail when stock is insufficient"""
    user = test_user_with_address

    # Set very low stock
    product_variant.stock_quantity = 1
    product_variant.save()

    request = type("DummyRequest", (), {"user": user})

    payload = {
        "full_name": "Stock Fail",
        "phone": "1234567890",
        "address_line1": "Line 1",
        "city": "Test City",
        "postal_code": "123456",
        "state": "Test State",
        "order_items": [
            {"product_variant_id": product_variant.id, "quantity": 5}  # requesting 5 but stock=1
        ]
    }

    serializer = OrderSerializer(data=payload, context={"request": request})
    is_valid = serializer.is_valid()

    # ✅ Should fail
    assert is_valid is False
    assert "order_items" in serializer.errors


@pytest.mark.django_db
def test_order_serializer_empty_items(client, test_user_with_address):
    """⚠️ Edge Case: Should fail if no items are provided"""
    user = test_user_with_address
    request = type("DummyRequest", (), {"user": user})

    payload = {
        "full_name": "Empty Case",
        "phone": "1234567890",
        "address_line1": "Line 1",
        "city": "Test City",
        "postal_code": "123456",
        "state": "Test State",
        "order_items": []  # empty list
    }

    serializer = OrderSerializer(data=payload, context={"request": request})
    is_valid = serializer.is_valid()

    assert is_valid is False
    assert "order_items" in serializer.errors
