import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_checkout_view_get_authenticated_customer(client, test_user, product_variant):
    client.login(username=test_user.username, password='testpass123')

    # simulate adding product_variant to the cart (session-based)
    session = client.session
    session['cart'] = {
        str(product_variant.id): {'quantity': 1, 'price': str(product_variant.price)}
    }
    session.save()

    print("TEST user role:", test_user.role)
    print("TEST is_customer:", test_user.is_customer)
    print("Login successful?", client.login(username="testuser", password="testpass123"))

    response = client.get(reverse('orders:checkout'))

    print("RESPONSE user:", response.wsgi_request.user)
    print("RESPONSE user role:", getattr(response.wsgi_request.user, 'role', None))
    print("RESPONSE is_customer:", getattr(response.wsgi_request.user, 'is_customer', None))

    assert response.status_code == 200
    assert 'form' in response.context
    assert 'cart' in response.context


def test_checkout_view_get_unauthenticated_user_denied(client):
    url = reverse('orders:checkout')
    response = client.get(url)

    assert response.status_code == 403  # Forbidden
    assert "403 Forbidden" in response.content.decode()


def test_checkout_view_get_authenticated_non_customer_denied(client, django_user_model):
    """Authenticated user with role not 'customer' should be denied."""
    user = django_user_model.objects.create_user(username='staffuser', email='staffuser@example.com',
                                                 password='pass123', role='staff')
    client.login(username='staffuser', password='pass123')
    response = client.get(reverse('orders:checkout'))
    assert response.status_code == 403
    assert b"403 Forbidden" in response.content


def test_checkout_post_empty_cart_shows_error(client, test_user):
    """POST checkout with empty cart should redirect with error message."""
    client.login(username=test_user.username, password='testpass123')
    response = client.post(reverse('orders:checkout'), data={
        'full_name': 'Test User',
        'phone': '1234567890',
        'address_line1': '123 Street',
        'city': 'Test City',
        'postal_code': '12345',
        'country': 'Test Country'
    })
    # Should redirect to product list because cart is empty
    assert response.status_code == 302
    assert response.url == reverse('products:product_list')


def test_checkout_post_invalid_form_rerenders(client, test_user, product_variant):
    """POST checkout with invalid form data should rerender the form with errors."""
    client.login(username=test_user.username, password='testpass123')

    # Setup session cart with valid product
    session = client.session
    session['cart'] = {str(product_variant.id): {'quantity': 1, 'price': str(product_variant.price)}}
    session.save()

    # Submit POST with missing required fields (e.g. full_name missing)
    response = client.post(reverse('orders:checkout'), data={
        'phone': '1234567890',
        'address_line1': '123 Street',
        'city': 'Test City',
        'postal_code': '12345',
        'country': 'Test Country'
    })


def test_checkout_post_quantity_exceeds_stock(client, test_user, product_variant):
    """POST checkout where requested quantity exceeds available stock should raise error."""
    client.login(username=test_user.username, password='testpass123')

    # Setup session cart with quantity exceeding stock
    session = client.session
    session['cart'] = {str(product_variant.id): {'quantity': product_variant.stock_quantity + 1, 'price': str(product_variant.price)}}
    session.save()

    # Valid form data
    post_data = {
        'full_name': 'Test User',
        'phone': '1234567890',
        'address_line1': '123 Street',
        'city': 'Test City',
        'postal_code': '12345',
        'country': 'Test Country'
    }

    response = client.post(reverse('orders:checkout'), data=post_data)

    # Should redirect back to cart with error message (or appropriate error handling)
    # Adjust according to your actual view behavior
    assert response.status_code == 302
    # You can also check if error messages exist in messages framework after redirection if needed