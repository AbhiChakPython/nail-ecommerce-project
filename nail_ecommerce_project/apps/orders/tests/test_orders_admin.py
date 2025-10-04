import pytest
from unittest.mock import patch
from decimal import Decimal
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model

from nail_ecommerce_project.apps.orders.admin import OrderAdmin, OrderItemInline
from nail_ecommerce_project.apps.orders.models import Order, OrderItem
from nail_ecommerce_project.apps.products.models import ProductVariant, Product

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def admin_site():
    return AdminSite()

@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="pass1234"
    )

@pytest.fixture
def customer_user(db):
    return User.objects.create_user(
        username="customer",
        email="customer@example.com",
        password="pass1234"
    )

@pytest.fixture
def product_variant(db):
    product = Product.objects.create(
        name="Test Product",
        description="Dummy product for admin tests"
    )
    variant = ProductVariant.objects.create(
        product=product,
        size="M",
        color="Red",
        price="100.00",
        stock_quantity=10
    )
    return variant

@pytest.fixture
def order(customer_user):
    return Order.objects.create(
        user=customer_user,
        full_name="John Doe",
        phone="9876543210",
        address_line1="123 Street",
        city="City",
        postal_code="12345",
        state="State",
        status="PENDING",
    )

@pytest.fixture
def order_item(order, product_variant):
    return OrderItem.objects.create(
        order=order,
        product_variant=product_variant,
        quantity=2,
        price_at_order=Decimal("100.00"),
    )


def test_total_amount_display(order, order_item, admin_site):
    admin = OrderAdmin(Order, admin_site)
    expected_display = "₹200.00"
    assert admin.total_amount_display(order) == expected_display


def test_readonly_fields_include_razorpay_id(admin_site):
    admin = OrderAdmin(Order, admin_site)
    assert "razorpay_order_id" in admin.readonly_fields


def test_order_item_inline_settings():
    inline = OrderItemInline(Order, AdminSite())
    assert "product_variant" in inline.readonly_fields
    assert "quantity" in inline.readonly_fields
    assert inline.can_delete is False
    assert inline.extra == 0


@patch("nail_ecommerce_project.apps.orders.admin.send_order_confirmed_email")
def test_save_model_confirms_order_and_deducts_stock(mock_send_email, admin_user, order, order_item, product_variant, admin_site):
    admin = OrderAdmin(Order, admin_site)

    # Simulate status change → CONFIRMED
    order.status = "CONFIRMED"

    initial_stock = product_variant.stock_quantity

    admin.save_model(request=None, obj=order, form=None, change=True)

    product_variant.refresh_from_db()

    # ✅ Stock should reduce
    assert product_variant.stock_quantity == initial_stock - order_item.quantity

    # ✅ Email should be sent once
    mock_send_email.assert_called_once_with(order)


@patch("nail_ecommerce_project.apps.orders.admin.send_order_confirmed_email")
def test_save_model_does_not_deduct_if_status_unchanged(mock_send_email, order, order_item, product_variant, admin_site):
    admin = OrderAdmin(Order, admin_site)

    initial_stock = product_variant.stock_quantity

    # No status change → should not deduct
    admin.save_model(request=None, obj=order, form=None, change=True)

    product_variant.refresh_from_db()
    assert product_variant.stock_quantity == initial_stock  # unchanged
    mock_send_email.assert_not_called()


@patch("nail_ecommerce_project.apps.orders.admin.logger.warning")
def test_save_model_logs_warning_if_insufficient_stock(mock_logger, admin_user, order, order_item, product_variant, admin_site):
    admin = OrderAdmin(Order, admin_site)

    # Set stock less than needed
    product_variant.stock_quantity = 1
    product_variant.save()

    order.status = "CONFIRMED"

    admin.save_model(request=None, obj=order, form=None, change=True)

    product_variant.refresh_from_db()

    # Stock should remain same (no negative)
    assert product_variant.stock_quantity == 1

    # ✅ Warning should be logged
    mock_logger.assert_called_once()
    assert "Not enough stock" in mock_logger.call_args[0][0]


@patch("nail_ecommerce_project.apps.orders.admin.send_order_confirmed_email", side_effect=Exception("SMTP error"))
@patch("nail_ecommerce_project.apps.orders.admin.logger.error")
def test_save_model_email_failure_logs_error(mock_logger, mock_send_email, order, order_item, product_variant, admin_site):
    admin = OrderAdmin(Order, admin_site)

    order.status = "CONFIRMED"
    admin.save_model(request=None, obj=order, form=None, change=True)

    # Email send will raise → should log error
    mock_logger.assert_called_once()
    assert "failed to send confirmation email" in mock_logger.call_args[0][0]
