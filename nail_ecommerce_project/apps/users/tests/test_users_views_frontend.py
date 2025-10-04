import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from nail_ecommerce_project.apps.users.forms import UserCreationForm

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestRegisterView:
    def test_register_user_success(self, client):
        response = client.post(reverse('users:register'), {
            'username': 'newuser',
            'email': 'new@x.com',
            'full_name': 'New User',
            'password1': 'securepass123',
            'password2': 'securepass123',
            'role': 'customer',
            'phone_number': '9876543210',

            # Address fields
            'address_line1': '123 Main St',
            'address_line2': 'Apt 4B',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400001',
            'landmark': 'Near Park',
            'use_for_home_service': 'on',
        })

        print("🧾 Response status:", response.status_code)

        if response.status_code == 200:
            print("🧾 Form errors:", response.context.get('form').errors if 'form' in response.context else 'No form')
            print("📬 Address form errors:", response.context.get(
                'address_form').errors if 'address_form' in response.context else 'No address form')

        assert response.status_code == 302
        assert User.objects.filter(username='newuser').exists()

    def test_register_user_fail_due_to_password_mismatch(self, client):
        data = {
            'username': 'newuser2',
            'email': 'new2@x.com',
            'full_name': 'New User 2',
            'password1': 'pass123',
            'password2': 'pass456',
            'role': 'customer',
            'phone_number': '9876543210',
        }
        form = UserCreationForm(data)
        assert not form.is_valid()
        assert "Passwords don’t match." in str(form.errors)


class TestLoginLogoutViews:
    @pytest.fixture
    def test_user(self):
        return User.objects.create_user(username="testlogin", email="log@x.com", password="pass123")

    def test_login_success(self, client, test_user):
        response = client.post(reverse('users:login'), {
            'username': 'testlogin',
            'password': 'pass123'
        })
        assert response.status_code == 302
        assert response.url == reverse('core:home')

    def test_login_fail_invalid_credentials(self, client):
        response = client.post(reverse('users:login'), {
            'username': 'fakeuser',
            'password': 'wrongpass'
        })
        assert response.status_code == 200
        assert b"This account is inactive." not in response.content

    def test_logout_success(self, client, test_user):
        client.login(username='testlogin', password='pass123')
        response = client.post(reverse('users:logout'))
        assert response.status_code == 302
        assert response.url == reverse('users:login')

    def test_login_fails_for_inactive_user(self, client):
        User.objects.create_user(
            username="inactiveuser",
            email="inactive@x.com",
            password="pass123",
            is_active=False
        )
        response = client.post(reverse('users:login'), {
            'username': 'inactiveuser',
            'password': 'pass123'
        })
        assert response.status_code == 200
        assert b"Please enter a correct username and password" in response.content


class TestProfileView:
    @pytest.fixture
    def profile_user(self, django_user_model):
        from nail_ecommerce_project.apps.users.models import CustomerAddress
        user = django_user_model.objects.create_user(
            username='profileuser',
            email='profile@x.com',
            password='pass123',
            full_name='Old Name',
        )
        CustomerAddress.objects.create(
            user=user,
            address_line1='Old Flat',
            address_line2='Old Street',
            city='Old City',
            state='Old State',
            pincode='000000',
            use_for_home_service=True
        )
        return user

    def test_profile_get_view(self, client, profile_user):
        client.login(username='profileuser', password='pass123')
        response = client.get(reverse('users:profile'))
        assert response.status_code == 200
        assert b'Welcome' in response.content

    def test_profile_update_user_and_address(self, client, profile_user):
        # 🔐 Login first
        client.login(username='profileuser', password='pass123')

        # 📨 POST form submission to update both user info + address
        response = client.post(reverse('users:profile'), data={
            'full_name': 'Updated Name',
            'email': 'updated@x.com',
            'phone_number': '9876543210',
            'address_line1': 'Updated Flat',
            'address_line2': 'Updated Street',
            'landmark': 'Near Park',
            'city': 'Updated City',
            'state': 'Updated State',
            'pincode': '123456',
            'use_for_home_service': 'on',
        })

        # 🔁 Should redirect after successful POST
        assert response.status_code == 302
        assert response.url == reverse('users:profile')

        # ✅ Refetch from DB and verify changes
        profile_user.refresh_from_db()
        assert profile_user.full_name == 'Updated Name'
        assert profile_user.email == 'updated@x.com'
        assert profile_user.phone_number == '9876543210'

        address = profile_user.address
        assert address.address_line1 == 'Updated Flat'
        assert address.address_line2 == 'Updated Street'
        assert address.landmark == 'Near Park'
        assert address.city == 'Updated City'
        assert address.state == 'Updated State'
        assert address.pincode == '123456'
        assert address.use_for_home_service is True


