from django import forms
from django.utils import timezone
from .models import Booking
from django.core.exceptions import ValidationError
from nail_ecommerce_project.apps.users.models import CustomerAddress


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['service', 'date', 'time_slot', 'number_of_customers', 'notes', 'is_home_service']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time_slot': forms.Select(),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'number_of_customers': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'is_home_service': forms.CheckboxInput(attrs={'class': 'ml-2'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields['notes'].required = False
        self.fields['is_home_service'].label = "Do you want a Home Visit?"
        self.fields['is_home_service'].required = False

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date < timezone.now().date():
            raise forms.ValidationError("Booking date cannot be in the past.")
        return date

    def clean_number_of_customers(self):
        number = self.cleaned_data.get('number_of_customers')
        if number < 1:
            raise forms.ValidationError("At least 1 customer is required.")
        if number > 5:
            raise forms.ValidationError("Maximum of 5 customers allowed for group booking.")
        return number

    def clean_is_home_service(self):
        is_home_service = self.cleaned_data.get('is_home_service')
        if is_home_service:
            user = getattr(self.request, 'user', None)
            if not user or not hasattr(user, 'address') or not user.address.is_complete:
                raise forms.ValidationError("Complete address required for home service.")
        return is_home_service

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time_slot = cleaned_data.get('time_slot')
        service = cleaned_data.get('service')
        is_home_service = cleaned_data.get('is_home_service')

        # Booking conflict check
        if date and time_slot and service:
            conflict = Booking.objects.filter(
                date=date,
                time_slot=time_slot,
                service=service,
            )
            if self.instance.pk:
                conflict = conflict.exclude(pk=self.instance.pk)
            if conflict.exists():
                raise ValidationError("This time slot for the selected service is already booked.")

        # Home address population
        if is_home_service:
            user = getattr(self.request, 'user', None)
            if not user or not hasattr(user, 'address'):
                raise ValidationError("You must have a saved address to request a home visit.")

            address = user.address
            if not address.is_complete:
                raise ValidationError("Your saved address is incomplete. Please update your profile.")

            full_address = f"{address.address_line1}, {address.address_line2}, "
            if address.landmark:
                full_address += f"Landmark: {address.landmark}, "
            full_address += f"{address.city}, {address.state} - {address.pincode}"

            # Only populate after validation passes
            self.instance.home_delivery_address = full_address

        return cleaned_data