from django.contrib.auth.forms import AuthenticationForm, UsernameField
from .models import CustomUser
from django import forms
from django.core.exceptions import ValidationError
from .models import CustomerAddress
from django.utils.translation import gettext_lazy as _
import re
from logs.logger import get_logger

logger = get_logger(__name__)


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500'
        })
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'full_name', 'phone_number')
        widgets = {
            'username': forms.TextInput(attrs={
                'autocomplete': 'username',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500'
            }),
            'email': forms.EmailInput(attrs={
                'autocomplete': 'email',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500'
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500'
            }),
            'phone_number': forms.TextInput(attrs={
                'type': 'tel',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500'
            }),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            logger.warning("Password mismatch during registration attempt.")
            raise forms.ValidationError("Passwords don’t match.")
        return p2

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email__iexact=email).exists():
            logger.warning(f"Duplicate email detected during registration: {email}")
            raise ValidationError("Email is already registered.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username__iexact=username).exists():
            logger.warning(f"Duplicate username detected during registration: {username}")
            raise ValidationError("Username is already taken.")
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            raise ValidationError("Username can only contain letters, numbers, and ./-/_ characters.")
        return username

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not re.match(r'^[6-9]\d{9}$', phone):
            raise ValidationError("Enter a valid 10-digit Indian mobile number.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.role = 'customer'
        if commit:
            user.save()
            logger.info(f"User created successfully: {user.username} (Role: {user.role})")
        return user


class UserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'phone_number')
        widgets = {
            'username': forms.TextInput(attrs={'readonly': True}),
        }


class UsernameAuthenticationForm(AuthenticationForm):
    """
    Custom AuthenticationForm with additional UI attributes
    and logic to block inactive users.
    """
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={
            "autofocus": True,
            "class": "form-control",
            "placeholder": "Enter your username"
        })
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "current-password",
            "class": "form-control",
            "placeholder": "Enter your password"
        }),
    )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                _("This account is inactive."),
                code='inactive',
            )


class CustomerAddressForm(forms.ModelForm):
    class Meta:
        model = CustomerAddress
        fields = [
            'address_line1',
            'address_line2',
            'landmark',
            'city',
            'pincode',
            'state',
            'use_for_home_service'
        ]
        labels = {
            'address_line1': "Flat or House No., Building, Apartment",
            'address_line2': "Area, Street, Sector, Village",
            'landmark': "Landmark (Optional)",
            'city': "Town or City",
            'pincode': "Pincode",
            'state': "State",
            'use_for_home_service': "Use this address for home delivery or service"
        }
        widgets = {
            'address_line1': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500',
                'placeholder': 'e.g. Flat 302, Rose Villa'
            }),
            'address_line2': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500',
                'placeholder': 'e.g. Sector 4, Shivaji Nagar'
            }),
            'landmark': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500',
                'placeholder': 'Near Domino\'s Pizza'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500'
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500',
                'placeholder': '6-digit PIN'
            }),
            'state': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-pink-500 focus:border-pink-500'
            }),
            'use_for_home_service': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-pink-600 border-gray-300 focus:ring-pink-500'
            }),
        }

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode')
        if not re.match(r'^\d{6}$', pincode):
            raise forms.ValidationError("Please enter a valid 6-digit PIN code.")
        return pincode
