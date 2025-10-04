import pytest
from django.urls import reverse
from django.utils import timezone
from nail_ecommerce_project.apps.bookings.models import Booking, TIME_SLOT_CHOICES
from nail_ecommerce_project.apps.bookings.models import BookingStatus


@pytest.mark.django_db
def test_booking_create_view_get_authenticated(client_logged_customer):
    url = reverse('bookings:booking_create')
    response = client_logged_customer.get(url)
    assert response.status_code == 200
    assert b"Booking Form" in response.content or b"date" in response.content


@pytest.mark.django_db
def test_booking_create_view_post_valid(client_logged_customer, service, customer_user):
    url = reverse('bookings:booking_create')
    data = {
        "service": service.id,
        "date": timezone.now().date() + timezone.timedelta(days=1),
        "time_slot": TIME_SLOT_CHOICES[0][0],
        "number_of_customers": 2,
        "notes": "Group booking",
        "is_home_service": False,
    }
    response = client_logged_customer.post(url, data)
    # should redirect to checkout
    assert response.status_code == 302
    assert Booking.objects.filter(customer=customer_user).exists()


@pytest.mark.django_db
def test_booking_create_view_post_invalid_date(client_logged_customer):
    url = reverse('bookings:booking_create')
    data = {
        "service": 1,  # assuming existing service ID
        "date": timezone.now().date() - timezone.timedelta(days=1),  # past date
        "time_slot": TIME_SLOT_CHOICES[0][0],
        "number_of_customers": 1,
    }
    response = client_logged_customer.post(url, data)
    assert response.status_code == 200
    assert b"Booking date cannot be in the past" in response.content


@pytest.mark.django_db
def test_booking_list_view_shows_only_customer_bookings(client_logged_customer, customer_user, other_user, service):
    # Booking for current customer
    Booking.objects.create(
        customer=customer_user,
        service=service,
        date=timezone.now().date() + timezone.timedelta(days=1),
        time_slot=TIME_SLOT_CHOICES[1][0]
    )
    # Booking for someone else
    Booking.objects.create(
        customer=other_user,
        service=service,
        date=timezone.now().date() + timezone.timedelta(days=2),
        time_slot=TIME_SLOT_CHOICES[2][0]
    )
    url = reverse('bookings:booking_list_create')
    response = client_logged_customer.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "Group booking" not in content
    assert str(other_user.email) not in content


@pytest.mark.django_db
def test_booking_detail_view_valid(client_logged_customer, booking):
    url = reverse('bookings:booking_detail', args=[booking.id])
    response = client_logged_customer.get(url)
    assert response.status_code == 200
    assert booking.service.title.encode() in response.content


@pytest.mark.django_db
def test_booking_detail_view_other_user_forbidden(client_logged_customer, other_user_booking):
    url = reverse('bookings:booking_detail', args=[other_user_booking.id])
    response = client_logged_customer.get(url)
    assert response.status_code == 404 or response.status_code == 403


@pytest.mark.django_db
def test_booking_checkout_view_allows_owner(client_logged_customer, booking):
    response = client_logged_customer.get(
        reverse('bookings:checkout', kwargs={'booking_id': booking.id})
    )
    assert response.status_code == 200
    assert b'Razorpay' in response.content  # or any text confirming Razorpay key rendered


@pytest.mark.django_db
def test_booking_checkout_view_blocks_non_owner(client_logged_other_customer, booking):
    url = reverse('bookings:checkout', kwargs={'booking_id': booking.id})
    response = client_logged_other_customer.get(url)

    # Ensure the user is redirected (unauthorized access)
    assert response.status_code == 302
    assert response.url.startswith('/users/login/')


@pytest.mark.django_db
def test_booking_success_view_for_valid_owner(client_logged_customer, booking):
    response = client_logged_customer.get(
        reverse('bookings:success', kwargs={'booking_id': booking.id})
    )
    assert response.status_code == 200
    assert b'Booking' in response.content  # or some success text


@pytest.mark.django_db
def test_booking_failed_view_for_valid_owner(client_logged_customer, booking):
    response = client_logged_customer.get(
        reverse('bookings:failed', kwargs={'booking_id': booking.id})
    )
    assert response.status_code == 200
    assert b'booking' in response.content.lower()



@pytest.mark.django_db
def test_booking_update_view_allows_admin_access(client, staff_user, booking):
    client.login(username=staff_user.username, password='pass')
    url = reverse('bookings:booking_update', kwargs={'pk': booking.pk})
    response = client.get(url)

    assert response.status_code == 200
    assert b'Update' in response.content or b'Submit' in response.content  # flexible match

@pytest.mark.django_db
def test_booking_update_view_denies_non_admin_access(client, customer_user, booking):
    client.login(username=customer_user.username, password='pass')
    url = reverse('bookings:booking_update', kwargs={'pk': booking.pk})
    response = client.get(url)

    assert response.status_code == 403  # Forbidden

@pytest.mark.django_db
def test_booking_update_view_allows_admin(client, staff_user, booking):
    client.login(username=staff_user.username, password='pass')
    url = reverse('bookings:booking_update', kwargs={'pk': booking.pk})
    response = client.get(url)

    assert response.status_code == 200
    assert b'Status' in response.content
    assert b'Staff' in response.content


@pytest.mark.django_db
def test_booking_update_view_post_updates_status_and_staff(client, staff_user, booking):
    client.login(username=staff_user.username, password='pass')
    url = reverse('bookings:booking_update', kwargs={'pk': booking.pk})

    response = client.post(url, {
        'status': BookingStatus.CONFIRMED_SERVICE,
        'staff': staff_user.pk,
        'notes': 'Updated by admin',
    })

    assert response.status_code == 302  # Redirect on success
    booking.refresh_from_db()
    assert booking.status == BookingStatus.CONFIRMED_SERVICE
    assert booking.staff == staff_user
    assert booking.notes == 'Updated by admin'
