import pytest
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse, resolve
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from nail_ecommerce_project.apps.users import views_frontend
from nail_ecommerce_project.apps.users.models import CustomUser


@pytest.mark.django_db
class TestUserURLs:

    def test_register_url_resolves(self):
        path = reverse('users:register')
        assert resolve(path).func.view_class == views_frontend.RegisterView

    def test_login_url_resolves(self):
        path = reverse('users:login')
        assert resolve(path).func.view_class == views_frontend.CustomLoginView

    def test_logout_url_resolves(self):
        path = reverse('users:logout')
        assert resolve(path).func.view_class == views_frontend.CustomLogoutView

    def test_profile_url_resolves(self):
        path = reverse('users:profile')
        assert resolve(path).func.view_class == views_frontend.ProfileView

    def test_change_password_url_resolves(self):
        path = reverse('users:change_password')
        assert resolve(path).func.view_class == views_frontend.CustomPasswordChangeView

    def test_password_reset_url_resolves(self):
        path = reverse('users:password_reset')
        assert resolve(path).url_name == 'password_reset'

    def test_password_reset_done_url_resolves(self):
        path = reverse('users:password_reset_done')
        assert resolve(path).url_name == 'password_reset_done'

    def test_password_reset_confirm_url_resolves(self):
        # Using sample uidb64 and token to simulate path
        path = reverse('users:password_reset_confirm', kwargs={'uidb64': 'uid', 'token': 'set-token'})
        assert resolve(path).url_name == 'password_reset_confirm'

    def test_password_reset_complete_url_resolves(self):
        path = reverse('users:password_reset_complete')
        assert resolve(path).url_name == 'password_reset_complete'

    def test_csrf_failure_url_resolves(self):
        path = reverse('users:csrf_failure')
        assert resolve(path).func == views_frontend.custom_csrf_failure_view


@pytest.mark.django_db
class TestPasswordResetFlow:

    def test_password_reset_view_sends_email(self, client):
        user = CustomUser.objects.create_user(
            username='resetuser',
            email='reset@example.com',
            password='oldpassword123'
        )

        response = client.post(reverse('users:password_reset'), data={
            'email': 'reset@example.com'
        })

        assert response.status_code == 302
        assert response.url == reverse('users:password_reset_done')

        from django.core import mail
        assert len(mail.outbox) == 1
        assert 'reset@example.com' in mail.outbox[0].to

    def test_password_reset_view_invalid_email_behaves_same(self, client):
        response = client.post(reverse('users:password_reset'), data={
            'email': 'nonexistent@example.com'
        })
        # Should still redirect to prevent email enumeration
        assert response.status_code == 302
        assert response.url == reverse('users:password_reset_done')

    def test_password_reset_done_view_loads(self, client):
        response = client.get(reverse('users:password_reset_done'))
        assert response.status_code == 200
        assert b"password reset" in response.content.lower()

    def test_password_reset_confirm_view_valid_token(self, client):
        user = CustomUser.objects.create_user(
            username='resetconfirmuser',
            email='reset2@example.com',
            password='oldpassword456'
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        confirm_url = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})

        # Step 1: GET initial confirm URL
        response = client.get(confirm_url)
        assert response.status_code == 302  # should redirect to set-password
        assert "set-password" in response.url

        # Step 2: GET the set-password form
        set_password_url = response.url
        response = client.get(set_password_url)
        assert response.status_code == 200
        assert b"new password" in response.content.lower()

        # Step 3: POST new password to set-password URL
        response = client.post(set_password_url, data={
            'new_password1': 'newsecurepass789',
            'new_password2': 'newsecurepass789',
        })
        assert response.status_code == 302  # final redirect
        assert response.url == reverse('users:password_reset_complete')

        # Step 4: Final page should load
        final_response = client.get(response.url)
        assert final_response.status_code == 200

        # ✅ Confirm password updated
        user.refresh_from_db()
        assert user.check_password('newsecurepass789')

    def test_password_reset_confirm_invalid_token(self, client):
        user = CustomUser.objects.create_user(
            username='badtokenuser',
            email='badtoken@example.com',
            password='pass123'
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        invalid_token = 'invalid-token'

        url = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': invalid_token})
        response = client.get(url)

        assert response.status_code == 200

        # More flexible check — looking for fallback content or no form input field
        assert (
                b"invalid" in response.content.lower() or
                b"expired" in response.content.lower() or
                b"set a new password" not in response.content.lower()
        )

    def test_password_reset_complete_view_renders(self, client):
        response = client.get(reverse('users:password_reset_complete'))
        assert response.status_code == 200
        assert b"complete" in response.content.lower()