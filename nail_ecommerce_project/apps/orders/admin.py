from django.contrib import admin
from .models import Order, OrderItem
from .utils import send_order_confirmed_email
from logs.logger import get_logger

logger = get_logger(__name__)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product_variant', 'quantity')
    can_delete = False
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'created_at', 'total_amount_display')
    list_filter = ('status', 'created_at')
    inlines = [OrderItemInline]

    def total_amount_display(self, obj):
        return f"₹{obj.total_price:.2f}"

    total_amount_display.short_description = 'Total Amount'

    readonly_fields = ('razorpay_order_id',)

    def save_model(self, request, obj, form, change):
        original = Order.objects.get(pk=obj.pk) if obj.pk else None
        super().save_model(request, obj, form, change)

        # ✅ Deduct stock and update availability when marked CONFIRMED
        if original and original.status != obj.status and obj.status == 'CONFIRMED':
            for item in obj.items.all():
                variant = item.product_variant

                if variant.stock_quantity >= item.quantity:
                    variant.stock_quantity -= item.quantity
                    variant.save(update_fields=["stock_quantity"])

                    # ✅ Update availability based on new stock
                    variant.update_availability_status()

                    logger.info(f"[ADMIN] Inventory updated for variant {variant}: -{item.quantity} (CONFIRMED)")
                else:
                    logger.warning(f"[ADMIN] Not enough stock to deduct for variant {variant} during CONFIRMED.")

            try:
                send_order_confirmed_email(obj)
                logger.info(f"Confirmation email (admin) sent to {obj.user.email} for order {obj.id}")
            except Exception as e:
                logger.error(f"Admin failed to send confirmation email for order {obj.id}: {e}")


