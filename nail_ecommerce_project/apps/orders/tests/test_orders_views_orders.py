import pytest
from django.urls import reverse
from django.contrib.messages import get_messages

pytestmark = pytest.mark.django_db

# --------------------------
# CustomerOrderListView Tests
# --------------------------

def test_order_list_shows_only_user_orders(client, test_user_with_address, order_with_status):
    """Should return only logged-in user's orders."""
    # Create 2 orders for logged-in user
    order1 = order_with_status("PENDING")
    order2 = order_with_status("PROCESSING")
    # Create another user's order
    from django.contrib.auth import get_user_model
    User = get_user_model()
    other_user = User.objects.create_user(username="other", password="pass", email="other@test.com")
    Order = order1.__class__
    Order.objects.create(user=other_user, full_name="Other User")

    client.force_login(test_user_with_address)
    response = client.get(reverse("orders:order_list"))
    assert response.status_code == 200

    # Should only show logged-in user's orders
    orders = response.context["orders"]
    assert order1 in orders
    assert order2 in orders
    # No orders from other user
    assert all(o.user == test_user_with_address for o in orders)

def test_order_list_search_by_order_id(client, test_user_with_address, order_with_status):
    """Should filter by exact order ID."""
    order = order_with_status("PENDING")

    client.force_login(test_user_with_address)
    url = reverse("orders:order_list") + f"?search={order.id}"
    response = client.get(url)

    assert response.status_code == 200
    orders = response.context["orders"]
    assert list(orders) == [order]  # Only matched order

def test_order_list_search_by_product_name(client, test_user_with_address, product_variant, order_with_status):
    """Should filter by product name partial match."""
    order = order_with_status("PENDING")
    # Link order to a product
    from nail_ecommerce_project.apps.orders.models import OrderItem
    OrderItem.objects.create(order=order, product_variant=product_variant, quantity=1, price_at_order=product_variant.price)

    client.force_login(test_user_with_address)
    url = reverse("orders:order_list") + "?search=Test%20Product"
    response = client.get(url)

    assert response.status_code == 200
    orders = response.context["orders"]
    assert order in orders

def test_order_list_invalid_product_search(client, test_user_with_address, order_with_status):
    """Should show invalid_order_search=True when no product match."""
    order_with_status("PENDING")  # Just to have an order
    client.force_login(test_user_with_address)
    url = reverse("orders:order_list") + "?search=NonExistentProduct"
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["invalid_order_search"] is True

def test_order_list_no_orders_found(client, test_user_with_address):
    """Should show no_orders_found=True when user has no orders."""
    client.force_login(test_user_with_address)
    response = client.get(reverse("orders:order_list"))
    assert response.status_code == 200
    assert response.context["no_orders_found"] is True

def test_order_list_status_filter(client, test_user_with_address, order_with_status):
    """Should filter by status."""
    pending_order = order_with_status("PENDING")
    shipped_order = order_with_status("SHIPPED")

    client.force_login(test_user_with_address)
    url = reverse("orders:order_list") + "?status=SHIPPED"
    response = client.get(url)
    assert response.status_code == 200
    orders = response.context["orders"]
    assert shipped_order in orders
    assert pending_order not in orders

def test_order_list_pagination(client, test_user_with_address, order_with_status):
    """Should paginate if >10 orders."""
    for _ in range(12):
        order_with_status("PENDING")

    client.force_login(test_user_with_address)
    response_page1 = client.get(reverse("orders:order_list"))
    assert response_page1.context["page_obj"].number == 1
    assert len(response_page1.context["orders"]) == 10  # First page has 10

    # Page 2
    response_page2 = client.get(reverse("orders:order_list") + "?page=2")
    assert response_page2.context["page_obj"].number == 2
    assert len(response_page2.context["orders"]) == 2  # Remaining orders


# --------------------------
# UserCancelOrderView Tests
# --------------------------

def _post_cancel(client, order, user):
    """Helper to call cancel view."""
    client.force_login(user)
    return client.post(reverse("orders:user_cancel_order", args=[order.id]))

def _get_message_texts(response):
    return [m.message for m in get_messages(response.wsgi_request)]

@pytest.mark.parametrize("status", ["PENDING", "PROCESSING"])
def test_cancel_order_success(client, test_user_with_address, order_with_status, status):
    """Should cancel when status is PENDING/PROCESSING."""
    order = order_with_status(status)
    response = _post_cancel(client, order, test_user_with_address)
    order.refresh_from_db()
    messages = _get_message_texts(response)

    assert order.status == "CANCELLED"
    assert any("successfully cancelled" in m for m in messages)


from django.contrib.messages import get_messages


def test_cancel_order_already_cancelled(client, test_user_with_address, order_with_status):
    """If already CANCELLED, show info message."""
    order = order_with_status("CANCELLED")

    # ✅ Ensure user is authenticated
    client.force_login(test_user_with_address)

    response = client.post(
        reverse("orders:user_cancel_order", args=[order.id]),
        follow=True
    )

    storage = list(get_messages(response.wsgi_request))
    messages = [m.message for m in storage]

    # ✅ Debug prints
    print("\n=== DEBUG: Cancel Already Cancelled ===")
    print("Response status code:", response.status_code)
    print("Redirect chain:", response.redirect_chain)
    print("Messages retrieved:", messages)

    assert any("cannot be cancelled because it is currently in 'CANCELLED' stage" in m for m in messages)


@pytest.mark.parametrize("status", ["SHIPPED", "DELIVERED"])
def test_cancel_order_invalid_status(client, test_user_with_address, order_with_status, status):
    """Should NOT cancel SHIPPED/DELIVERED -> error message."""
    order = order_with_status(status)
    response = _post_cancel(client, order, test_user_with_address)
    order.refresh_from_db()
    messages = _get_message_texts(response)

    assert order.status == status  # unchanged
    assert any("cannot be cancelled" in m for m in messages)

def test_cancel_order_not_owner(client, test_user_with_address, order_with_status, django_user_model):
    """Should 404 if order not belonging to user."""
    # Create other user and their order
    other_user = django_user_model.objects.create_user(username="otheruser", password="pass", email="o@o.com")
    other_order = order_with_status("PENDING")
    other_order.user = other_user
    other_order.save()

    client.force_login(test_user_with_address)
    response = client.post(reverse("orders:user_cancel_order", args=[other_order.id]))
    assert response.status_code == 404

def test_cancel_order_unauthenticated_redirects(client, order_with_status):
    """Unauthenticated user should be redirected to login."""
    order = order_with_status("PENDING")
    response = client.post(reverse("orders:user_cancel_order", args=[order.id]))
    assert response.status_code == 302  # redirect to login
    assert "/login" in response.url
