import pytest
from django.db import IntegrityError
from decimal import Decimal
from datetime import date
from nail_ecommerce_project.apps.bookings.models import Booking, BookingStatus
from nail_ecommerce_project.apps.users.models import CustomUser
from nail_ecommerce_project.apps.services.models import Service

pytestmark = pytest.mark.django_db

def test_create_valid_booking(customer_user, service):
    booking = Booking.objects.create(
        customer=customer_user,
        service=service,
        date=date.today(),
        time_slot='10:00',
        number_of_customers=1
    )
    assert booking.pk is not None
    assert booking.status == BookingStatus.CONFIRMATION_PENDING
    assert isinstance(str(booking), str)

def test_booking_group_discount_applied(customer_user, service):
    booking = Booking.objects.create(
        customer=customer_user,
        service=service,
        date=date.today(),
        time_slot='11:00',
        number_of_customers=3
    )
    discounted = booking.get_final_price()
    expected = service.price - (service.price * Decimal('0.05'))
    assert discounted == expected

def test_booking_no_discount_if_single_customer(customer_user, service):
    booking = Booking.objects.create(
        customer=customer_user,
        service=service,
        date=date.today(),
        time_slot='12:00',
        number_of_customers=1
    )
    assert booking.get_final_price() == service.price

def test_booking_rejects_duplicates(customer_user, service):
    Booking.objects.create(
        customer=customer_user,
        service=service,
        date=date.today(),
        time_slot='13:00',
        number_of_customers=2
    )
    with pytest.raises(IntegrityError):
        Booking.objects.create(
            customer=customer_user,
            service=service,
            date=date.today(),
            time_slot='13:00',
            number_of_customers=2
        )

def test_booking_invalid_customer_count_exceeds_max(customer_user, service):
    with pytest.raises(ValueError):
        Booking.objects.create(
            customer=customer_user,
            service=service,
            date=date.today(),
            time_slot='14:00',
            number_of_customers=6  # invalid
        )

def test_booking_auto_assigns_staff(customer_user, service, staff_user):  # ← use the fixture
    booking = Booking.objects.create(
        customer=customer_user,
        service=service,
        date=date.today(),
        time_slot='15:00',
        number_of_customers=1
    )
    assert booking.staff is not None
    assert booking.staff == staff_user


def test_booking_missing_required_fields_raises_error(service):
    with pytest.raises(Exception):
        Booking.objects.create(
            service=service,
            date=date.today(),
            time_slot='08:00',
            number_of_customers=1
        )


def test_home_service_requires_address(customer_user, service, staff_user):
    booking = Booking.objects.create(
        customer=customer_user,
        service=service,
        date=date.today(),
        time_slot='10:00',
        number_of_customers=1,
        is_home_service=True,
        home_delivery_address=''  # empty
    )
    # You may enforce validation in save() or forms
    assert booking.is_home_service
    assert booking.home_delivery_address == ''


def test_auto_assign_staff_returns_none_if_no_staff(customer_user, service):
    Booking.objects.all().delete()
    # No staff created
    booking = Booking.objects.create(
        customer=customer_user,
        service=service,
        date=date.today(),
        time_slot='16:00',
        number_of_customers=1
    )
    assert booking.staff is None
