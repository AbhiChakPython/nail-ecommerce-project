from nail_ecommerce_project.apps.users.models import CustomUser
from nail_ecommerce_project.apps.services.models import Service
import pytest
from datetime import date, timedelta
from nail_ecommerce_project.apps.bookings.models import Booking, TIME_SLOT_CHOICES

@pytest.fixture
def customer_user(db):
    return CustomUser.objects.create_user(username='cust1', email='cust1@example.com', password='pass', role='customer')

@pytest.fixture
def service(db):
    return Service.objects.create(title='Facial', price=1000)


@pytest.fixture
def staff_user(db):
    return CustomUser.objects.create_user(
        username='staff1',
        email='staff@example.com',
        password='pass',
        is_staff=True
    )

@pytest.fixture
def client_logged_customer(client, customer_user):
    client.login(username='cust1', password='pass')
    return client

@pytest.fixture
def other_user(db):
    return CustomUser.objects.create_user(username='other1', email='other1@example.com', password='pass', role='customer')

@pytest.fixture
def client_logged_other_customer(client, other_user):
    client.login(username='other_user', password='pass')
    return client

@pytest.fixture
def booking(customer_user, service):
    return Booking.objects.create(
        customer=customer_user,
        service=service,
        date=date.today() + timedelta(days=1),
        time_slot=TIME_SLOT_CHOICES[0][0],
        number_of_customers=1
    )

@pytest.fixture
def other_user_booking(other_user, service):
    return Booking.objects.create(
        customer=other_user,
        service=service,
        date=date.today() + timedelta(days=2),
        time_slot=TIME_SLOT_CHOICES[1][0],
        number_of_customers=1
    )