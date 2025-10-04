from django.urls import path
from .views_api import (
    ProductListCreateAPIView,
    ProductRetrieveUpdateDestroyAPIView,
    ProductCategoryRetrieveUpdateDestroyAPIView,
    ProductCategoryListCreateAPIView,
)


app_name = "products_api"

urlpatterns = [
    # Products
    path('', ProductListCreateAPIView.as_view(), name='product-list-create'),
    path('<int:pk>/', ProductRetrieveUpdateDestroyAPIView.as_view(), name='product-detail'),

    # Categories (Read-only, no create/update/delete via API)
    path('categories/', ProductCategoryListCreateAPIView.as_view(), name='category-list'),
    path('categories/<int:pk>/', ProductCategoryRetrieveUpdateDestroyAPIView.as_view(), name='category-detail'),

]
