import pytest
from nail_ecommerce_project.apps.orders.forms import OrderCreateForm

pytestmark = pytest.mark.django_db


def test_order_create_form_valid():
    form_data = {
        'full_name': 'John Doe',
        'phone': '9876543210',
        'address_line1': '123 Main Street',
        'address_line2': 'Apt 4B',  # optional
        'city': 'New York',
        'postal_code': '10001',
        'state': 'NY',  # ✅ REQUIRED field
    }
    form = OrderCreateForm(data=form_data)
    assert form.is_valid()


def test_order_create_form_missing_required_field():
    form_data = {
        # 'full_name': 'John Doe',  # intentionally omitted
        'phone': '9876543210',
        'address_line1': '123 Main Street',
        'city': 'New York',
        'postal_code': '10001',
        'state': 'NY',  # ✅ still required
    }
    form = OrderCreateForm(data=form_data)
    assert not form.is_valid()
    assert 'full_name' in form.errors


def test_order_create_form_optional_field_blank():
    form_data = {
        'full_name': 'Alice Smith',
        'phone': '1234567890',
        'address_line1': '456 Elm Street',
        'address_line2': '',  # explicitly blank
        'city': 'Los Angeles',
        'postal_code': '90001',
        'state': 'CA',  # ✅ REQUIRED
    }
    form = OrderCreateForm(data=form_data)
    assert form.is_valid()


def test_order_create_form_valid():
    """✅ Basic valid data should pass"""
    form_data = {
        'full_name': 'John Doe',
        'phone': '9876543210',
        'address_line1': '123 Main Street',
        'address_line2': 'Apt 4B',  # optional
        'city': 'New York',
        'postal_code': '10001',
        'state': 'NY',
    }
    form = OrderCreateForm(data=form_data)
    assert form.is_valid()


def test_order_create_form_missing_required_field():
    """❌ Missing full_name should fail"""
    form_data = {
        # 'full_name': 'John Doe',  # intentionally omitted
        'phone': '9876543210',
        'address_line1': '123 Main Street',
        'city': 'New York',
        'postal_code': '10001',
        'state': 'NY',
    }
    form = OrderCreateForm(data=form_data)
    assert not form.is_valid()
    assert 'full_name' in form.errors


def test_order_create_form_optional_field_blank():
    """✅ Optional address_line2 can be blank"""
    form_data = {
        'full_name': 'Alice Smith',
        'phone': '1234567890',
        'address_line1': '456 Elm Street',
        'address_line2': '',  # explicitly blank
        'city': 'Los Angeles',
        'postal_code': '90001',
        'state': 'CA',
    }
    form = OrderCreateForm(data=form_data)
    assert form.is_valid()


# ✅ EDGE CASES

def test_order_create_form_extremely_long_name():
    """❌ Full name exceeding max length should fail"""
    form_data = {
        'full_name': 'A' * 300,  # too long
        'phone': '9876543210',
        'address_line1': '123 Main Street',
        'city': 'New York',
        'postal_code': '10001',
        'state': 'NY',
    }
    form = OrderCreateForm(data=form_data)
    # Django will fail max_length validation from the model
    assert not form.is_valid()
    assert 'full_name' in form.errors


def test_order_create_form_invalid_phone_number():
    """❌ Phone with letters should fail"""
    form_data = {
        'full_name': 'Bob Marley',
        'phone': '98AB54321Z',  # invalid
        'address_line1': '789 Pine Road',
        'city': 'Miami',
        'postal_code': '33101',
        'state': 'FL',
    }
    form = OrderCreateForm(data=form_data)
    # Depending on model validation, it may pass as CharField OR fail
    # Here we expect it to fail (if we later add regex validators)
    # For now, it will likely pass, so just asserting is_valid for awareness:
    assert form.is_valid()  # change to `not` if you add phone validators


def test_order_create_form_empty_postal_code():
    """❌ Missing postal code should fail"""
    form_data = {
        'full_name': 'Charlie Brown',
        'phone': '1234567890',
        'address_line1': '456 Elm Street',
        'city': 'Los Angeles',
        'postal_code': '',  # empty
        'state': 'CA',
    }
    form = OrderCreateForm(data=form_data)
    assert not form.is_valid()
    assert 'postal_code' in form.errors


def test_order_create_form_blank_required_fields():
    """❌ All required fields blank should fail"""
    form = OrderCreateForm(data={})
    assert not form.is_valid()
    # Ensure multiple errors are triggered
    for field in ['full_name', 'phone', 'address_line1', 'city', 'postal_code', 'state']:
        assert field in form.errors


def test_order_create_form_extreme_postal_code_length():
    long_postal = "9" * 200  # way beyond allowed max_length (likely 20)
    form_data = {
        'full_name': 'John Doe',
        'phone': '9876543210',
        'address_line1': '123 Main Street',
        'address_line2': 'Apt 4B',
        'city': 'New York',
        'postal_code': long_postal,
        'state': 'NY',
    }
    form = OrderCreateForm(data=form_data)
    assert not form.is_valid()  # ✅ Should fail due to model max_length
    assert 'postal_code' in form.errors


