from django.db import models
from django.conf import settings
from nail_ecommerce_project.apps.products.models import ProductVariant
from logs.logger import get_logger
logger = get_logger(__name__)


class Order(models.Model):
    STATUS_CHOICES = [
        ('ORDERED', 'Ordered'),
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    state = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    was_restocked = models.BooleanField(default=False)
    cancelled_by_customer = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        order_str = f"Order #{self.id} by {self.user}"
        logger.debug(f"[ORDER] __str__ called: {order_str}")
        return order_str

    @property
    def total_price(self):
        total = sum(item.get_total() for item in self.items.all())
        logger.debug(f"[ORDER] Calculated total (with recorded prices) for Order #{self.id}: ₹{total}")
        return total

    @property
    def total_discount(self):
        item_total_without_discount = sum(
            item.product_variant.price * item.quantity for item in self.items.select_related('product_variant')
        )
        item_total_with_discount = sum(item.price_at_order * item.quantity for item in self.items.all())

        discount_amount = item_total_without_discount - item_total_with_discount
        return discount_amount if discount_amount > 0 else 0

    def cancel_order(self, by_customer=False):
        if self.status == 'CANCELLED':
            logger.warning(f"[CANCEL IGNORE] Order #{self.id} already cancelled.")
            return

        logger.info(f"[CANCEL_TRIGGER] Order #{self.id} triggered cancellation")

        self.status = 'CANCELLED'
        self.cancelled_by_customer = by_customer

        if not self.was_restocked:
            for item in self.items.select_related('product_variant').all():
                variant = item.product_variant
                old_stock = variant.stock_quantity
                variant.stock_quantity += item.quantity
                variant.save()

                logger.info(
                    f"[RESTOCK COMPLETE] Order #{self.id} | Variant ID: {variant.id} | "
                    f"Restocked: {item.quantity} | Old Stock: {old_stock} → New Stock: {variant.stock_quantity}"
                )

            self.was_restocked = True

        self.save(update_fields=['status', 'cancelled_by_customer', 'was_restocked'])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status

    def save(self, *args, **kwargs):
        logger.debug(
            f"[ORDER SAVE] Order #{self.id} | Status: {self.status} | WasRestocked: {self.was_restocked}"
        )
        super().save(*args, **kwargs)
        self._original_status = self.status


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def line_total(self):
        return self.get_total()

    def get_total(self):
        return self.quantity * self.price_at_order

    def __str__(self):
        return f"{self.quantity} × {self.product_variant}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        logger.info(f"[ORDER ITEM] Saved {self.quantity} × {self.product_variant} in Order #{self.order.id}")
