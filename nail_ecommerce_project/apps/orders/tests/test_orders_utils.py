import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

import razorpay
from nail_ecommerce_project.apps.orders.utils import (
    create_razorpay_order,
    deduct_variant_stock,
    send_order_placed_email,
    send_order_confirmed_email,
)

pytestmark = pytest.mark.django_db

# ✅ -------------------------
# TESTS for create_razorpay_order
# ✅ -------------------------

def test_create_razorpay_order_valid_amount(monkeypatch):
    """Should successfully create Razorpay order with valid amount"""
    mock_response = {"id": "order_test_id", "amount": 10000}

    def mock_create(params):
        assert params["amount"] == 10000  # ₹100
        return mock_response

    # Patch Razorpay client
    mock_client = MagicMock()
    mock_client.order.create.side_effect = mock_create
    monkeypatch.setattr(razorpay, "Client", lambda auth=None: mock_client)

    response = create_razorpay_order(Decimal("100.00"))
    assert response == mock_response


def test_create_razorpay_order_raises_for_amount_less_than_1():
    """Should raise ValueError if amount < ₹1.00"""
    with pytest.raises(ValueError) as exc:
        create_razorpay_order(Decimal("0.50"))
    assert "must be at least ₹1.00" in str(exc.value)


def test_create_razorpay_order_raises_for_non_numeric_amount():
    """Should raise AssertionError for invalid amount type"""
    with pytest.raises(AssertionError) as exc:
        create_razorpay_order("invalid_amount")
    assert "Amount must be a number" in str(exc.value)


def test_create_razorpay_order_handles_client_exception(monkeypatch):
    """Should raise if Razorpay client throws exception"""

    def mock_create(_):
        raise Exception("Razorpay API error")

    mock_client = MagicMock()
    mock_client.order.create.side_effect = mock_create
    monkeypatch.setattr(razorpay, "Client", lambda auth=None: mock_client)

    with pytest.raises(Exception) as exc:
        create_razorpay_order(Decimal("100.00"))
    assert "Razorpay API error" in str(exc.value)

# ✅ -------------------------
# TESTS for deduct_variant_stock
# ✅ -------------------------

def test_deduct_variant_stock_success(order_item):
    """Should deduct stock correctly"""
    order = order_item.order
    variant = order_item.product_variant

    assert variant.stock_quantity == 10  # initial
    deduct_variant_stock(order)

    variant.refresh_from_db()
    assert variant.stock_quantity == 9  # deducted 1


def test_deduct_variant_stock_exact_quantity(order_item):
    """Should allow exact stock deduction without negative"""
    variant = order_item.product_variant
    variant.stock_quantity = 1
    variant.save()

    deduct_variant_stock(order_item.order)

    variant.refresh_from_db()
    assert variant.stock_quantity == 0  # exactly zero


def test_deduct_variant_stock_raises_if_insufficient(order_item):
    """Should raise ValueError if stock < quantity"""
    variant = order_item.product_variant
    variant.stock_quantity = 0
    variant.save()

    with pytest.raises(ValueError) as exc:
        deduct_variant_stock(order_item.order)
    assert "Cannot deduct stock" in str(exc.value)

# ✅ -------------------------
# TESTS for email sending
# ✅ -------------------------

@pytest.mark.parametrize("email_func", [send_order_placed_email, send_order_confirmed_email])
def test_email_send_success(email_func, order, monkeypatch):
    """Should send email successfully when EmailMultiAlternatives.send() works"""

    class MockEmail:
        def attach_alternative(self, *_):
            return None
        def send(self):
            return 1  # success

    # Patch EmailMultiAlternatives
    monkeypatch.setattr(
        "nail_ecommerce_project.apps.orders.utils.EmailMultiAlternatives",
        lambda *args, **kwargs: MockEmail()
    )

    # Should NOT raise any exception
    email_func(order)


@pytest.mark.parametrize("email_func", [send_order_placed_email, send_order_confirmed_email])
def test_email_send_failure_logs_error(email_func, order, monkeypatch):
    """Should log error if email sending fails"""

    class MockEmail:
        def attach_alternative(self, *_):
            return None
        def send(self):
            raise Exception("SMTP Error")

    monkeypatch.setattr(
        "nail_ecommerce_project.apps.orders.utils.EmailMultiAlternatives",
        lambda *args, **kwargs: MockEmail()
    )

    # Should NOT raise, only log
    email_func(order)
