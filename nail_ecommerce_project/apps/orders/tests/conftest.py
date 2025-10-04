from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from nail_ecommerce_project.apps.products.models import ProductVariant, Product
from nail_ecommerce_project.apps.orders.models import Order, OrderItem
from nail_ecommerce_project.apps.users.models import CustomerAddress
from rest_framework.test import APIClient

User = get_user_model()

# --------------------------
# USER FIXTURES
# --------------------------

@pytest.fixture
def test_user(db):
    """Basic user without address"""
    user = User(
        username="testuser",
        email="testuser@example.com",
        role='customer'
    )
    user.set_password("testpass123")
    user.save()
    return user

@pytest.fixture
def test_user_with_address(db):
    """User with a linked CustomerAddress (needed for payment callbacks)"""
    user = User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
        role="customer"
    )
    CustomerAddress.objects.create(
        user=user,
        address_line1="Line 1",
        address_line2="Line 2",
        city="Test City",
        state="Test State",
        pincode="123456",
        landmark="Near Test Landmark",
        use_for_home_service=True
    )
    return user

# --------------------------
# PRODUCT & ORDER FIXTURES
# --------------------------

@pytest.fixture
def product_variant(db):
    product = Product.objects.create(
        name="Test Product",
        description="Test product description",
        slug="test-product"
    )
    return ProductVariant.objects.create(
        product=product,
        size="M",
        color="Red",
        price=Decimal("100.00"),
        stock_quantity=10
    )

@pytest.fixture
def order(test_user_with_address):
    return Order.objects.create(
        user=test_user_with_address,
        full_name="Test User",
        phone="1234567890",
        address_line1="Line 1",
        address_line2="Line 2",
        city="Test City",
        postal_code="123456",
        state="Test State"
    )

@pytest.fixture
def order_item(order, product_variant):
    return OrderItem.objects.create(
        order=order,
        product_variant=product_variant,
        quantity=1,
        price_at_order=product_variant.price
    )

@pytest.fixture
def order_with_razorpay(order):
    order.razorpay_order_id = "test_razorpay_order_id"
    order.save()
    return order

# --------------------------
# CART SESSION FIXTURES
# --------------------------

@pytest.fixture
def cart_with_valid_variant(client, product_variant):
    """Add a normal cart with 1 item"""
    session = client.session
    session['cart'] = {
        str(product_variant.id): {
            'quantity': 1,
            'price': str(product_variant.price)
        }
    }
    session.save()
    return session

@pytest.fixture
def pre_payment_cart_session(client, product_variant):
    """Simulate a pre_payment_cart before callback"""
    session = client.session
    session['pre_payment_cart'] = [{
        'variant_id': product_variant.id,
        'quantity': 2,
        'price': str(product_variant.price)
    }]
    session['cart_razorpay_order_id'] = "test_razorpay_order_id"
    session.save()
    return session

@pytest.fixture
def pre_payment_buy_now_callback_session(client, product_variant):
    """Session setup for BuyNowCallbackView (uses pre_payment_buy_now)."""
    session = client.session
    session['pre_payment_buy_now'] = [
        {
            'variant_id': product_variant.id,
            'quantity': 1,
            'price': str(product_variant.price),
        }
    ]
    session.save()
    return session

@pytest.fixture
def buy_now_cart_session(client, product_variant):
    """Simulates BuyNowCart session for BuyNowPaymentVerifyView"""
    session = client.session
    session['buy_now'] = {
        'variant_id': product_variant.id,
        'quantity': 1,
        'price': str(product_variant.price)
    }
    session.save()
    return session

# --------------------------
# RAZORPAY MOCK FIXTURES
# --------------------------

@pytest.fixture(autouse=True)
def mock_razorpay(monkeypatch):
    """Mock create_razorpay_order always returns fake order_id"""
    monkeypatch.setattr(
        "nail_ecommerce_project.apps.orders.utils.create_razorpay_order",
        lambda amount, currency='INR': {"id": "test_razorpay_order_id"}
    )

@pytest.fixture
def mock_verify_signature_success(monkeypatch):
    """Mocks Razorpay verify_payment_signature to always succeed."""
    class MockRazorpayClient:
        def __init__(self, *args, **kwargs):
            self.utility = self
        def verify_payment_signature(self, params):
            return True
    monkeypatch.setattr("razorpay.Client", MockRazorpayClient)
    return MockRazorpayClient

@pytest.fixture
def mock_verify_signature_failure(monkeypatch):
    """Mocks Razorpay verify_payment_signature to raise SignatureVerificationError."""
    from razorpay.errors import SignatureVerificationError
    class MockRazorpayClient:
        def __init__(self, *args, **kwargs):
            self.utility = self
        def verify_payment_signature(self, params):
            raise SignatureVerificationError("Invalid signature", "error")
    monkeypatch.setattr("razorpay.Client", MockRazorpayClient)
    return MockRazorpayClient

# --------------------------
# EMAIL & STOCK MOCKS
# --------------------------

@pytest.fixture
def mock_send_order_email(monkeypatch):
    """Avoid sending real emails during tests."""
    monkeypatch.setattr(
        "nail_ecommerce_project.apps.orders.views_payment.send_order_placed_email",
        lambda order: True
    )

@pytest.fixture
def mock_deduct_stock(monkeypatch):
    """Avoid modifying real stock during tests."""
    monkeypatch.setattr(
        "nail_ecommerce_project.apps.orders.views_payment.deduct_variant_stock",
        lambda order: True
    )


@pytest.fixture
def order_with_status(test_user_with_address):
    """Factory fixture to create an order with a custom status."""
    def _create(status="PENDING"):
        return Order.objects.create(
            user=test_user_with_address,
            full_name="Test User",
            phone="1234567890",
            address_line1="Line 1",
            address_line2="Line 2",
            city="Test City",
            postal_code="123456",
            state="Test State",
            status=status
        )
    return _create

@pytest.fixture
def multiple_product_variants(db):
    """Create multiple variants for testing multi-item orders."""
    from decimal import Decimal
    from nail_ecommerce_project.apps.products.models import Product, ProductVariant

    product1 = Product.objects.create(
        name="Product A",
        description="First product",
        slug="product-a"
    )
    product2 = Product.objects.create(
        name="Product B",
        description="Second product",
        slug="product-b"
    )

    variant1 = ProductVariant.objects.create(
        product=product1,
        size="M",
        color="Red",
        price=Decimal("150.00"),
        stock_quantity=5
    )

    variant2 = ProductVariant.objects.create(
        product=product2,
        size="L",
        color="Blue",
        price=Decimal("200.00"),
        stock_quantity=2
    )

    return [variant1, variant2]


@pytest.fixture
def api_client():
    """Unauthenticated DRF client"""
    return APIClient()

@pytest.fixture
def api_user(db, django_user_model):
    """Normal customer user"""
    return django_user_model.objects.create_user(
        username="apiuser",
        email="apiuser@example.com",
        password="testpass123",
        role="customer"
    )

@pytest.fixture
def api_admin(db, django_user_model):
    """Admin/staff user"""
    return django_user_model.objects.create_user(
        username="apiadmin",
        email="apiadmin@example.com",
        password="adminpass123",
        role="admin",
        is_staff=True
    )

@pytest.fixture
def auth_api_client_user(api_client, api_user):
    """Authenticated API client for normal user"""
    api_client.force_authenticate(user=api_user)
    return api_client

@pytest.fixture
def auth_api_client_admin(api_client, api_admin):
    """Authenticated API client for admin"""
    api_client.force_authenticate(user=api_admin)
    return api_client
