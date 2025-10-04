from django.conf import settings
from django.contrib.auth import get_user_model
from random import choice
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from decimal import Decimal
from nail_ecommerce_project.apps.services.models import Service
from logs.logger import get_logger
logger = get_logger(__name__)

User = get_user_model()


def auto_assign_staff():
    staff_users = User.objects.filter(is_staff=True, is_active=True)
    if staff_users.exists():
        return choice(staff_users)  # Simple random choice
    return None  # fallback if no staff available


def send_booking_placed_email(booking):
    subject = f"Booking #{booking.id} Received Successfully"
    to_email = booking.customer.email
    context = {'booking': booking}

    text_content = render_to_string('bookings/emails/booking_placed.txt', context)
    html_content = render_to_string('bookings/emails/booking_placed.html', context)

    try:
        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Booking placed email sent to {to_email} for booking #{booking.id}")
    except Exception as e:
        logger.error(f"Failed to send booking placed email to {to_email}: {e}")


def send_booking_confirmed_email(booking):
    subject = f"Booking #{booking.id} Confirmed"
    to_email = booking.customer.email
    context = {'booking': booking}

    text_content = render_to_string('bookings/emails/booking_confirmed.txt', context)
    html_content = render_to_string('bookings/emails/booking_confirmed.html', context)

    try:
        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Booking confirmation email sent to {to_email} for booking #{booking.id}")
    except Exception as e:
        logger.error(f"Failed to send booking confirmation email to {to_email}: {e}")


def calculate_booking_price(service_id, number_of_customers=1, is_home_service=False):
    try:
        service = Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        return {
            'base_price': Decimal('0.00'),
            'regular_discount': Decimal('0.00'),
            'group_discount': Decimal('0.00'),
            'home_fee': Decimal('0.00'),
            'final_price': Decimal('0.00')
        }

    base_price = service.price
    regular_discount = base_price * Decimal('0.05')
    discounted_price = base_price - regular_discount

    group_discount = Decimal('0.00')
    if 2 <= number_of_customers <= 5:
        group_discount = discounted_price * number_of_customers * Decimal('0.05')

    home_fee = Decimal('250.00') if is_home_service else Decimal('0.00')

    final_price = (discounted_price * number_of_customers) - group_discount + home_fee

    return {
        'base_price': base_price,
        'regular_discount': regular_discount,
        'group_discount': group_discount,
        'home_fee': home_fee,
        'final_price': final_price
    }
