import pytest
from decimal import Decimal
from nail_ecommerce_project.apps.orders.models import Order, OrderItem

pytestmark = pytest.mark.django_db


def test_order_str_representation(order):
    assert str(order) == f"Order #{order.id} by {order.user}"


def test_order_item_str_representation(order_item):
    assert str(order_item) == f"{order_item.quantity} × {order_item.product_variant}"


def test_order_line_total(order, product_variant):
    order_item = OrderItem.objects.create(order=order, product_variant=product_variant, quantity=4, price_at_order=Decimal("50.00"))
    assert order_item.line_total == Decimal("200.00")
    assert order_item.get_total() == Decimal("200.00")


def test_order_with_no_items_returns_zero(order):
    assert order.total_price == 0
    assert order.total_discount == 0


def test_order_total_price_no_discount(order, product_variant):
    # No discount (price_at_order == product_variant.price)
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=2, price_at_order=product_variant.price)
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=3, price_at_order=product_variant.price)

    expected_total = (2 + 3) * product_variant.price
    assert order.total_price == expected_total
    assert order.total_discount == 0  # No discount


def test_order_total_price_and_discount(order, product_variant):
    # Discounted recorded price
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=2, price_at_order=Decimal("80.00"))
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=3, price_at_order=Decimal("90.00"))

    discounted_total = Decimal("80.00") * 2 + Decimal("90.00") * 3
    assert order.total_price == discounted_total

    original_total = product_variant.price * 5
    expected_discount = original_total - discounted_total
    assert order.total_discount == expected_discount


def test_order_total_discount_cannot_be_negative(order, product_variant):
    # Simulate price_at_order > original price → should NOT give negative discount
    high_price = product_variant.price + Decimal("50.00")
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=1, price_at_order=high_price)

    assert order.total_discount == 0  # discount cannot be negative


def test_order_cancel_restock_once(order, product_variant):
    initial_stock = product_variant.stock_quantity
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=2, price_at_order=product_variant.price)

    # Simulate real-world stock deduction before cancel
    product_variant.stock_quantity -= 2
    product_variant.save()

    # Cancel the order → restock once
    order.cancel_order(by_customer=True)
    order.refresh_from_db()
    assert order.status == "CANCELLED"
    assert order.cancelled_by_customer is True

    product_variant.refresh_from_db()
    assert product_variant.stock_quantity == initial_stock  # Restored correctly

    # Cancel again → should NOT double-restock
    order.cancel_order()
    product_variant.refresh_from_db()
    assert product_variant.stock_quantity == initial_stock  # Still same


def test_cancel_already_cancelled_order_does_nothing(order, product_variant):
    initial_stock = product_variant.stock_quantity
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=1, price_at_order=product_variant.price)

    # Simulate real-world deduction
    product_variant.stock_quantity -= 1
    product_variant.save()

    # Cancel twice → second cancel should not double restock
    order.cancel_order()
    order.cancel_order()
    product_variant.refresh_from_db()
    assert product_variant.stock_quantity == initial_stock  # No double restock
    assert order.status == "CANCELLED"


def test_order_decimal_precision(order, product_variant):
    # Model only stores 2 decimals
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=1, price_at_order=Decimal("99.9999"))

    # ✅ Should auto-round to 2 decimals → 100.00
    assert order.total_price == Decimal("100.00")


def test_deduct_variant_stock_integrity(order, product_variant):
    # Stock before
    initial_stock = product_variant.stock_quantity
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=5, price_at_order=product_variant.price)

    # Simulate stock deduction (as done in views)
    from nail_ecommerce_project.apps.orders.utils import deduct_variant_stock
    deduct_variant_stock(order)

    product_variant.refresh_from_db()
    assert product_variant.stock_quantity == initial_stock - 5
    assert product_variant.stock_quantity >= 0  # Never negative


def test_deduct_variant_stock_raises_error_on_insufficient_stock(order, product_variant):
    product_variant.stock_quantity = 3
    product_variant.save()

    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=5, price_at_order=product_variant.price)

    from nail_ecommerce_project.apps.orders.utils import deduct_variant_stock
    with pytest.raises(ValueError, match="Cannot deduct stock"):
        deduct_variant_stock(order)

import pytest
from decimal import Decimal
from nail_ecommerce_project.apps.orders.models import Order, OrderItem

pytestmark = pytest.mark.django_db


# ✅ Existing tests already present...

def test_order_str_representation(order):
    assert str(order) == f"Order #{order.id} by {order.user}"


def test_order_item_str_representation(order_item):
    assert str(order_item) == f"{order_item.quantity} × {order_item.product_variant}"