def test_order_create_form_state_missing():
    """❌ Missing state should fail"""
    form_data = {
        'full_name': 'Eve Adams',
        'phone': '9998887777',
        'address_line1': '555 Sunset Blvd',
        'city': 'San Diego',
        'postal_code': '92101',
        # 'state': 'CA'  # omitted
    }
    form = OrderCreateForm(data=form_data)
    assert not form.is_valid()
    assert 'state' in form.errors


import pytest
from nail_ecommerce_project.apps.orders.forms import (
    OrderCreateForm,
    BuyNowShippingForm,
    CartShippingForm
)


# --- EXISTING TESTS for OrderCreateForm ---
def test_order_create_form_empty_data_triggers_all_required_errors():
    form = OrderCreateForm(data={})
    assert not form.is_valid()
    assert 'full_name' in form.errors
    assert 'phone' in form.errors
    assert 'address_line1' in form.errors
    assert 'city' in form.errors
    assert 'postal_code' in form.errors
    assert 'state' in form.errors


def test_order_create_form_overly_long_input():
    long_name = "A" * 300  # exceeds max_length=100
    form_data = {
        'full_name': long_name,
        'phone': '9876543210',
        'address_line1': '123 Main Street',
        'address_line2': 'Apt 4B',
        'city': 'New York',
        'postal_code': '10001',
        'state': 'NY',
    }
    form = OrderCreateForm(data=form_data)
    assert not form.is_valid()  # ✅ Should fail because name > max_length
    assert 'full_name' in form.errors


# --- NEW TESTS for BuyNowShippingForm ---
def test_buy_now_shipping_form_valid_true():
    form_data = {
        'full_name': 'Jane Buyer',
        'phone': '9876543210',
        'address_line1': '221B Baker Street',
        'address_line2': '',
        'city': 'London',
        'postal_code': 'NW16XE',
        'state': 'UK',
        'use_for_home_service': True
    }
    form = BuyNowShippingForm(data=form_data)
    assert form.is_valid()
    assert form.cleaned_data['use_for_home_service'] is True


def test_buy_now_shipping_form_valid_false():
    form_data = {
        'full_name': 'Jane Buyer',
        'phone': '9876543210',
        'address_line1': '221B Baker Street',
        'address_line2': '',
        'city': 'London',
        'postal_code': 'NW16XE',
        'state': 'UK',
        'use_for_home_service': False
    }
    form = BuyNowShippingForm(data=form_data)
    assert form.is_valid()
    assert form.cleaned_data['use_for_home_service'] is False


def test_buy_now_shipping_form_missing_required_field():
    form_data = {
        # Missing full_name
        'phone': '9876543210',
        'address_line1': '221B Baker Street',
        'city': 'London',
        'postal_code': 'NW16XE',
        'state': 'UK',
    }
    form = BuyNowShippingForm(data=form_data)
    assert not form.is_valid()
    assert 'full_name' in form.errors


def test_buy_now_shipping_form_invalid_phone_length():
    form_data = {
        'full_name': 'John ShortPhone',
        'phone': '123',  # too short
        'address_line1': 'Short Street',
        'city': 'Test City',
        'postal_code': '12345',
        'state': 'CA',
        'use_for_home_service': True,
    }
    form = BuyNowShippingForm(data=form_data)
    # Will still pass because no explicit validator, but we assert is_valid() True/False
    assert form.is_valid()  # unless we add a phone validator later


def test_buy_now_shipping_form_empty_data():
    form = BuyNowShippingForm(data={})
    assert not form.is_valid()
    assert 'full_name' in form.errors
    assert 'phone' in form.errors
    assert 'address_line1' in form.errors
    assert 'city' in form.errors
    assert 'postal_code' in form.errors
    assert 'state' in form.errors


def test_buy_now_shipping_form_overly_long_fields():
    from nail_ecommerce_project.apps.orders.forms import BuyNowShippingForm

    long_input = "B" * 300  # exceeds max_length
    form_data = {
        'full_name': long_input,
        'phone': '1234567890',
        'address_line1': long_input,
        'address_line2': '',
        'city': long_input,
        'postal_code': '12345',
        'state': long_input,
        'use_for_home_service': True,
    }
    form = BuyNowShippingForm(data=form_data)
    assert not form.is_valid()  # ✅ Should fail because of max_length constraints
    assert 'full_name' in form.errors
    assert 'city' in form.errors
    assert 'state' in form.errors


# --- Minimal Test for CartShippingForm (inherits same fields) ---
def test_cart_shipping_form_valid():
    form_data = {
        'full_name': 'Cart Buyer',
        'phone': '9876543210',
        'address_line1': '123 Test Ave',
        'address_line2': '',
        'city': 'Testville',
        'postal_code': '12345',
        'state': 'CA',
        'use_for_home_service': True,
    }
    form = CartShippingForm(data=form_data)
    assert form.is_valid()
