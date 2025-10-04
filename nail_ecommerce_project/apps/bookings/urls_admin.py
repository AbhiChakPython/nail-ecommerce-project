from django.urls import path
from .views_admin import AdminBookingListView, UpdateBookingStatusView

app_name = 'bookings_admin'

urlpatterns = [
    path('', AdminBookingListView.as_view(), name='bookings_list'),
    path('<int:booking_id>/update-status/', UpdateBookingStatusView.as_view(), name='update_booking_status'),
]
