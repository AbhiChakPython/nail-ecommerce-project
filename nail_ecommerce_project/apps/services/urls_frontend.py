from django.urls import path
from .views_frontend import ServiceListView, ServiceDetailView, ServiceCreateView, ServiceUpdateView, ServiceDeleteView, \
    ManageServiceGalleryView
from ..bookings.views_frontend import BookingPaymentCallbackView

app_name = 'services'
urlpatterns = [
    path('', ServiceListView.as_view(), name='service_list'),

    # Admin views (Superuser-only)
    path('add/', ServiceCreateView.as_view(), name='service_create'),
    path('<slug:slug>/edit/', ServiceUpdateView.as_view(), name='service_update'),
    path('<slug:slug>/delete/', ServiceDeleteView.as_view(), name='service_delete'),
    path('<slug:slug>/gallery/', ManageServiceGalleryView.as_view(), name='service_manage_gallery'),

    path('<slug:slug>/', ServiceDetailView.as_view(), name='service_detail'),
]
