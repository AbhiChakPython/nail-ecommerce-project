from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.views.decorators.csrf import requires_csrf_token
from django.views.generic import TemplateView, FormView, ListView
from django.contrib.auth.views import LogoutView as AuthLogoutView, PasswordChangeView, \
    LoginView
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.generic.edit import FormMixin, DeleteView
from .forms import UserCreationForm, UserChangeForm, UsernameAuthenticationForm, CustomerAddressForm
from .models import CustomerAddress
from .utils import get_recent_bookings, get_recent_orders, send_welcome_email
from logs.logger import get_logger
logger = get_logger(__name__)

User = get_user_model()

class ProfileView(LoginRequiredMixin, FormMixin, TemplateView):
    template_name = 'users/profile.html'
    form_class = UserChangeForm
    success_url = reverse_lazy('users:profile')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        # 👇 Bind address form
        try:
            address_instance = request.user.address
        except CustomerAddress.DoesNotExist:
            address_instance = None
        address_form = CustomerAddressForm(request.POST, instance=address_instance)

        if form.is_valid() and address_form.is_valid():
            form.save()
            address = address_form.save(commit=False)
            address.user = request.user
            address.save()

            logger.info(f"Profile and address updated for user: {request.user.username}")
            messages.success(request, "Your profile has been updated successfully.")
            return self.form_valid(form)
        else:
            logger.warning(f"Profile update failed for user: {request.user.username} | "
                           f"Form Errors: {form.errors.as_json()} | Address Errors: {address_form.errors.as_json()}")

            context = self.get_context_data()
            context['form'] = form
            context['address_form'] = address_form
            return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['recent_bookings'] = get_recent_bookings(self.request.user)
        context['recent_orders'] = get_recent_orders(self.request.user)

        # ✅ Prefill CustomerAddressForm
        try:
            address_instance = self.request.user.address
        except CustomerAddress.DoesNotExist:
            address_instance = None
        context['address_form'] = CustomerAddressForm(instance=address_instance)

        return context

    @login_required
    def update_address_view(request):
        user = request.user

        # Reuse or create the address instance
        if hasattr(user, 'address'):
            instance = user.address
        else:
            instance = CustomerAddress(user=user)

        if request.method == 'POST':
            form = CustomerAddressForm(request.POST, instance=instance)
            if form.is_valid():
                form.save()
                messages.success(request, "✅ Address updated successfully.")
                return redirect('users:profile')  # 🔁 Adjust this URL name as needed
            else:
                messages.error(request, "❌ Please correct the errors below.")
        else:
            form = CustomerAddressForm(instance=instance)

        return render(request, "users/address_update.html", {"form": form})


class RegisterView(FormView):
    template_name = 'users/register.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('users:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['address_form'] = kwargs.get('address_form') or CustomerAddressForm()
        return context

    def post(self, request, *args, **kwargs):
        user_form = self.get_form()
        address_form = CustomerAddressForm(request.POST)

        if user_form.is_valid() and address_form.is_valid():
            try:
                with transaction.atomic():
                    user = user_form.save()
                    address = address_form.save(commit=False)
                    address.user = user
                    address.save()

                    send_welcome_email(user)
                    logger.info(f"New user registered: {user.username} with address.")
                    messages.success(request, "Registration successful! Please log in.")
                    return redirect(self.success_url)
            except Exception as e:
                logger.exception("Registration failed during DB transaction.")
                messages.error(request, "An error occurred. Please try again.")
        else:
            logger.warning(f"Invalid registration form submitted. Errors: "
                           f"{user_form.errors.as_json()} | {address_form.errors.as_json()}")

        # Re-render with bound forms
        return self.render_to_response(self.get_context_data(form=user_form, address_form=address_form))


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = UsernameAuthenticationForm

    def get_success_url(self):
        print("✅ Using CustomLoginView.get_success_url()")
        return reverse_lazy('core:home')

    def form_invalid(self, form):
        logger.warning(f"Login failed | Errors: {form.errors.as_json()}")
        return super().form_invalid(form)

    def form_valid(self, form):
        user = form.get_user()
        remember = self.request.POST.get('remember_me', None)
        if remember != 'on':
            self.request.session.set_expiry(0)  # expires on browser close
        else:
            self.request.session.set_expiry(1209600)  # 2 weeks

        logger.info(f"User logged in: {user.username}")
        print("Login success for:", user.username)
        return super().form_valid(form)


class CustomLogoutView(AuthLogoutView):
    next_page = reverse_lazy('users:login')

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"User logged out: {request.user} at {now()}")
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'users/change_password.html'
    success_url = reverse_lazy('users:login')


class DeleteAccountView(LoginRequiredMixin, DeleteView):
    model = User
    template_name = 'users/delete_account.html'
    success_url = reverse_lazy('core:home')
    context_object_name = 'user_to_delete'

    def get_object(self, queryset=None):
        return self.request.user

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        logger.info(f"User {user.username} requested account deletion.")
        user.delete()
        return render(request, self.template_name, {
            'account_deleted': True
        })

class AdminUserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = User
    template_name = 'users/admin_user_list.html'
    context_object_name = 'users'

    def test_func(self):
        return self.request.user.is_superuser

    def get_queryset(self):
        return User.objects.filter(is_superuser=False)

class AdminUserDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = User
    template_name = 'users/admin_user_confirm_delete.html'
    success_url = reverse_lazy('users:admin_user_list')
    context_object_name = 'user_to_delete'

    def test_func(self):
        return self.request.user.is_superuser


def custom_bad_request_view(request, exception):
    return render(request, 'users/400.html', status=400)

def custom_unauthorized_view(request, exception=None):
    return render(request, 'users/401.html', status=401)

@requires_csrf_token
def custom_csrf_failure_view(request, reason=""):
    return render(request, 'users/csrf_error.html', status=403, context={'reason': reason})

def custom_permission_denied_view(request, exception=None):
    return render(request, 'users/403.html', status=403)

def custom_page_not_found_view(request, exception):
    return render(request, 'users/404.html', status=404)

def custom_server_error_view(request):
    return render(request, 'users/500.html', status=500)
