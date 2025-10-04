from django.urls import path
from . import views_api

app_name = 'services_api'

urlpatterns = [
    path('', views_api.ActiveServiceListAPIView.as_view(), name='api_service_list'),
    path('<slug:slug>/', views_api.ServiceDetailAPIView.as_view(), name='api_service_detail'),
]
