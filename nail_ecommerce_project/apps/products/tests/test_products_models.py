import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from nail_ecommerce_project.apps.products.models import (
    ProductCategory, Product, ProductVariant, ProductGalleryImage
)

pytestmark = pytest.mark.django_db


def test_product_category_slug_autogeneration():
    category = ProductCategory.objects.create(name="Nail Art")
    assert category.slug == "nail-art"
    assert str(category) == "Nail Art"


def test_product_slug_autogeneration():
    product = Product.objects.create(name="Glitter Polish", description="Shiny finish")
    assert product.slug == "glitter-polish"
    assert str(product) == "Glitter Polish"


def test_product_discount_regular_only():
    product = Product.objects.create(name="Matte Polish", discount_percent=20)
    base_price = Decimal("100.00")
    discounted = product.get_discounted_price(base_price)
    assert discounted == Decimal("80.00")


def test_product_lto_discount_applied(monkeypatch):
    product = Product.objects.create(
        name="LTO Polish",
        discount_percent=10,
        lto_discount_percent=30,
        lto_start_date=timezone.now() - timezone.timedelta(days=1),
        lto_end_date=timezone.now() + timezone.timedelta(days=1)
    )
    base_price = Decimal("100.00")
    discounted = product.get_discounted_price(base_price)
    assert discounted == Decimal("70.00")


def test_product_lto_not_applied_outside_period():
    product = Product.objects.create(
        name="Expired LTO Polish",
        discount_percent=10,
        lto_discount_percent=30,
        lto_start_date=timezone.now() - timezone.timedelta(days=10),
        lto_end_date=timezone.now() - timezone.timedelta(days=5)
    )
    base_price = Decimal("100.00")
    discounted = product.get_discounted_price(base_price)
    assert discounted == Decimal("90.00")  # fallback to regular discount


def test_product_is_lto_active_true():
    product = Product.objects.create(
        name="Active LTO",
        lto_discount_percent=15,
        lto_start_date=timezone.now() - timezone.timedelta(days=1),
        lto_end_date=timezone.now() + timezone.timedelta(days=1)
    )
    assert product.is_lto_active() is True


def test_product_is_lto_active_false():
    product = Product.objects.create(
        name="Inactive LTO",
        lto_discount_percent=15,
        lto_start_date=timezone.now() - timezone.timedelta(days=5),
        lto_end_date=timezone.now() - timezone.timedelta(days=1)
    )
    assert product.is_lto_active() is False


def test_product_clean_raises_validation_error():
    product = Product(
        name="Invalid LTO Product",
        lto_discount_percent=25,
        lto_start_date=None,
        lto_end_date=None
    )
    with pytest.raises(ValidationError):
        product.clean()


def test_product_variant_discounted_price():
    product = Product.objects.create(name="Combo Polish", discount_percent=10)
    variant = ProductVariant.objects.create(
        product=product,
        size="Large",
        color="Red",
        price=Decimal("200.00"),
        stock_quantity=5
    )
    assert variant.get_discounted_price() == Decimal("180.00")
    assert str(variant) == "Combo Polish - Large - Red"


def test_product_gallery_image_str():
    product = Product.objects.create(name="Shimmer Set")
    image = ProductGalleryImage.objects.create(product=product, image="dummy.jpg")
    assert str(image) == "Image for Shimmer Set"


def test_product_variant_updates_availability():
    product = Product.objects.create(name="Stock Test Product")
    variant = ProductVariant.objects.create(
        product=product,
        size="Medium",
        color="Blue",
        price=Decimal("150.00"),
        stock_quantity=0
    )

    # Initially stock is 0 → product should become unavailable
    variant.update_availability_status()
    product.refresh_from_db()
    assert product.is_available is False

    # Increase stock → product should become available
    variant.stock_quantity = 10
    variant.save()
    variant.update_availability_status()
    product.refresh_from_db()
    assert product.is_available is True


def test_product_no_discounts_returns_same_price():
    product = Product.objects.create(name="No Discount Product", discount_percent=0)
    base_price = Decimal("50.00")
    discounted = product.get_discounted_price(base_price)
    assert discounted == Decimal("50.00")


def test_product_lto_takes_priority_over_regular_discount():
    product = Product.objects.create(
        name="Priority LTO",
        discount_percent=20,
        lto_discount_percent=50,
        lto_start_date=timezone.now() - timezone.timedelta(days=1),
        lto_end_date=timezone.now() + timezone.timedelta(days=1)
    )
    base_price = Decimal("100.00")
    discounted = product.get_discounted_price(base_price)
    assert discounted == Decimal("50.00")  # LTO wins
