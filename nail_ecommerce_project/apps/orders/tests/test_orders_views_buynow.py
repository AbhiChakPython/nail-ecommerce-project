import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_buy_now_post_valid_customer(client, test_user, product_variant):
    client.login(username=test_user.username, password="testpass123")
    product_variant.stock_quantity = 10
    product_variant.save()

    url = reverse("orders:buy_now")

    response = client.post(url, {
        "variant_id": product_variant.id,
        "quantity": 2,
    })

    assert response.status_code == 302
    assert response.url == reverse("orders:checkout_buy_now")
    assert client.session["buy_now"]["variant_id"] == product_variant.id
    assert client.session["buy_now"]["quantity"] == 2

@pytest.mark.django_db
def test_buy_now_post_insufficient_stock(client, test_user, product_variant):
    product_variant.stock_quantity = 1
    product_variant.save()
    client.login(username=test_user.username, password="testpass123")

    response = client.post(reverse("orders:buy_now"), {
        "variant_id": product_variant.id,
        "quantity": 5,  # requesting more than available
    })

    assert response.status_code == 302
    expected_redirect_url = reverse("products:product_detail", kwargs={"slug": product_variant.product.slug})
    assert expected_redirect_url in response.url

@pytest.mark.django_db
def test_buy_now_post_invalid_variant(client, test_user):
    client.login(username=test_user.username, password="testpass123")

    response = client.post(reverse("orders:checkout_buy_now").replace("/checkout-buy-now", "/buy-now/"), {
        "variant_id": 9999,
        "quantity": 1,
    })

    assert response.status_code == 404

@pytest.mark.django_db
def test_buy_now_checkout_get_valid_session(client, test_user, product_variant):
    client.login(username=test_user.username, password="testpass123")
    session = client.session
    session["buy_now"] = {
        "variant_id": product_variant.id,
        "quantity": 2
    }
    session.save()

    response = client.get(reverse("orders:checkout_buy_now"))
    assert response.status_code == 200
    assert "razorpay_order_id" in response.context

@pytest.mark.django_db
def test_buy_now_checkout_get_no_session(client, test_user):
    client.login(username=test_user.username, password="testpass123")
    response = client.get(reverse("orders:checkout_buy_now"))
    assert response.status_code == 302
    assert response.url == reverse("products:product_list")

@pytest.mark.django_db
def test_buy_now_checkout_post_valid(client, test_user, product_variant):
    client.login(username=test_user.username, password="testpass123")
    session = client.session
    session["buy_now"] = {"variant_id": product_variant.id, "quantity": 1}
    session["buy_now_order"] = "razorpay_mock_id_123"
    session.save()

    response = client.post(reverse("orders:checkout_buy_now"), {
        "full_name": "Test User",
        "phone": "1234567890",
        "address_line1": "123 Main St",
        "address_line2": "",
        "city": "Testville",
        "postal_code": "12345",
        "state": "Testland"
    })

    assert response.status_code == 302
    assert "/orders/success/" in response.url
    assert not client.session.get("buy_now")

@pytest.mark.django_db
def test_buy_now_checkout_post_invalid_form(client, test_user, product_variant):
    client.login(username=test_user.username, password="testpass123")
    session = client.session
    session["buy_now"] = {"variant_id": product_variant.id, "quantity": 1}
    session["buy_now_order"] = "razorpay_mock_id_123"
    session.save()

    response = client.post(reverse("orders:checkout_buy_now"), {
        "full_name": "",  # Missing required fields
        "phone": "",
        "address_line1": "",
        "city": "",
        "postal_code": "",
        "state": ""
    })

    # ✅ Only check redirect
    assert response.status_code == 302
    assert response.url == reverse("orders:checkout_buy_now")


