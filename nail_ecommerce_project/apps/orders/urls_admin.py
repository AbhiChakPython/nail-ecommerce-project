from django.urls import path
from .views_admin import AdminOrderListView, UpdateOrderStatusView, ManageInventoryView

app_name = 'orders_admin'

urlpatterns = [
    path('', AdminOrderListView.as_view(), name='order_list'),
    path('<int:order_id>/update-status/', UpdateOrderStatusView.as_view(), name='update_order_status'),
    path('manage-inventory/', ManageInventoryView.as_view(), name='manage_inventory'),

]
