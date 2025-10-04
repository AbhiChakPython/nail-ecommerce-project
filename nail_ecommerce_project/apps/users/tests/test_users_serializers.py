import pytest
from django.contrib.auth import get_user_model
from nail_ecommerce_project.apps.users.serializers import (
    UserRegisterSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer
)
from nail_ecommerce_project.apps.users.models import CustomerAddress

User = get_user_model()


@pytest.fixture
def user_data():
    return {
        "username": "john_doe",
        "email": "john@example.com",
        "full_name": "John Doe",
        "phone_number": "1234567890",
        "role": "customer",
        "password": "StrongPass123!",
        "password2": "StrongPass123!",
        "address_line1": "123 Main St",
        "address_line2": "Apt 4",
        "landmark": "Near Park",
        "city": "Metropolis",
        "state": "NY",
        "pincode": "123456",
        "use_for_home_service": True
    }


@pytest.mark.django_db
def test_user_register_serializer_creates_user_with_address(user_data):
    serializer = UserRegisterSerializer(data=user_data)
    assert serializer.is_valid(), serializer.errors

    user = serializer.save()

    # ✅ Check user created
    assert User.objects.filter(email=user_data["email"]).exists()
    assert user.check_password(user_data["password"])

    # ✅ Check address created
    address = CustomerAddress.objects.get(user=user)
    assert address.city == "Metropolis"
    assert address.use_for_home_service is True


@pytest.mark.django_db
def test_user_register_serializer_password_mismatch(user_data):
    user_data["password2"] = "WrongPass123!"
    serializer = UserRegisterSerializer(data=user_data)
    assert not serializer.is_valid()
    assert "password" in serializer.errors


@pytest.mark.django_db
def test_user_register_serializer_weak_password(user_data):
    user_data["password"] = "123"
    user_data["password2"] = "123"
    serializer = UserRegisterSerializer(data=user_data)
    assert not serializer.is_valid()
    assert "password" in serializer.errors


@pytest.mark.django_db
def test_user_register_serializer_duplicate_email(user_data):
    # First user registration
    serializer1 = UserRegisterSerializer(data=user_data)
    serializer1.is_valid(raise_exception=True)
    serializer1.save()

    # Try again with same email → should fail
    serializer2 = UserRegisterSerializer(data=user_data)
    assert not serializer2.is_valid()
    assert "email" in serializer2.errors


@pytest.mark.django_db
def test_user_serializer_returns_nested_address(user_data):
    serializer = UserRegisterSerializer(data=user_data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    # Serialize user
    user_serializer = UserSerializer(user)
    data = user_serializer.data

    assert data["username"] == user_data["username"]
    assert "address" in data
    assert data["address"]["city"] == "Metropolis"


@pytest.mark.django_db
def test_user_serializer_update_does_not_change_read_only_fields(user_data):
    serializer = UserRegisterSerializer(data=user_data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    update_serializer = UserSerializer(
        user,
        data={"is_superuser": True, "full_name": "Changed Name"},
        partial=True
    )
    assert update_serializer.is_valid()
    updated_user = update_serializer.save()

    # ✅ Should update only allowed fields
    assert updated_user.full_name == "Changed Name"
    assert not updated_user.is_superuser


def test_change_password_serializer_valid():
    serializer = ChangePasswordSerializer(data={
        "old_password": "OldPass123!",
        "new_password": "NewStrongPass123!"
    })
    assert serializer.is_valid(), serializer.errors


def test_change_password_serializer_weak_password():
    serializer = ChangePasswordSerializer(data={
        "old_password": "OldPass123!",
        "new_password": "123"
    })
    assert not serializer.is_valid()
    assert "new_password" in serializer.errors


@pytest.mark.django_db
def test_custom_token_obtain_pair_serializer_includes_user_details(user_data):
    # Create user
    serializer = UserRegisterSerializer(data=user_data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    # Get token
    token_serializer = CustomTokenObtainPairSerializer.get_token(user)
    assert "email" in token_serializer
    assert token_serializer["email"] == user.email
    assert token_serializer["role"] == user.role