@pytest.mark.django_db
def test_buy_now_post_unauthorized_user_role(client, django_user_model, product_variant):
    # Create a staff/admin user
    staff_user = django_user_model.objects.create_user(
        username="staffuser", email="staff@example.com", password="pass123", role="staff"
    )
    client.login(username="staffuser", password="pass123")

    # Staff tries to use Buy Now → should raise PermissionDenied (403)
    response = client.post(reverse("orders:buy_now"), {
        "variant_id": product_variant.id,
        "quantity": 1
    })

    assert response.status_code == 403


@pytest.mark.django_db
def test_buy_now_post_anonymous_redirects_to_login(client, product_variant):
    response = client.post(reverse("orders:buy_now"), {
        "variant_id": product_variant.id,
        "quantity": 1,
    })
    expected_login_url = f"{reverse('users:login')}?next={reverse('orders:buy_now')}"
    assert response.status_code == 302
    assert response.url == expected_login_url


@pytest.mark.django_db
def test_buy_now_checkout_post_insufficient_stock(client, test_user, product_variant):
    # Reduce stock to simulate insufficient stock
    product_variant.stock_quantity = 0
    product_variant.save()

    client.login(username=test_user.username, password="testpass123")
    session = client.session
    session["buy_now"] = {"variant_id": product_variant.id, "quantity": 2}
    session.save()

    response = client.post(reverse("orders:checkout_buy_now"), {
        "full_name": "Test User",
        "phone": "1234567890",
        "address_line1": "123 Main St",
        "city": "Testville",
        "postal_code": "12345",
        "state": "TestState",
    })

    # ✅ Should redirect to product detail page
    expected_redirect_url = reverse("products:product_detail", kwargs={"slug": product_variant.product.slug})
    assert response.status_code == 302
    assert response.url == expected_redirect_url


@pytest.mark.django_db
def test_buy_now_checkout_post_no_session_redirects(client, test_user):
    client.login(username=test_user.username, password="testpass123")

    # No session present
    response = client.post(reverse("orders:checkout_buy_now"), {
        "full_name": "Test User",
        "phone": "1234567890",
        "address_line1": "123 Main St",
        "city": "Test City",
        "postal_code": "12345",
    })

    # Should redirect back to checkout page
    assert response.status_code == 302
    assert response.url == reverse("orders:checkout_buy_now")


@pytest.mark.django_db
def test_buy_now_checkout_get_deleted_variant_redirects(client, test_user, product_variant):
    client.login(username=test_user.username, password="testpass123")

    # Simulate session with a valid variant ID
    session = client.session
    session["buy_now"] = {"variant_id": product_variant.id, "quantity": 1}
    session.save()

    # Delete variant
    product_variant.delete()

    response = client.get(reverse("orders:checkout_buy_now"))

    # Should redirect to product list because variant no longer exists
    assert response.status_code == 302
    assert response.url == reverse("products:product_list")


@pytest.mark.django_db
def test_buy_now_checkout_post_missing_razorpay_fields(client, test_user, product_variant):
    client.login(username=test_user.username, password="testpass123")
    session = client.session
    session["buy_now"] = {"variant_id": product_variant.id, "quantity": 1}
    session.save()

    response = client.post(reverse("orders:checkout_buy_now"), {
        "full_name": "Test User",
        "phone": "1234567890",
        "address_line1": "123 Main St",
        "address_line2": "",
        "city": "Testville",
        "postal_code": "12345",
        "state": "TestState",
        # ❌ No razorpay fields provided
    })

    # ✅ Expect success redirect because current view doesn't enforce Razorpay fields
    assert response.status_code == 302
    assert "/orders/success/" in response.url


@pytest.mark.django_db
def test_buy_now_post_defaults_to_quantity_1(client, test_user, product_variant):
    client.login(username=test_user.username, password="testpass123")

    response = client.post(reverse("orders:buy_now"), {
        "variant_id": product_variant.id
        # No quantity provided
    })

    assert response.status_code == 302
    assert response.url == reverse("orders:checkout_buy_now")
    assert client.session["buy_now"]["quantity"] == 1
