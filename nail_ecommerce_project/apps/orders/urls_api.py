from django.urls import path
from . import views_api


app_name = 'orders_api'

urlpatterns = [
    path('create/', views_api.OrderCreateAPIView.as_view(), name='order_create'),
    path('list/', views_api.OrderListAPIView.as_view(), name='order_list'),
    path('<int:pk>/', views_api.OrderDetailAPIView.as_view(), name='order_detail'),
]
