from django import forms
from .models import Order


class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'full_name', 'phone',
            'address_line1', 'address_line2',
            'city', 'postal_code', 'state'
        ]
        widgets = {
            'address_line2': forms.TextInput(attrs={'placeholder': 'Optional'}),
        }
        labels = {
            'full_name': 'Full Name',
            'address_line1': 'Address Line 1',
            'postal_code': 'Postal / ZIP Code',
        }


class BuyNowShippingForm(forms.Form):
    full_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=20)
    address_line1 = forms.CharField(max_length=255)
    address_line2 = forms.CharField(max_length=255, required=False)
    city = forms.CharField(max_length=100)
    postal_code = forms.CharField(max_length=20)
    state = forms.CharField(max_length=100)
    use_for_home_service = forms.BooleanField(
    required=False,
    initial=True,
    label="Use this address for home delivery or service"
)


class CartShippingForm(BuyNowShippingForm):
    """Same fields as BuyNowShippingForm, used for cart checkout."""
    pass
