from rest_framework import serializers
from .models import Service, ServiceGalleryImage


class ServiceGalleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceGalleryImage
        fields = ['id', 'image_file', 'caption']

class ServiceSerializer(serializers.ModelSerializer):
    gallery_images = ServiceGalleryImageSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            'id',
            'title',
            'slug',
            'short_description',
            'duration_minutes',
            'price',
            'featured_image',
            'is_active',
            'gallery_images',
        ]
        read_only_fields = ['slug']
