from django.urls import path
from .views_frontend import (BookingSuccessView, BookingFailedView, BookingCheckoutView, \
                             BookingPaymentCallbackView, BookingPriceEstimateView, BookingCreateView, BookingListView,
                             BookingDetailView,
                             BookingUpdateView, AvailableSlotsView, RetryBookingPaymentView, CancelBookingView)


app_name = "bookings"
urlpatterns = [
    path('', BookingListView.as_view(), name='booking_list_create'),
    path('new/', BookingCreateView.as_view(), name='booking_create'),
    path('<int:pk>/', BookingDetailView.as_view(), name='booking_detail'),
    path('<int:pk>/edit/', BookingUpdateView.as_view(), name='booking_update'),
    path("available_slots/", AvailableSlotsView.as_view(), name="available_slots"),

    path('price_estimate/', BookingPriceEstimateView.as_view(), name='price_estimate'),
    path('checkout/<int:booking_id>/', BookingCheckoutView.as_view(), name='checkout'),
    path('payment/callback/<int:booking_id>/', BookingPaymentCallbackView.as_view(), name='payment_callback'),
    path('success/<int:booking_id>/', BookingSuccessView.as_view(), name='success'),
    path('failed/<int:booking_id>/', BookingFailedView.as_view(), name='failed'),
    path('<int:booking_id>/retry/', RetryBookingPaymentView.as_view(), name='retry_payment'),
    path('<int:booking_id>/cancel/', CancelBookingView.as_view(), name='cancel_booking'),
]
