import pytest
from django.contrib.auth import get_user_model, authenticate
from nail_ecommerce_project.apps.users.forms import UserCreationForm, UserChangeForm, UsernameAuthenticationForm
from django.test import RequestFactory

User = get_user_model()

@pytest.mark.django_db
class TestUserCreationForm:
    def test_valid_user_creation_form(self):
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password1": "strongpassword123",
            "password2": "strongpassword123",
            "phone_number": "9876543210",
        }
        form = UserCreationForm(data=form_data)
        if not form.is_valid():
            print("\nForm Errors:", form.errors)

        assert form.is_valid()
        user = form.save()
        assert user.username == "testuser"
        assert user.role == "customer"

    def test_password_mismatch(self):
        form_data = {
            "username": "user1",
            "email": "user1@example.com",
            "full_name": "User One",
            "password1": "password1",
            "password2": "password2",  # mismatch
            "role": "customer"
        }
        form = UserCreationForm(data=form_data)
        assert not form.is_valid()
        assert "Passwords don’t match." in form.errors["password2"]

    def test_duplicate_email(self):
        User.objects.create_user(username="userx", email="dupe@example.com", password="12345")
        form_data = {
            "username": "newuser",
            "email": "dupe@example.com",  # duplicate
            "full_name": "Dup Email",
            "password1": "password123",
            "password2": "password123",
            "role": "customer"
        }
        form = UserCreationForm(data=form_data)
        assert not form.is_valid()
        assert "Email is already registered." in form.errors["email"]

    def test_duplicate_username(self):
        User.objects.create_user(username="duplicate", email="unique@example.com", password="12345")
        form_data = {
            "username": "duplicate",  # duplicate
            "email": "new@example.com",
            "full_name": "Dup Username",
            "password1": "password123",
            "password2": "password123",
            "role": "customer"
        }
        form = UserCreationForm(data=form_data)
        assert not form.is_valid()
        assert "Username is already taken." in form.errors["username"]


@pytest.mark.django_db
class TestUserChangeForm:
    def test_change_form_valid_fields(self):
        user = User.objects.create_user(username="chuser", email="ch@example.com", password="12345")
        form_data = {
            "email": "newemail@example.com",
            "full_name": "Changed User",
            "phone_number": "9999999999"
        }
        form = UserChangeForm(data=form_data, instance=user)
        assert form.is_valid()
        updated_user = form.save()
        assert updated_user.email == "newemail@example.com"
        assert updated_user.full_name == "Changed User"

@pytest.mark.django_db
class TestUsernameAuthenticationForm:
    def test_valid_login_allowed(self, client):
        user = User.objects.create_user(username="authuser", email="a@b.com", password="pass123")

        # Simulate authentication manually
        authenticated_user = authenticate(username="authuser", password="pass123")
        assert authenticated_user is not None  # Ensure authentication succeeds

        # Now test the form logic with a real request
        request = RequestFactory().post("/login/", data={"username": "authuser", "password": "pass123"})
        form = UsernameAuthenticationForm(request, data={"username": "authuser", "password": "pass123"})

        assert form.is_valid()
        assert form.get_user() == authenticated_user

from nail_ecommerce_project.apps.users.forms import CustomerAddressForm

@pytest.mark.django_db
class TestCustomerAddressForm:

    def test_valid_address_form(self, django_user_model):
        user = django_user_model.objects.create_user(username='addruser', email='addr@example.com', password='1234')
        form_data = {
            "address_line1": "Flat 101",
            "address_line2": "MG Road",
            "landmark": "Near Metro",
            "city": "Pune",
            "pincode": "411001",
            "state": "Maharashtra",
            "use_for_home_service": True
        }
        form = CustomerAddressForm(data=form_data)
        assert form.is_valid()
        address = form.save(commit=False)
        address.user = user
        address.save()
        assert address.user.username == 'addruser'

    def test_invalid_pincode_format(self):
        form_data = {
            "address_line1": "Flat 101",
            "address_line2": "MG Road",
            "landmark": "Near Metro",
            "city": "Pune",
            "pincode": "411",  # Invalid
            "state": "Maharashtra",
            "use_for_home_service": True
        }
        form = CustomerAddressForm(data=form_data)
        assert not form.is_valid()
        assert "Please enter a valid 6-digit PIN code." in form.errors["pincode"]
