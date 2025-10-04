from django.contrib import admin
from .models import Booking


class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer', 'service', 'date', 'time_slot',
        'status', 'is_home_service', 'home_visit_fee', 'final_price_display'
    )
    list_filter = ('status', 'date', 'is_home_service')
    search_fields = ('customer__email', 'service__title')
    ordering = ('-created_at',)

    @admin.display(description="Final Price (₹)")
    def final_price_display(self, obj):
        return f"{obj.get_final_price():.2f}"

admin.site.register(Booking, BookingAdmin)
