from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify


class Service(models.Model):
    title = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    short_description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=60, help_text="Duration in minutes")
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    featured_image = models.ImageField(upload_to='services/featured_image/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-generate slug if not manually entered
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class ServiceGalleryImage(models.Model):
    service = models.ForeignKey(Service, related_name='gallery_images', on_delete=models.CASCADE)
    image_file = models.ImageField(upload_to='services/gallery/')
    caption = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Gallery image for {self.service.title}"