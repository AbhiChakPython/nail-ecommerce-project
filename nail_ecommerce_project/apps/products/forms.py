from django import forms
from django.forms import inlineformset_factory

from .models import Product, ProductVariant, ProductGalleryImage


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'thumbnail', 'is_available',
            'categories', 'discount_percent', 'lto_discount_percent',
            'lto_start_date', 'lto_end_date',
        ]

ProductVariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    fields=('color', 'size', 'price', 'stock_quantity'),
    extra=1,
    can_delete=False
)

class ProductGalleryImageForm(forms.ModelForm):
    class Meta:
        model = ProductGalleryImage
        fields = ['image']