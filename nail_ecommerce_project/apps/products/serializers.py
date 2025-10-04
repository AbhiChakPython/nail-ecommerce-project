from rest_framework import serializers
from .models import ProductCategory, Product, ProductVariant, ProductGalleryImage
from logs.logger import get_logger
logger = get_logger(__name__)


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'slug', 'parent_category']


class ProductGalleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductGalleryImage
        fields = ['id', 'image']


class ProductVariantSerializer(serializers.ModelSerializer):
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ['id', 'size', 'color', 'price', 'stock_quantity', 'discounted_price']

    def get_discounted_price(self, obj):
        return obj.get_discounted_price()


class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True)
    gallery_images = ProductGalleryImageSerializer(many=True)
    categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ProductCategory.objects.all()
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'thumbnail', 'is_available',
            'discount_percent', 'lto_discount_percent', 'lto_start_date', 'lto_end_date',
            'categories', 'variants', 'gallery_images', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        gallery_data = validated_data.pop('gallery_images', [])
        categories_data = validated_data.pop('categories', [])

        product = Product.objects.create(**validated_data)
        product.categories.set(categories_data)

        for variant in variants_data:
            ProductVariant.objects.create(product=product, **variant)

        for image in gallery_data:
            ProductGalleryImage.objects.create(product=product, **image)

        logger.info(
            f"Product created via API: {product.name} (ID: {product.id}) with {len(variants_data)} variants and {len(gallery_data)} images")
        return product

    def update(self, instance, validated_data):
        variants_data = validated_data.pop('variants', [])
        gallery_data = validated_data.pop('gallery_images', [])
        categories_data = validated_data.pop('categories', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.categories.set(categories_data)
        instance.save()

        if variants_data:
            instance.variants.all().delete()
            for variant in variants_data:
                ProductVariant.objects.create(product=instance, **variant)

        if gallery_data:
            instance.gallery_images.all().delete()
            for image in gallery_data:
                ProductGalleryImage.objects.create(product=instance, **image)

        logger.info(
            f"Product updated via API: {instance.name} (ID: {instance.id}) with {len(variants_data)} variants and {len(gallery_data)} images")
        return instance