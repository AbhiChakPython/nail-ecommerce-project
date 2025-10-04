from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Booking
from nail_ecommerce_project.apps.services.serializers import ServiceSerializer


User = get_user_model()

class BookingSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Booking._meta.get_field('service').remote_field.model.objects.all(),
        source='service',
        write_only=True
    )
    customer = serializers.StringRelatedField(read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    staff_email = serializers.EmailField(source='staff.email', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'service', 'service_id', 'number_of_customers', 'customer_email', 'is_home_service',
            'date', 'time_slot', 'status', 'notes', 'created_at', 'staff_email',
        ]
        read_only_fields = ['id', 'customer', 'status', 'created_at', 'customer_email', 'staff_email']
