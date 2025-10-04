from unittest.mock import patch
import pytest
from django.db.models import QuerySet
from nail_ecommerce_project.apps.users.utils import get_recent_bookings, get_recent_orders, send_welcome_email
from nail_ecommerce_project.apps.users.models import CustomUser
from django.utils import timezone
from datetime import timedelta

pytestmark = pytest.mark.django_db


class TestUserUtils:

    def test_get_recent_bookings_returns_queryset(self):
        user = CustomUser.objects.create_user(username="testuser", email="x@test.com", password="pass123")

        from nail_ecommerce_project.apps.services.models import Service
        from nail_ecommerce_project.apps.bookings.models import Booking

        service = Service.objects.create(title="Sample Service", duration_minutes=60, price=100)

        for i in range(3):
            Booking.objects.create(
                customer=user,
                service=service,
                date=timezone.now().date() - timedelta(days=i),
                time_slot="10:00",
                number_of_customers=1
            )

        result = get_recent_bookings(user)

        assert result.count() == 3
        assert result[0].customer == user
        assert result[0].service == service

    def test_get_recent_orders_returns_queryset_with_items(self):
        from nail_ecommerce_project.apps.products.models import Product, ProductVariant
        from nail_ecommerce_project.apps.orders.models import Order, OrderItem
        from nail_ecommerce_project.apps.users.models import CustomUser

        user = CustomUser.objects.create_user(
            username='orderuser',
            email='order@test.com',
            password='pass123'
        )

        product = Product.objects.create(name="Lipstick")
        variant = ProductVariant.objects.create(
            product=product,
            size="M",
            color="Red",
            price=250.00,
            stock_quantity=10
        )

        for i in range(2):
            order = Order.objects.create(
                user=user,
                full_name='Test User',
                phone='1234567890',
                address_line1='123 Main St',
                address_line2='Apt 4B',
                city='Testville',
                postal_code='123456'
            )
            OrderItem.objects.create(order=order, product_variant=variant, quantity=2)

        result = get_recent_orders(user)

        assert isinstance(result, QuerySet)
        assert result.count() == 2
        assert all(order.items.exists() for order in result)

    @patch("nail_ecommerce_project.apps.users.utils.EmailMultiAlternatives")
    def test_send_welcome_email_sends_email(self, mock_email_class):
        # Arrange: create test user
        user = CustomUser.objects.create_user(
            username='emailuser',
            email='welcome@test.com',
            password='pass123',
            full_name='Welcome User'
        )

        # Act: call utility
        send_welcome_email(user)

        # Assert: email was prepared and sent
        assert mock_email_class.called is True
        instance = mock_email_class.return_value
        assert instance.attach_alternative.called is True
        assert instance.send.called is True