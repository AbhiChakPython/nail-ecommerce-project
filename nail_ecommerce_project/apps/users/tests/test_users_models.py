import pytest
from django.contrib.auth import get_user_model
from nail_ecommerce_project.apps.users.models import CustomerAddress
from nail_ecommerce_project.apps.users.models import UserRole

User = get_user_model()

@pytest.mark.django_db
class TestCustomUserModel:

    def test_create_customer_user(self):
        user = User.objects.create_user(
            username='customer1',
            email='customer1@example.com',
            password='securepass123',
            full_name='Ravi Kumar'
        )
        assert user.username == 'customer1'
        assert user.email == 'customer1@example.com'
        assert user.role == UserRole.CUSTOMER
        assert user.is_customer is True
        assert user.check_password('securepass123') is True

    def test_create_admin_user(self):
        user = User.objects.create_superuser(
            username='admin1',
            email='admin@example.com',
            password='adminpass',
            full_name='Admin User'
        )
        assert user.is_superuser is True
        assert user.is_staff is True
        assert user.role == UserRole.ADMIN
        assert user.is_customer is False

    def test_role_and_is_customer_sync(self):
        user = User.objects.create_user(
            username='mixeduser',
            email='mixed@example.com',
            password='mixedpass',
            full_name='Mixed Role',
            role=UserRole.ADMIN
        )
        assert user.is_customer is False  # should sync with role

    def test_duplicate_username_raises_error(self):
        User.objects.create_user(
            username='uniqueuser',
            email='unique@example.com',
            password='pass',
            full_name='User One'
        )
        with pytest.raises(Exception):
            User.objects.create_user(
                username='uniqueuser',
                email='another@example.com',
                password='pass',
                full_name='User Two'
            )

    def test_get_short_name(self):
        user = User.objects.create_user(
            username='shorty',
            email='short@example.com',
            password='shortpass',
            full_name='Priya Sharma'
        )
        assert user.get_short_name() == 'Priya'


@pytest.mark.django_db
class TestCustomerAddressModel:

    def test_address_completion_true_and_false(self):
        user = User.objects.create_user(
            username='addruser',
            email='addr@example.com',
            password='addrpass',
            full_name='Address User'
        )

        address = CustomerAddress.objects.create(
            user=user,
            address_line1='Flat 12',
            address_line2='Park Street',
            city='Pune',
            state='Maharashtra',
            pincode='411001',
            landmark='Near Mall',
            use_for_home_service=True
        )

        # Test all fields populated and is_complete = True
        assert address.address_line1 == 'Flat 12'
        assert address.address_line2 == 'Park Street'
        assert address.city == 'Pune'
        assert address.state == 'Maharashtra'
        assert address.pincode == '411001'
        assert address.landmark == 'Near Mall'
        assert address.use_for_home_service is True
        assert address.is_complete is True

        # Test incomplete address: address_line2 missing
        address.address_line2 = ''
        address.save()
        address.refresh_from_db()
        print(f"address_line2: '{address.address_line2}'")
        print(f"is_complete: {address.is_complete}")
        assert address.is_complete is False

    def test_customer_address_str_output(self):
        user = User.objects.create_user(
            username='addrtest',
            email='addrtest@example.com',
            password='pass',
            full_name='Address Tester'
        )
        address = CustomerAddress.objects.create(
            user=user,
            address_line1='A1',
            address_line2='A2',
            city='City',
            state='State',
            pincode='999999'
        )
        assert str(address) == "addrtest's address"


@pytest.mark.django_db
def test_get_full_name_method():
    user = User.objects.create_user(
        username='fulltest',
        email='fulltest@example.com',
        password='fullpass',
        full_name='Simran Kaur'
    )
    assert user.get_full_name() == 'Simran Kaur'
