import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from nail_ecommerce_project.apps.products.models import Product, ProductVariant
from nail_ecommerce_project.apps.orders.cart import Cart

User = get_user_model()


@pytest.mark.django_db
def test_add_to_cart_success(client, django_user_model):
    # Create customer user and login
    user = django_user_model.objects.create_user(
        username='custuser', email='cust@example.com', password='pass123', role='customer'
    )
    client.login(username='custuser', password='pass123')

    # Create product and variant
    product = Product.objects.create(name='Test Product', description='Test product')
    variant = ProductVariant.objects.create(
        product=product, size='S', color='Red', price='99.99', stock_quantity=10
    )

    # POST to add to cart
    response = client.post(
        reverse('orders:add_to_cart'),
        data={'variant_id': variant.id, 'quantity': 2}
    )

    # Check session cart
    session = client.session
    cart_data = session.get(Cart.SESSION_KEY)
    assert str(variant.id) in cart_data
    assert cart_data[str(variant.id)]['quantity'] == 2

    # Check redirect
    assert response.status_code == 302
    assert reverse('products:product_detail', kwargs={'slug': product.slug}) in response.url


@pytest.mark.django_db
def test_add_to_cart_invalid_variant(client, django_user_model):
    # Setup test user (customer) and login
    user = django_user_model.objects.create_user(
        username='custuser2', email='cust2@example.com', password='pass123', role='customer'
    )
    client.login(username='custuser2', password='pass123')

    # Use an invalid variant ID
    invalid_variant_id = 9999

    # Send POST to AddToCartView
    response = client.post(
        reverse('orders:add_to_cart'),
        data={'variant_id': invalid_variant_id, 'quantity': 1}
    )

    # Verify it redirected (to product list most likely)
    assert response.status_code == 404
    assert "Not Found" in response.content.decode()

    # Ensure cart remains empty
    session = client.session
    cart = session.get(Cart.SESSION_KEY, {})
    assert cart == {}


@pytest.mark.django_db
def test_remove_from_cart_valid_variant(client, django_user_model):
    # Create and login test customer user
    user = django_user_model.objects.create_user(
        username='custuser3', email='cust3@example.com', password='pass123', role='customer'
    )
    client.login(username='custuser3', password='pass123')

    # Create a product and variant
    product = Product.objects.create(name='Product 3', description='Desc 3')
    variant = ProductVariant.objects.create(
        product=product, size='L', color='Blue', price='50.00', stock_quantity=10
    )

    # Add to cart using the view
    client.post(reverse('orders:add_to_cart'), data={'variant_id': variant.id, 'quantity': 1})

    # Now remove it using the view
    response = client.post(
        reverse('orders:remove_from_cart', kwargs={'variant_id': variant.id})
    )

    # Validate that it's removed from session cart
    session = client.session
    cart_data = session.get(Cart.SESSION_KEY)
    assert str(variant.id) not in cart_data

    # Confirm redirection
    assert response.status_code == 302
    assert reverse('orders:cart_detail') in response.url


@pytest.mark.django_db
def test_remove_from_cart_invalid_variant(client, django_user_model):
    # Create and login test customer
    user = django_user_model.objects.create_user(
        username='custuser4', email='cust4@example.com', password='pass123', role='customer'
    )
    client.login(username='custuser4', password='pass123')

    # Use a non-existent variant ID
    invalid_variant_id = 9999

    # Send POST to RemoveFromCartView with invalid ID
    response = client.post(
        reverse('orders:remove_from_cart', kwargs={'variant_id': invalid_variant_id})
    )

    # Should return 404 Not Found
    assert response.status_code == 404


@pytest.mark.django_db
def test_cart_detail_view_displays_cart_items(client, django_user_model):
    # Create and login test customer
    user = django_user_model.objects.create_user(
        username='custuser5', email='cust5@example.com', password='pass123', role='customer'
    )
    client.login(username='custuser5', password='pass123')

    # Create product + variant
    product = Product.objects.create(name='Product 5', description='Desc')
    variant = ProductVariant.objects.create(
        product=product, size='XL', color='Green', price='99.00', stock_quantity=20
    )

    # Add item to cart using view
    client.post(reverse('orders:add_to_cart'), data={'variant_id': variant.id, 'quantity': 2})

    # Now access cart detail view
    response = client.get(reverse('orders:cart_detail'))

    # Validate page loads
    assert response.status_code == 200

    # Check that the variant is shown in the rendered content
    assert variant.product.name in response.content.decode()
    assert str(variant.price) in response.content.decode()


# -------------------------
# NEW EDGE & NEGATIVE TESTS
# -------------------------

