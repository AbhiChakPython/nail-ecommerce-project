from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from nail_ecommerce_project.apps.bookings.utils import auto_assign_staff
from nail_ecommerce_project.apps.services.models import Service

TIME_SLOT_CHOICES = [
    ('08:00', '08:00 AM'),
    ('09:00', '09:00 AM'),
    ('10:00', '10:00 AM'),
    ('11:00', '11:00 AM'),
    ('12:00', '12:00 PM'),
    ('13:00', '01:00 PM'),
    ('14:00', '02:00 PM'),
    ('15:00', '03:00 PM'),
    ('16:00', '04:00 PM'),
    ('17:00', '05:00 PM'),
    ('18:00', '06:00 PM'),
    ('19:00', '07:00 PM'),
    ('20:00', '08:00 PM'),
]


class BookingStatus(models.TextChoices):
    CONFIRMATION_PENDING = 'CONFIRMATION_PENDING', 'Confirmation Pending'
    CONFIRMED_SERVICE = 'CONFIRMED_SERVICE', 'Confirmed Service'
    COMPLETED_SERVICE = 'COMPLETED_SERVICE', 'Completed Service'
    CANCELLED_SERVICE = 'CANCELLED_SERVICE', 'Cancelled Service'


class Booking(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    date = models.DateField()
    time_slot = models.CharField(max_length=5, choices=TIME_SLOT_CHOICES)
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'is_staff': True},
        related_name='assigned_bookings'
    )
    status = models.CharField(max_length=25, choices=BookingStatus.choices, default=BookingStatus.CONFIRMATION_PENDING)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    number_of_customers = models.PositiveIntegerField(
        default=1,
        help_text="Number of people for the booking (max 5)"
    )
    is_home_service = models.BooleanField(default=False, help_text="Check if the customer requested home visit")
    home_delivery_address = models.TextField(blank=True, null=True, help_text="Address for home service, if applicable")
    home_visit_fee = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=Decimal('250.00'),
        help_text="Fee for home service visit. Applied only if is_home_service is True."
    )

    # ➕ Razorpay payment tracking fields
    is_paid = models.BooleanField(default=False)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('date', 'time_slot', 'service', 'customer')
        ordering = ['-created_at']

    def get_final_price(self):
        base_price = self.service.price
        regular_discount = base_price * Decimal('0.05')
        discounted_unit_price = base_price - regular_discount
        customer_count = getattr(self, 'number_of_customers', 1)

        group_discount = Decimal('0.00')
        if 2 <= customer_count <= 5:
            group_discount = discounted_unit_price * customer_count * Decimal('0.05')

        total = discounted_unit_price * customer_count - group_discount

        # Add home visit fee if applicable
        if self.is_home_service:
            total += self.home_visit_fee

        return total.quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        if self.number_of_customers > 5:
            raise ValidationError("Maximum 5 customers allowed per booking.")
        if not self.staff:
            self.staff = auto_assign_staff()
        super().save(*args, **kwargs)

    def __str__(self):
        service_type = "Home" if self.is_home_service else "Salon"
        return f"{self.customer} - {self.service} ({service_type}) on {self.date} at {self.time_slot}"

    def get_price_breakdown(self):
        base = self.service.price
        reg_discount = base * Decimal('0.05')
        discounted_price = base - reg_discount
        count = self.number_of_customers

        group_discount = Decimal('0.00')
        if 2 <= count <= 5:
            group_discount = discounted_price * count * Decimal('0.05')

        home_fee = self.home_visit_fee if self.is_home_service else Decimal('0.00')

        return {
            'base_price': base,
            'regular_discount': reg_discount,
            'group_discount': group_discount,
            'home_visit_fee': home_fee,
            'total_price': self.get_final_price()
        }