from django.contrib import admin
from .models import ProductCategory, Product, ProductVariant, ProductGalleryImage


class ProductGalleryImageInline(admin.TabularInline):
    model = ProductGalleryImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent_category')
    search_fields = ('name',)
    exclude = ['slug']


# If you want to register variants or images standalone (optional)
@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    def available_quantity_display(self, obj):
        return obj.available_quantity

    available_quantity_display.short_description = "Available"

    list_display = ('product', 'size', 'color', 'stock_quantity', 'available_quantity_display')
    list_filter = ('size', 'color')
    search_fields = ('product__name', 'size', 'color')


@admin.register(ProductGalleryImage)
class ProductGalleryImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_available', 'discount_percent', 'lto_discount_percent', 'created_at', 'updated_at')
    list_filter = ('is_available', 'created_at', 'categories')
    search_fields = ('name', 'description')
    inlines = [ProductGalleryImageInline, ProductVariantInline]
    filter_horizontal = ('categories',)
    exclude = ['slug']