def test_order_line_total(order, product_variant):
    order_item = OrderItem.objects.create(order=order, product_variant=product_variant, quantity=4, price_at_order=Decimal("50.00"))
    assert order_item.line_total == Decimal("200.00")
    assert order_item.get_total() == Decimal("200.00")


def test_order_with_no_items_returns_zero(order):
    assert order.total_price == 0
    assert order.total_discount == 0


def test_order_total_price_no_discount(order, product_variant):
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=2, price_at_order=product_variant.price)
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=3, price_at_order=product_variant.price)

    expected_total = (2 + 3) * product_variant.price
    assert order.total_price == expected_total
    assert order.total_discount == 0


def test_order_total_price_and_discount(order, product_variant):
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=2, price_at_order=Decimal("80.00"))
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=3, price_at_order=Decimal("90.00"))

    discounted_total = Decimal("80.00") * 2 + Decimal("90.00") * 3
    assert order.total_price == discounted_total

    original_total = product_variant.price * 5
    expected_discount = original_total - discounted_total
    assert order.total_discount == expected_discount


def test_order_total_discount_cannot_be_negative(order, product_variant):
    high_price = product_variant.price + Decimal("50.00")
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=1, price_at_order=high_price)
    assert order.total_discount == 0  # discount cannot be negative


def test_order_cancel_restock_once(order, product_variant):
    initial_stock = product_variant.stock_quantity
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=2, price_at_order=product_variant.price)

    product_variant.stock_quantity -= 2
    product_variant.save()

    order.cancel_order(by_customer=True)
    order.refresh_from_db()
    assert order.status == "CANCELLED"
    assert order.cancelled_by_customer is True
    assert order.was_restocked is True  # ✅ Ensure restocked flag is set

    product_variant.refresh_from_db()
    assert product_variant.stock_quantity == initial_stock

    # Cancel again → should NOT double-restock
    order.cancel_order()
    product_variant.refresh_from_db()
    assert product_variant.stock_quantity == initial_stock


def test_cancel_already_cancelled_order_does_nothing(order, product_variant):
    initial_stock = product_variant.stock_quantity
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=1, price_at_order=product_variant.price)

    product_variant.stock_quantity -= 1
    product_variant.save()

    order.cancel_order()
    order.cancel_order()
    product_variant.refresh_from_db()
    assert product_variant.stock_quantity == initial_stock
    assert order.status == "CANCELLED"


def test_order_decimal_precision(order, product_variant):
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=1, price_at_order=Decimal("99.9999"))
    assert order.total_price == Decimal("100.00")


def test_deduct_variant_stock_integrity(order, product_variant):
    initial_stock = product_variant.stock_quantity
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=5, price_at_order=product_variant.price)

    from nail_ecommerce_project.apps.orders.utils import deduct_variant_stock
    deduct_variant_stock(order)

    product_variant.refresh_from_db()
    assert product_variant.stock_quantity == initial_stock - 5
    assert product_variant.stock_quantity >= 0


def test_deduct_variant_stock_raises_error_on_insufficient_stock(order, product_variant):
    product_variant.stock_quantity = 3
    product_variant.save()

    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=5, price_at_order=product_variant.price)

    from nail_ecommerce_project.apps.orders.utils import deduct_variant_stock
    with pytest.raises(ValueError, match="Cannot deduct stock"):
        deduct_variant_stock(order)


# ✅ NEW TEST CASES BELOW

def test_was_restocked_flag_behavior(order, product_variant):
    """Initially False, should become True after cancel_order"""
    assert order.was_restocked is False
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=1, price_at_order=product_variant.price)

    # Deduct then cancel
    product_variant.stock_quantity -= 1
    product_variant.save()
    order.cancel_order()
    order.refresh_from_db()
    assert order.was_restocked is True


def test_cancel_order_by_admin(order, product_variant):
    """Cancel by admin should NOT mark cancelled_by_customer"""
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=1, price_at_order=product_variant.price)
    product_variant.stock_quantity -= 1
    product_variant.save()

    order.cancel_order(by_customer=False)
    order.refresh_from_db()
    assert order.cancelled_by_customer is False
    assert order.status == "CANCELLED"


def test_multiple_order_items_sum_correctly(order, product_variant):
    """Verify total_price & discount with mixed prices"""
    pv = product_variant
    pv2 = product_variant
    OrderItem.objects.create(order=order, product_variant=pv, quantity=1, price_at_order=Decimal("90.00"))
    OrderItem.objects.create(order=order, product_variant=pv2, quantity=2, price_at_order=Decimal("85.00"))

    total_expected = Decimal("90.00") + (2 * Decimal("85.00"))
    assert order.total_price == total_expected
    assert order.total_discount >= 0  # no negative discount