class TestPasswordChangeView:
    @pytest.fixture
    def password_user(self):
        return User.objects.create_user(username='changepass', email='cp@x.com', password='oldpass123')

    def test_change_password_success(self, client, password_user):
        client.login(username='changepass', password='oldpass123')
        response = client.post(reverse('users:change_password'), {
            'old_password': 'oldpass123',
            'new_password1': 'newpass456',
            'new_password2': 'newpass456',
        })
        assert response.status_code == 302
        assert response.url == reverse('users:login')


class TestErrorViews:
    def test_custom_csrf_failure(self, client):
        response = client.get(reverse('users:csrf_failure'))
        assert response.status_code == 403

    def test_custom_bad_request(self, client):
        from nail_ecommerce_project.apps.users.views_frontend import custom_bad_request_view
        request = client.request().wsgi_request
        response = custom_bad_request_view(request, Exception("bad"))
        assert response.status_code == 400


class TestDeleteAccountView:
    @pytest.fixture
    def delete_user(self):
        return User.objects.create_user(
            username='deleteuser',
            email='del@x.com',
            password='delete123',
            full_name='Deletable User'
        )

    def test_account_deletion_success(self, client, delete_user):
        # Login
        login_success = client.login(username='deleteuser', password='delete123')
        assert login_success

        # Submit delete request
        response = client.post(reverse('users:delete_account'), follow=True)

        # Debug output
        print("📡 Response status code:", response.status_code)
        print("📡 Redirect chain:", response.redirect_chain)

        # Assertions
        assert response.redirect_chain[-1][0] == reverse('core:home')
        assert response.status_code == 200
        assert not User.objects.filter(username='deleteuser').exists()


class TestAdminUserListView:
    @pytest.fixture
    def admin_user(self):
        return User.objects.create_superuser(username='admin1', email='admin@example.com', password='adminpass')

    @pytest.fixture
    def normal_user(self):
        return User.objects.create_user(username='normal1', email='normal@example.com', password='userpass')

    def test_admin_can_view_user_list(self, client, admin_user, normal_user):
        client.login(username='admin1', password='adminpass')
        response = client.get(reverse('users:admin_user_list'))

        assert response.status_code == 200
        assert b'normal1' in response.content  # Only normal user should be listed
        assert b'admin1' not in response.content  # Superuser should not be listed

    def test_non_admin_cannot_access(self, client, normal_user):
        client.login(username='normal1', password='userpass')
        response = client.get(reverse('users:admin_user_list'))

        assert response.status_code == 403


class TestAdminUserDeleteView:
    @pytest.fixture
    def admin_user(self):
        return User.objects.create_superuser(username='admin2', email='admin2@example.com', password='adminpass')

    @pytest.fixture
    def deletable_user(self):
        return User.objects.create_user(username='delete_me', email='del@example.com', password='userpass')

    def test_admin_can_delete_user(self, client, admin_user, deletable_user):
        client.login(username='admin2', password='adminpass')
        delete_url = reverse('users:admin_user_delete', args=[deletable_user.id])
        response = client.post(delete_url)

        assert response.status_code == 302  # redirect after delete
        assert not User.objects.filter(username='delete_me').exists()

    def test_non_admin_cannot_delete_user(self, client, deletable_user):
        normal_user = User.objects.create_user(username='not_admin', email='user@example.com', password='pass123')
        client.login(username='not_admin', password='pass123')
        delete_url = reverse('users:admin_user_delete', args=[deletable_user.id])
        response = client.post(delete_url)

        assert response.status_code == 403
        assert User.objects.filter(username='delete_me').exists()
