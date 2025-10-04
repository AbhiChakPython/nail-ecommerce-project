import pytest
from datetime import timedelta
from django.utils import timezone
from nail_ecommerce_project.apps.bookings.forms import BookingForm
from nail_ecommerce_project.apps.bookings.models import Booking


@pytest.mark.django_db
def test_booking_form_valid_data(customer_user, service):
    form_data = {
        'service': service.id,
        'date': timezone.now().date() + timedelta(days=1),
        'time_slot': '10:00',
        'number_of_customers': 2,
        'notes': 'Please be on time',
        'is_home_service': False
    }
    form = BookingForm(data=form_data)
    assert form.is_valid()


@pytest.mark.django_db
def test_booking_form_rejects_past_date(service):
    form_data = {
        'service': service.id,
        'date': timezone.now().date() - timedelta(days=1),
        'time_slot': '10:00',
        'number_of_customers': 1,
        'is_home_service': False
    }
    form = BookingForm(data=form_data)
    assert not form.is_valid()
    assert 'date' in form.errors


@pytest.mark.django_db
def test_booking_form_rejects_zero_customers(service):
    form_data = {
        'service': service.id,
        'date': timezone.now().date() + timedelta(days=1),
        'time_slot': '11:00',
        'number_of_customers': 0,
        'is_home_service': False
    }
    form = BookingForm(data=form_data)
    assert not form.is_valid()
    assert 'number_of_customers' in form.errors


@pytest.mark.django_db
def test_booking_form_rejects_excess_customers(service):
    form_data = {
        'service': service.id,
        'date': timezone.now().date() + timedelta(days=1),
        'time_slot': '12:00',
        'number_of_customers': 6,
        'is_home_service': False
    }
    form = BookingForm(data=form_data)
    assert not form.is_valid()
    assert 'number_of_customers' in form.errors


@pytest.mark.django_db
def test_booking_form_detects_time_slot_conflict(customer_user, service):
    # Create existing booking with same slot
    Booking.objects.create(
        customer=customer_user,
        service=service,
        date=timezone.now().date() + timedelta(days=1),
        time_slot='13:00',
        number_of_customers=2
    )

    # Submit form with same details
    form_data = {
        'service': service.id,
        'date': timezone.now().date() + timedelta(days=1),
        'time_slot': '13:00',
        'number_of_customers': 2,
        'is_home_service': False
    }
    form = BookingForm(data=form_data)
    assert not form.is_valid()
    assert '__all__' in form.errors  # form-level error


@pytest.mark.django_db
def test_booking_form_optional_fields_work(service):
    form_data = {
        'service': service.id,
        'date': timezone.now().date() + timedelta(days=2),
        'time_slot': '14:00',
        'number_of_customers': 1,
        # No notes, is_home_service is False by default
    }
    form = BookingForm(data=form_data)
    assert form.is_valid()
