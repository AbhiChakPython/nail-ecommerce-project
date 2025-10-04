from django.urls import path
from .views_api import (
    BookingListCreateAPIView,
    BookingDetailAPIView,
    AvailableSlotsAPIView,
    BookingStatusUpdateAPIView,
    BookingCancelAPIView,
)


app_name = "bookings_api"
urlpatterns = [
    path('', BookingListCreateAPIView.as_view(), name='api_booking_list_create'),
    path('<int:pk>/', BookingDetailAPIView.as_view(), name='api_booking_detail'),
    path('<int:pk>/status/', BookingStatusUpdateAPIView.as_view(), name='api_booking_status_update'),
    path('cancel/<int:pk>/', BookingCancelAPIView.as_view(), name='api_booking_cancel'),
    path('available_slots/', AvailableSlotsAPIView.as_view(), name='api_available_slots'),
]
