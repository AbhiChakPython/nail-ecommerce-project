from nail_ecommerce_project.apps.users.models import CustomUser
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def api_client():
    """Use DRF APIClient for API requests"""
    return APIClient()

@pytest.fixture
def create_test_user(db):
    """Create a user for authentication tests"""
    password = "securepass123"
    user = User.objects.create_user(
        username="apitestuser",
        email="apitestuser@example.com",
        full_name="API Test User",
        password=password,
        phone_number="9999999999",
        role="customer"
    )
    return user, password

@pytest.fixture
def auth_client(create_test_user):
    """Authenticated DRF API client"""
    user, _ = create_test_user  # ✅ unpack user & password
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.mark.django_db
class TestRegisterAPIView:
    def test_register_success(self, api_client):
        url = reverse('users_api:api_register')
        payload = {
            "username": "newuser",
            "email": "newuser@example.com",
            "full_name": "New User",
            "phone_number": "9876543210",
            "role": "customer",
            "password": "StrongPass123",
            "password2": "StrongPass123",
            "address_line1": "123 Main St",
            "address_line2": "Apt 4B",
            "landmark": "Near Park",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "use_for_home_service": True
        }
        response = api_client.post(url, payload, format='json')

        print("DEBUG RESPONSE:", response.data)
        assert response.status_code == 201
        assert response.data['message'] == 'User registered successfully.'
        assert CustomUser.objects.filter(email="newuser@example.com").exists()

    def test_register_fail_invalid_data(self, api_client):
        url = reverse('users_api:api_register')
        payload = {
            "username": "baduser",
            "email": "",  # invalid
            "full_name": "Bad User",
            "phone_number": "invalid",  # might still be accepted if no validation
            "address": "",
            "role": "customer",
            "password": "123",
            "password2": "321"  # mismatch
        }
        response = api_client.post(url, payload, format='json')

        assert response.status_code == 400
        assert "password" in response.data or "email" in response.data

@pytest.mark.django_db
class TestLoginAPIView:
    def test_login_success(self, api_client, create_test_user):
        user, password = create_test_user  # ✅ unpack properly
        response = api_client.post(reverse('users_api:api_login'), {
            "username": user.username,
            "password": password
        }, format='json')

        assert response.status_code == 200
        assert "access" in response.data

    def test_login_fail_wrong_credentials(self, api_client):
        """Login with wrong credentials should return 401"""
        response = api_client.post(reverse('users_api:api_login'), {
            "username": "wronguser",
            "password": "wrongpass"
        }, format='json')

        print("🔴 LOGIN FAIL RESPONSE:", response.data)

        assert response.status_code == 401  # Unauthorized
        assert "access" not in response.data


@pytest.mark.django_db
class TestProfileAPIView:
    def test_profile_retrieve_authenticated(self, api_client, create_test_user):
        """✅ Authenticated user can retrieve their profile"""
        user, _ = create_test_user
        api_client.force_authenticate(user=user)

        url = reverse('users_api:api_profile')
        response = api_client.get(url)

        assert response.status_code == 200
        assert response.data['username'] == user.username
        assert response.data['email'] == user.email

    def test_profile_retrieve_unauthenticated(self, api_client):
        """❌ Unauthenticated should return 401"""
        url = reverse('users_api:api_profile')
        response = api_client.get(url)
        assert response.status_code == 401

    def test_profile_update_authenticated(self, api_client, create_test_user):
        """✅ Authenticated user can update allowed fields"""
        user, _ = create_test_user
        api_client.force_authenticate(user=user)

        url = reverse('users_api:api_profile')
        payload = {
            "full_name": "Updated Name",
            "phone_number": "9999999999",
            "is_staff": True  # should NOT actually update
        }

        response = api_client.put(url, payload, format='json')
        assert response.status_code == 200

        user.refresh_from_db()
        assert user.full_name == "Updated Name"
        assert user.phone_number == "9999999999"
        # Ensure read-only field not updated
        assert user.is_staff is False

    def test_profile_update_unauthenticated(self, api_client):
        """❌ Unauthenticated should return 401"""
        url = reverse('users_api:api_profile')
        payload = {"full_name": "Should Fail"}
        response = api_client.put(url, payload, format='json')
        assert response.status_code == 401


@pytest.mark.django_db
class TestChangePasswordAPIView:

    @pytest.fixture
    def authenticated_client(self, create_test_user):
        user, _ = create_test_user
        client = APIClient()
        client.force_authenticate(user=user)
        return client, user

    def test_change_password_success(self, auth_client, create_test_user):
        """✅ Authenticated user can successfully change password"""
        url = reverse('users_api:api_change_password')

        payload = {
            "old_password": "securepass123",
            "new_password": "NewSecurePass123!"
        }
        response = auth_client.post(url, payload, format='json')

        assert response.status_code == 200
        # ✅ Adjusted expected message to match API response
        assert response.data['message'] == "Password changed successfully."

    def test_change_password_unauthenticated(self, api_client):
        """❌ Unauthenticated should return 403 (Forbidden)"""
        url = reverse('users_api:api_change_password')
        payload = {
            "old_password": "randomold",
            "new_password": "NewPass123!"
        }
        response = api_client.put(url, payload, format='json')

        # ✅ Adjusted to match actual behavior
        assert response.status_code == 403

    def test_change_password_wrong_old(self, authenticated_client):
        """❌ Wrong old password"""
        client, _ = authenticated_client
        url = reverse('users_api:api_change_password')

        payload = {
            "old_password": "wrongoldpass",
            "new_password": "NewStrongPass123"
        }

        response = client.post(url, payload, format='json')

        assert response.status_code == 400
        assert "old_password" in response.data

    def test_change_password_weak_new_password(self, authenticated_client):
        """❌ Weak new password should be rejected"""
        client, _ = authenticated_client
        url = reverse('users_api:api_change_password')

        payload = {
            "old_password": "securepass123",
            "new_password": "123"
        }

        response = client.post(url, payload, format='json')

        assert response.status_code == 400
        assert "new_password" in response.data
