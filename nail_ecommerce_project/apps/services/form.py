from django import forms
from .models import Service
from .models import ServiceGalleryImage


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            'title',
            'short_description',
            'duration_minutes',
            'price',
            'featured_image',
            'is_active',
        ]
        widgets = {
            'short_description': forms.Textarea(attrs={'rows': 3}),
        }
        exclude = ['slug']


class ServiceGalleryImageForm(forms.ModelForm):
    class Meta:
        model = ServiceGalleryImage
        fields = ['image_file', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'Optional caption'}),
        }