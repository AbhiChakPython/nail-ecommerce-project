from django.contrib import admin
from .models import Service, ServiceGalleryImage


class ServiceGalleryImageInline(admin.TabularInline):
    model = ServiceGalleryImage
    extra = 1  # Number of blank images shown by default
    fields = ['image_file', 'caption']
    readonly_fields = []

class ServiceAdmin(admin.ModelAdmin):
    list_display = ['title', 'price', 'duration_minutes', 'is_active']
    list_filter = ['is_active']
    search_fields = ['title', 'short_description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ServiceGalleryImageInline]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('title', 'short_description', 'duration_minutes', 'price', 'is_active')
        }),
        ("Images", {
            'fields': ('featured_image',)
        }),
        ("Timestamps", {
            'fields': ('created_at', 'updated_at')
        }),
    )


admin.site.register(Service, ServiceAdmin)
