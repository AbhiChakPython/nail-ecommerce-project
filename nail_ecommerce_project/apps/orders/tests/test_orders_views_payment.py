import pytest
from django.urls import reverse
from nail_ecommerce_project.apps.orders.models import Order, OrderItem


# ========================
# ✅ CART CALLBACK VIEW
# ========================

def test_cart_callback_success(
    client, test_user_with_address, product_variant, pre_payment_cart_session,
    mock_verify_signature_success, mock_send_order_email
):
    client.force_login(test_user_with_address)

    resp = client.post(reverse("orders:cart_callback"), data={
        "razorpay_payment_id": "pid123",
        "razorpay_signature": "sig123",
        "razorpay_order_id": "test_razorpay_order_id"
    })

    # ✅ Redirects to order_success
    order = Order.objects.last()
    assert resp.status_code == 302
    assert reverse("orders:order_success", kwargs={"order_id": order.id}) in resp.url

    # ✅ Order created
    assert order.user == test_user_with_address
    assert OrderItem.objects.filter(order=order).count() == 1
    assert "pre_payment_cart" not in client.session  # ✅ cleared session


def test_cart_callback_signature_fail(
    client, test_user_with_address, pre_payment_cart_session,
    mock_verify_signature_failure
):
    client.force_login(test_user_with_address)

    resp = client.post(reverse("orders:cart_callback"), data={
        "razorpay_payment_id": "pid123",
        "razorpay_signature": "bad_sig",
        "razorpay_order_id": "test_razorpay_order_id"
    })

    assert resp.status_code == 302
    assert reverse("orders:order_failed") in resp.url


def test_cart_callback_missing_session(
    client, test_user_with_address, mock_verify_signature_success
):
    client.force_login(test_user_with_address)

    resp = client.post(reverse("orders:cart_callback"), data={
        "razorpay_payment_id": "pid123",
        "razorpay_signature": "sig123",
        "razorpay_order_id": "test_razorpay_order_id"
    })
    # ✅ No pre_payment_cart -> fail
    assert resp.status_code == 302
    assert reverse("orders:order_failed") in resp.url


# ========================
# ✅ BUY NOW CALLBACK VIEW
# ========================

def test_buy_now_callback_success(client, test_user_with_address, pre_payment_buy_now_callback_session, mock_verify_signature_success):
    client.force_login(test_user_with_address)

    resp = client.post(reverse("orders:buy_now_callback"), data={
        "razorpay_payment_id": "pidBN",
        "razorpay_signature": "sigBN",
        "razorpay_order_id": "test_razorpay_order_id"
    })

    order = Order.objects.last()
    assert order is not None
    assert order.status == "CONFIRMED"
    assert order.razorpay_payment_id == "pidBN"
    assert resp.status_code == 302
    assert reverse("orders:order_success", kwargs={"order_id": order.id}) in resp.url


def test_buy_now_callback_missing_session(
    client, test_user_with_address, mock_verify_signature_success
):
    client.force_login(test_user_with_address)

    resp = client.post(reverse("orders:buy_now_callback"), data={
        "razorpay_payment_id": "pidBN",
        "razorpay_signature": "sigBN",
        "razorpay_order_id": "test_razorpay_order_id"
    })
    assert resp.status_code == 302
    assert reverse("orders:order_failed") in resp.url


def test_buy_now_callback_signature_fail(
    client, test_user_with_address, pre_payment_buy_now_callback_session,
    mock_verify_signature_failure
):
    client.force_login(test_user_with_address)
    resp = client.post(reverse("orders:buy_now_callback"), data={
        "razorpay_payment_id": "pidBN",
        "razorpay_signature": "wrong",
        "razorpay_order_id": "test_razorpay_order_id"
    })
    assert resp.status_code == 302
    assert reverse("orders:order_failed") in resp.url


# ========================
# ✅ ORDER SUCCESS + FAILED VIEWS
# ========================

def test_order_success_valid_user(client, test_user_with_address, order_with_razorpay):
    client.force_login(test_user_with_address)
    resp = client.get(reverse("orders:order_success", kwargs={"order_id": order_with_razorpay.id}))
    assert resp.status_code == 200
    assert str(order_with_razorpay.id) in resp.content.decode()


def test_order_success_wrong_user(client, django_user_model, order_with_razorpay):
    # Different user should be redirected to failed
    other = django_user_model.objects.create_user(username="wrong", password="1234", email="wrong@example.com")
    client.force_login(other)
    resp = client.get(reverse("orders:order_success", kwargs={"order_id": order_with_razorpay.id}))
    assert resp.status_code == 302
    assert reverse("orders:order_failed") in resp.url


def test_order_success_not_found(client, test_user_with_address):
    client.force_login(test_user_with_address)
    resp = client.get(reverse("orders:order_success", kwargs={"order_id": 99999}))
    assert resp.status_code == 302
    assert reverse("orders:order_failed") in resp.url


def test_order_failed_view(client, test_user_with_address):
    client.force_login(test_user_with_address)
    resp = client.get(reverse("orders:order_failed"))
    assert resp.status_code == 200
    assert "Order" in resp.content.decode() or resp.content.decode() != ""


# ========================
# ✅ CART PAYMENT VERIFY VIEW
# ========================