@pytest.mark.django_db
def test_add_to_cart_exceeds_stock(client, django_user_model):
    """Requesting more than available stock should show error and redirect."""
    user = django_user_model.objects.create_user(
        username='custuser6', email='cust6@example.com', password='pass123', role='customer'
    )
    client.login(username='custuser6', password='pass123')

    product = Product.objects.create(name='Stock Product', description='Limited stock')
    variant = ProductVariant.objects.create(
        product=product, size='M', color='Black', price='75.00', stock_quantity=3
    )

    response = client.post(
        reverse('orders:add_to_cart'),
        data={'variant_id': variant.id, 'quantity': 5}  # exceeds stock
    )

    # Should redirect to product detail page with error message
    assert response.status_code == 302
    assert reverse('products:product_detail', kwargs={'slug': product.slug}) in response.url

    # Cart must remain empty because request was invalid
    session_cart = client.session.get(Cart.SESSION_KEY, {})
    assert session_cart == {}


@pytest.mark.django_db
def test_cart_detail_unauthorized_user(client, django_user_model):
    """Non-customer user should get PermissionDenied when accessing cart."""
    staff_user = django_user_model.objects.create_user(
        username='staffuser', email='staff@example.com', password='pass123', role='staff'
    )
    client.login(username='staffuser', password='pass123')

    response = client.get(reverse('orders:cart_detail'))

    # PermissionDenied should result in 403 Forbidden
    assert response.status_code == 403


