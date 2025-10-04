from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_recent_bookings(user, limit=5):
    try:
        from nail_ecommerce_project.apps.bookings.models import Booking
    except ImportError:
        return []

    return Booking.objects.filter(customer=user).order_by('-date')[:limit]


def get_recent_orders(user, limit=5):
    try:
        from nail_ecommerce_project.apps.orders.models import Order
    except ImportError:
        return []

    return Order.objects.filter(user=user).order_by('-created_at')[:limit]


def send_welcome_email(user):
    subject = "Welcome to Rupa's Nails Xtension Hub!"
    to_email = user.email
    context = {'user': user}

    text_content = render_to_string('users/emails/welcome.txt', context)
    html_content = render_to_string('users/emails/welcome.html', context)

    try:
        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Welcome email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {to_email}: {e}")
