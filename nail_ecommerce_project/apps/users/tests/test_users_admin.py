import pytest
from django.contrib import admin
from django.urls import reverse
from django.test import Client
from nail_ecommerce_project.apps.users.models import CustomUser, CustomerAddress
from nail_ecommerce_project.apps.users.admin import UserAdmin, CustomerAddressAdmin, AdminUserCreationForm


@pytest.mark.django_db
def test_customuser_registered():
    assert isinstance(admin.site._registry.get(CustomUser), UserAdmin)


@pytest.mark.django_db
def test_customeraddress_registered():
    assert isinstance(admin.site._registry.get(CustomerAddress), CustomerAddressAdmin)


@pytest.mark.django_db
def test_admin_user_creation_form_validates_matching_passwords():
    form_data = {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "customer",
        "password1": "securepass123",
        "password2": "securepass123",
    }
    form = AdminUserCreationForm(data=form_data)
    assert form.is_valid()


@pytest.mark.django_db
def test_admin_user_creation_form_rejects_mismatched_passwords():
    form_data = {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "customer",
        "password1": "pass1",
        "password2": "pass2",
    }
    form = AdminUserCreationForm(data=form_data)
    assert not form.is_valid()
    assert "Passwords don't match" in form.errors['password2'][0]


@pytest.mark.django_db
def test_admin_user_change_page_loads(admin_client):
    user = CustomUser.objects.create_user(username="testuser", email="test@example.com", password="pass123")
    url = reverse("admin:users_customuser_change", args=[user.id])
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_customeraddress_page_loads(admin_client):
    user = CustomUser.objects.create_user(username="cust", email="cust@example.com", password="pass123")
    address = CustomerAddress.objects.create(user=user, address_line1="Line 1", city="City", state="State", pincode="123456")
    url = reverse("admin:users_customeraddress_change", args=[address.id])
    response = admin_client.get(url)
    assert response.status_code == 200