@pytest.mark.django_db
def test_remove_from_cart_unauthorized_user(client, django_user_model):
    """Non-customer user should NOT be allowed to remove items from cart."""
    staff_user = django_user_model.objects.create_user(
        username='staffuser2', email='staff2@example.com', password='pass123', role='staff'
    )
    client.login(username='staffuser2', password='pass123')

    product = Product.objects.create(name='Prod Remove', description='Test')
    variant = ProductVariant.objects.create(
        product=product, size='S', color='White', price='45.00', stock_quantity=5
    )

    # Attempt to remove variant from cart → should raise PermissionDenied
    response = client.post(reverse('orders:remove_from_cart', kwargs={'variant_id': variant.id}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_cart_detail_anonymous_redirects_to_login(client):
    """Anonymous user should be redirected to login when accessing cart."""
    response = client.get(reverse('orders:cart_detail'))
    assert response.status_code == 302
    assert '/login' in response.url.lower()


@pytest.mark.django_db
def test_cart_checkout_with_empty_cart(client, django_user_model):
    """CartCheckoutView with empty cart should redirect back to cart detail."""
    user = django_user_model.objects.create_user(
        username='custuser7', email='cust7@example.com', password='pass123', role='customer'
    )
    client.login(username='custuser7', password='pass123')

    response = client.get(reverse('orders:checkout_cart'))
    # Since total will be 0 < 1, should redirect to cart detail
    assert response.status_code == 302
    assert reverse('orders:cart_detail') in response.url


@pytest.mark.django_db
def test_cart_checkout_exceeds_stock(client, django_user_model):
    """Checkout with an item exceeding stock should show error and redirect back."""
    user = django_user_model.objects.create_user(
        username='custuser8', email='cust8@example.com', password='pass123', role='customer'
    )
    client.login(username='custuser8', password='pass123')

    product = Product.objects.create(name='Low Stock', description='Testing checkout stock')
    variant = ProductVariant.objects.create(
        product=product, size='L', color='Yellow', price='120.00', stock_quantity=1
    )

    # Manually add more than available stock to cart session
    session = client.session
    session[Cart.SESSION_KEY] = {
        str(variant.id): {'quantity': 5, 'price': str(variant.price)}
    }
    session.save()

    response = client.get(reverse('orders:checkout_cart'))

    # Should redirect to cart detail with error message
    assert response.status_code == 302
    assert reverse('orders:cart_detail') in response.url


@pytest.mark.django_db
def test_cart_checkout_minimum_amount_fail(client, django_user_model):
    """Checkout should fail if total < ₹1.00"""
    user = django_user_model.objects.create_user(
        username='custuser9', email='cust9@example.com', password='pass123', role='customer'
    )
    client.login(username='custuser9', password='pass123')

    product = Product.objects.create(name='Cheap Item', description='Very cheap')
    variant = ProductVariant.objects.create(
        product=product, size='XS', color='Gray', price='0.50', stock_quantity=10
    )

    # Add to cart (total < 1.00)
    client.post(reverse('orders:add_to_cart'), data={'variant_id': variant.id, 'quantity': 1})

    response = client.get(reverse('orders:checkout_cart'))

    # Should redirect because total < ₹1
    assert response.status_code == 302
    assert reverse('orders:cart_detail') in response.url


@pytest.mark.django_db
def test_cart_checkout_success_creates_session_data(client, django_user_model, monkeypatch):
    """Valid checkout should set Razorpay session data properly."""
    user = django_user_model.objects.create_user(
        username='custuser10', email='cust10@example.com', password='pass123', role='customer'
    )
    client.login(username='custuser10', password='pass123')

    product = Product.objects.create(name='Normal Product', description='For checkout success')
    variant = ProductVariant.objects.create(
        product=product, size='M', color='Pink', price='200.00', stock_quantity=5
    )

    # Add valid item
    client.post(reverse('orders:add_to_cart'), data={'variant_id': variant.id, 'quantity': 2})

    # Monkeypatch Razorpay order creation
    monkeypatch.setattr(
        "nail_ecommerce_project.apps.orders.utils.create_razorpay_order",
        lambda total, currency='INR': {"id": "test_rzp_order_123"}
    )

    response = client.get(reverse('orders:checkout_cart'))

    # Should load checkout page
    assert response.status_code == 200

    # Verify Razorpay order_id stored in session
    session = client.session
    assert session['cart_razorpay_order_id'] == "test_razorpay_order_id"
    assert 'pre_payment_cart' in session
    assert session['pre_payment_cart'][0]['variant_id'] == variant.id


@pytest.mark.django_db
def test_add_to_cart_missing_variant_id_redirects(client, django_user_model):
    # Setup customer
    user = django_user_model.objects.create_user(
        username='cust_edge1', email='edge1@example.com', password='pass123', role='customer'
    )
    client.login(username='cust_edge1', password='pass123')

    # POST without variant_id
    response = client.post(reverse('orders:add_to_cart'), data={'quantity': 2})

    # Should redirect to product list
    assert response.status_code == 302
    assert reverse('products:product_list') in response.url

    # Ensure cart stays empty
    assert client.session.get(Cart.SESSION_KEY, {}) == {}


@pytest.mark.django_db
def test_add_to_cart_defaults_to_quantity_1(client, django_user_model):
    user = django_user_model.objects.create_user(
        username='cust_edge2', email='edge2@example.com', password='pass123', role='customer'
    )
    client.login(username='cust_edge2', password='pass123')

    product = Product.objects.create(name='Edge Product', description='Edge Desc')
    variant = ProductVariant.objects.create(
        product=product, size='M', color='Yellow', price='20.00', stock_quantity=5
    )

    # No quantity provided
    response = client.post(reverse('orders:add_to_cart'), data={'variant_id': variant.id})

    # Should add 1 item
    cart_data = client.session.get(Cart.SESSION_KEY)
    assert cart_data[str(variant.id)]['quantity'] == 1
    assert response.status_code == 302


@pytest.mark.django_db
def test_remove_from_cart_variant_not_in_cart(client, django_user_model):
    user = django_user_model.objects.create_user(
        username='cust_edge3', email='edge3@example.com', password='pass123', role='customer'
    )
    client.login(username='cust_edge3', password='pass123')

    # Create variant but never add to cart
    product = Product.objects.create(name='Edge Product 2', description='Edge Desc')
    variant = ProductVariant.objects.create(
        product=product, size='XL', color='Black', price='30.00', stock_quantity=10
    )

    # Remove variant not in cart
    response = client.post(reverse('orders:remove_from_cart', kwargs={'variant_id': variant.id}))

    # Should still redirect to cart detail (no error)
    assert response.status_code == 302
    assert reverse('orders:cart_detail') in response.url
    # Cart remains empty
    assert client.session.get(Cart.SESSION_KEY, {}) == {}


@pytest.mark.django_db
def test_remove_from_empty_cart(client, django_user_model):
    user = django_user_model.objects.create_user(
        username='cust_edge4', email='edge4@example.com', password='pass123', role='customer'
    )
    client.login(username='cust_edge4', password='pass123')

    # Use completely invalid variant id
    response = client.post(reverse('orders:remove_from_cart', kwargs={'variant_id': 12345}))

    # Should 404 since variant doesn't exist
    assert response.status_code == 404
    # Cart still empty
    assert client.session.get(Cart.SESSION_KEY, {}) == {}


@pytest.mark.django_db
def test_cart_detail_view_empty_cart(client, django_user_model):
    user = django_user_model.objects.create_user(
        username='cust_edge5', email='edge5@example.com', password='pass123', role='customer'
    )
    client.login(username='cust_edge5', password='pass123')

    # Directly access cart detail (cart is empty)
    response = client.get(reverse('orders:cart_detail'))
    assert response.status_code == 200
    # Should mention no items or render without crash
    content = response.content.decode()
    assert "Cart" in content


@pytest.mark.django_db
def test_cart_checkout_forbidden_for_non_customer(client, django_user_model):
    user = django_user_model.objects.create_user(
        username='staffuser', email='staff@example.com', password='pass123', role='staff'
    )
    client.login(username='staffuser', password='pass123')

    response = client.get(reverse('orders:checkout_cart'))
    assert response.status_code == 403  # PermissionDenied for non-customer


@pytest.mark.django_db
def test_cart_checkout_redirects_for_anonymous(client):
    # Anonymous user tries checkout
    response = client.get(reverse('orders:checkout_cart'))

    # Should redirect to login
    assert response.status_code == 302
    assert "/login" in response.url
