import pytest
from decimal import Decimal
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

from nail_ecommerce_project.apps.orders.cart import Cart, BuyNowCart
from nail_ecommerce_project.apps.products.models import Product, ProductVariant, ProductCategory

pytestmark = pytest.mark.django_db  # DB access required for tests


# ===================== HELPERS =====================

def add_session_to_request(request):
    """Attach a session to a request (needed for Cart & BuyNowCart)."""
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()


@pytest.fixture
def product_variant():
    """Create a valid ProductVariant for testing."""
    category = ProductCategory.objects.create(name="Test Category")
    product = Product.objects.create(name="Test Product", description="A test product")
    product.categories.add(category)
    return ProductVariant.objects.create(
        product=product,
        size="M",
        color="Red",
        price=Decimal("100.00"),
        stock_quantity=10
    )


@pytest.fixture
def cart_request():
    """Return a request with an attached session."""
    factory = RequestFactory()
    request = factory.get("/")
    add_session_to_request(request)
    return request


@pytest.fixture
def cart(cart_request):
    return Cart(cart_request)


@pytest.fixture
def buy_now_request():
    """Request with session for BuyNowCart."""
    factory = RequestFactory()
    request = factory.get("/")
    add_session_to_request(request)
    return request


# ===================== CART TESTS =====================

def test_cart_initially_empty(cart):
    """Cart should be empty on first init."""
    assert len(cart) == 0
    assert cart.get_total_price() == Decimal("0.00")
    assert list(cart) == []


def test_add_valid_variant_increases_quantity(cart, product_variant):
    """Adding a valid variant should increase cart length & total."""
    cart.add(product_variant, quantity=2)
    assert len(cart) == 2
    assert cart.get_total_price() == Decimal("200.00")

    # Add same variant again
    cart.add(product_variant, quantity=3)
    assert len(cart) == 5
    assert cart.get_total_price() == Decimal("500.00")

    # Session should reflect updated quantity
    vid = str(product_variant.pk)
    assert cart.session[Cart.SESSION_KEY][vid]["quantity"] == 5


def test_add_zero_or_negative_quantity_does_nothing(cart, product_variant):
    """Adding 0 or negative quantity should not change cart."""
    cart.add(product_variant, quantity=0)
    cart.add(product_variant, quantity=-2)
    assert len(cart) == 0
    assert cart.get_total_price() == Decimal("0.00")
    assert list(cart) == []


def test_add_invalid_price_type_is_ignored(cart):
    """Adding a variant with invalid price type should be ignored."""
    # Fake variant-like object
    class FakeVariant:
        pk = "999"
        price = "not-a-decimal"

        def __str__(self):
            return "FakeVariant"

    cart.add(FakeVariant(), quantity=1)
    assert len(cart) == 0
    assert list(cart) == []


def test_remove_variant_from_cart(cart, product_variant):
    """Removing an existing variant should update the cart."""
    cart.add(product_variant, quantity=2)
    assert len(cart) == 2

    # Remove it
    cart.remove(product_variant)
    assert len(cart) == 0
    assert list(cart) == []


def test_remove_non_existing_variant_is_safe(cart, product_variant):
    """Removing a non-existing variant should not error."""
    cart.remove(product_variant)  # Nothing happens
    assert len(cart) == 0  # Still empty


def test_cart_iteration_returns_correct_items(cart, product_variant):
    """Iterating over cart should yield correct item details."""
    cart.add(product_variant, quantity=2)

    items = list(cart)
    assert len(items) == 1
    item = items[0]

    assert item["variant"] == product_variant
    assert item["quantity"] == 2
    assert item["price"] == Decimal("100.00")
    assert item["total_price"] == Decimal("200.00")


def test_cart_iter_skips_deleted_variants(cart, product_variant):
    """If a variant was deleted from DB, iter should skip it."""
    cart.add(product_variant, quantity=2)

    # Delete variant from DB
    product_variant.delete()

    items = list(cart)
    assert len(items) == 0  # Skipped because variant not found


def test_clear_cart_resets_session(cart, product_variant):
    """Clearing cart should remove all session data."""
    cart.add(product_variant, quantity=2)
    assert len(cart) == 2

    cart.clear()
    assert len(cart) == 0
    assert Cart.SESSION_KEY not in cart.session  # Session key removed


def test_cart_json_serializable_format(cart, product_variant):
    """Ensure JSON serializable output structure."""
    cart.add(product_variant, quantity=3)

    json_data = cart.get_items_as_json_serializable()
    assert isinstance(json_data, list)
    assert json_data[0]["variant_id"] == product_variant.id
    assert json_data[0]["product_name"] == product_variant.product.name
    assert json_data[0]["quantity"] == 3
    assert json_data[0]["price"] == 100.0  # Converted to float


# ===================== BUY NOW CART TESTS =====================

def test_buy_now_valid_session_data(buy_now_request, product_variant):
    """Valid buy_now session returns correct item details."""
    buy_now_request.session[BuyNowCart.SESSION_KEY] = {
        "variant_id": product_variant.id,
        "quantity": 2,
        "price": "150.00"
    }
    cart = BuyNowCart(buy_now_request)

    item = cart.get_item()
    assert item["variant"] == product_variant
    assert item["quantity"] == 2
    assert item["price"] == Decimal("150.00")
    assert item["total_price"] == Decimal("300.00")


def test_buy_now_missing_quantity_defaults_to_1(buy_now_request, product_variant):
    buy_now_request.session[BuyNowCart.SESSION_KEY] = {
        "variant_id": product_variant.id,
        "price": "120.00"
    }
    cart = BuyNowCart(buy_now_request)
    item = cart.get_item()
    assert item["quantity"] == 1  # Defaults to 1


def test_buy_now_missing_price_backfills_from_variant(buy_now_request, product_variant):
    buy_now_request.session[BuyNowCart.SESSION_KEY] = {
        "variant_id": product_variant.id,
        "quantity": 1
        # missing price
    }
    cart = BuyNowCart(buy_now_request)
    item = cart.get_item()
    assert item["price"] == Decimal("100.00")  # Backfilled
    assert item["total_price"] == Decimal("100.00")


def test_buy_now_invalid_price_clears_session(buy_now_request, product_variant):
    buy_now_request.session[BuyNowCart.SESSION_KEY] = {
        "variant_id": product_variant.id,
        "quantity": 1,
        "price": "not-a-price"
    }
    cart = BuyNowCart(buy_now_request)
    assert cart.get_item() is None  # Clears session due to invalid price


def test_buy_now_variant_not_found_returns_none(buy_now_request):
    """If variant is deleted, should return None."""
    buy_now_request.session[BuyNowCart.SESSION_KEY] = {
        "variant_id": 9999,
        "quantity": 1,
        "price": "120.00"
    }
    cart = BuyNowCart(buy_now_request)
    assert cart.get_item() is None


def test_buy_now_clear_resets_session(buy_now_request, product_variant):
    """Clearing BuyNowCart should remove session key."""
    buy_now_request.session[BuyNowCart.SESSION_KEY] = {
        "variant_id": product_variant.id,
        "quantity": 1,
        "price": "120.00"
    }
    cart = BuyNowCart(buy_now_request)
    cart.clear()
    assert BuyNowCart.SESSION_KEY not in buy_now_request.session
    assert cart.get_item() is None
