from django.urls import path
from .views_frontend import (
    ProductListView,
    ProductDetailView,
    ProductCreateView,
    ProductUpdateView,
    ProductDeleteView, ManageProductGalleryView, DeleteGalleryImageView, ProductVariantManageView
)


app_name = "products"

urlpatterns = [
    path('create/', ProductCreateView.as_view(), name='product_create'),
    path('<slug:slug>/edit/', ProductUpdateView.as_view(), name='product_update'),
    path('<slug:slug>/manage-variants/', ProductVariantManageView.as_view(), name='manage_variants'),
    path('<slug:slug>/delete/', ProductDeleteView.as_view(), name='product_delete'),
    path('<slug:slug>/gallery/', ManageProductGalleryView.as_view(), name='manage_gallery'),
    path('gallery/<int:pk>/delete/', DeleteGalleryImageView.as_view(), name='delete_gallery_image'),
    path('<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
    path('', ProductListView.as_view(), name='product_list'),
]
