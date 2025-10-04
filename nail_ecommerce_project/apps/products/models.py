from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from logs.logger import get_logger
logger = get_logger(__name__)


class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    parent_category = models.ForeignKey(
        'self', null=True, blank=True, related_name='subcategories', on_delete=models.CASCADE
    )

    class Meta:
        verbose_name_plural = 'Product Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to='products/thumbnails/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    categories = models.ManyToManyField(ProductCategory, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 💸 Discount Fields (NEW)
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Fixed discount % off retail price (e.g., 30 means 30%)"
    )
    lto_discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Limited Time Offer (LTO) % discount (active only during period)"
    )
    lto_start_date = models.DateTimeField(null=True, blank=True)
    lto_end_date = models.DateTimeField(null=True, blank=True)

    def get_discounted_price(self, base_price):
        base_price = Decimal(base_price)
        final_price = base_price
        now = timezone.now()

        if (
                self.lto_discount_percent > 0 and
                self.lto_start_date and
                self.lto_end_date and
                self.lto_start_date <= now <= self.lto_end_date
        ):
            discount = (Decimal(self.lto_discount_percent) / Decimal("100")) * base_price
            final_price = base_price - discount
            logger.debug(f"[DISCOUNT] LTO applied to {self.name}: -{self.lto_discount_percent}%")
        elif self.discount_percent > 0:
            discount = (Decimal(self.discount_percent) / Decimal("100")) * base_price
            final_price = base_price - Decimal(discount)
            logger.debug(f"[DISCOUNT] Regular discount applied to {self.name}: -{self.discount_percent}%")

        return final_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def clean(self):
        if self.lto_discount_percent and (not self.lto_start_date or not self.lto_end_date):
            logger.warning(f"[CLEAN] LTO discount defined but missing start/end dates for product: {self.name}")
            raise ValidationError("Limited-time discount requires both start and end dates.")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            logger.info(f"[SAVE] Slug generated for product '{self.name}': {self.slug}")
        super().save(*args, **kwargs)

    def is_lto_active(self):
        now = timezone.now()
        is_active = (
                self.lto_discount_percent > 0 and
                self.lto_start_date and self.lto_end_date and
                self.lto_start_date <= now <= self.lto_end_date
        )
        logger.debug(f"[CHECK] LTO active for '{self.name}': {is_active}")
        return is_active

    def __str__(self):
        return self.name


class ProductGalleryImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='products/gallery/')

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=50)
    color = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('product', 'size', 'color')

    def get_discounted_price(self):
        """
            Wrapper for variant discount logic using the parent product's discount rules.
            """
        return self.product.get_discounted_price(self.price)

    @property
    def available_quantity(self):
        return self.stock_quantity or 0

    def update_availability_status(self):
        if self.available_quantity == 0:
            self.product.is_available = False
        else:
            self.product.is_available = True
        self.product.save()

    def __str__(self):
        return f"{self.product.name} - {self.size} - {self.color}"