def test_cart_payment_verify_success(
    client, test_user_with_address, product_variant,
    pre_payment_cart_session, mock_verify_signature_success,
    mock_send_order_email, mock_deduct_stock
):
    client.force_login(test_user_with_address)

    resp = client.post(reverse("orders:verify_cart_payment"), data={
        "razorpay_order_id": "test_razorpay_order_id",
        "razorpay_payment_id": "pid123",
        "razorpay_signature": "sig123",
        "full_name": "John",
        "phone": "1234567890",
        "address_line1": "Addr",
        "address_line2": "Addr2",
        "city": "City",
        "postal_code": "123456",
        "state": "State"
    })

    assert resp.status_code == 200  # ✅ success page
    order = Order.objects.last()
    assert order.user == test_user_with_address
    assert OrderItem.objects.filter(order=order).count() == 1


def test_cart_payment_verify_form_invalid(
    client, test_user_with_address, product_variant,
    pre_payment_cart_session, mock_verify_signature_success
):
    client.force_login(test_user_with_address)
    # Missing phone/state etc.
    resp = client.post(reverse("orders:verify_cart_payment"), data={
        "razorpay_order_id": "test_razorpay_order_id",
        "razorpay_payment_id": "pid123",
        "razorpay_signature": "sig123",
        "full_name": "",
        "phone": "",
    })
    # Should redirect back to checkout_cart
    assert resp.status_code == 302
    assert reverse("orders:checkout_cart") in resp.url


def test_cart_payment_verify_signature_fail(
    client, test_user_with_address, pre_payment_cart_session,
    mock_verify_signature_failure
):
    client.force_login(test_user_with_address)
    resp = client.post(reverse("orders:verify_cart_payment"), data={
        "razorpay_order_id": "test_razorpay_order_id",
        "razorpay_payment_id": "pid123",
        "razorpay_signature": "wrong",
        "full_name": "J",
        "phone": "1",
        "address_line1": "A",
        "address_line2": "B",
        "city": "C",
        "postal_code": "123456",
        "state": "S"
    })
    assert resp.status_code == 302
    assert reverse("orders:order_failed") in resp.url


def test_cart_payment_verify_stock_fail(
    client, test_user_with_address, product_variant,
    pre_payment_cart_session, mock_verify_signature_success
):
    client.force_login(test_user_with_address)
    # Make stock insufficient
    product_variant.stock_quantity = 0
    product_variant.save()

    resp = client.post(reverse("orders:verify_cart_payment"), data={
        "razorpay_order_id": "test_razorpay_order_id",
        "razorpay_payment_id": "pid123",
        "razorpay_signature": "sig123",
        "full_name": "John",
        "phone": "123",
        "address_line1": "Addr",
        "address_line2": "Addr2",
        "city": "City",
        "postal_code": "123456",
        "state": "State"
    })
    # Should fail gracefully
    assert resp.status_code == 302
    assert reverse("orders:order_failed") in resp.url


# ========================
# ✅ BUY NOW PAYMENT VERIFY VIEW
# ========================

def test_buy_now_payment_verify_success(
    client, test_user_with_address, product_variant,
    buy_now_cart_session, mock_verify_signature_success,
    mock_send_order_email, mock_deduct_stock
):
    client.force_login(test_user_with_address)
    resp = client.post(reverse("orders:verify_buy_now_payment"), data={
        "razorpay_order_id": "test_razorpay_order_id",
        "razorpay_payment_id": "pidBN",
        "razorpay_signature": "sigBN",
        "full_name": "John",
        "phone": "1234567890",
        "address_line1": "Addr",
        "address_line2": "Addr2",
        "city": "City",
        "postal_code": "123456",
        "state": "State"
    })
    assert resp.status_code == 200
    order = Order.objects.last()
    assert order.user == test_user_with_address
    assert OrderItem.objects.filter(order=order).count() == 1


def test_buy_now_payment_verify_form_invalid(
    client, test_user_with_address, buy_now_cart_session,   # ✅ FIXED FIXTURE
    mock_verify_signature_success
):
    client.force_login(test_user_with_address)
    # Sending invalid form (missing required fields)
    resp = client.post(reverse("orders:verify_buy_now_payment"), data={
        "razorpay_order_id": "test_razorpay_order_id",
        "razorpay_payment_id": "pidBN",
        "razorpay_signature": "sigBN",
        "full_name": "",  # ❌ invalid
        "phone": "",      # ❌ invalid
        "address_line1": "",
        "address_line2": "",
        "city": "",
        "postal_code": "",
        "state": ""
    })
    # Should redirect back to checkout_buy_now due to invalid form
    assert resp.status_code == 302
    assert reverse("orders:checkout_buy_now") in resp.url


def test_buy_now_payment_verify_signature_fail(
    client, test_user_with_address, buy_now_cart_session,
    mock_verify_signature_failure
):
    client.force_login(test_user_with_address)
    resp = client.post(reverse("orders:verify_buy_now_payment"), data={
        "razorpay_order_id": "test_razorpay_order_id",
        "razorpay_payment_id": "pidBN",
        "razorpay_signature": "wrong",
        "full_name": "J",
        "phone": "1",
        "address_line1": "A",
        "address_line2": "B",
        "city": "C",
        "postal_code": "123456",
        "state": "S"
    })
    assert resp.status_code == 302
    assert reverse("orders:order_failed") in resp.url
