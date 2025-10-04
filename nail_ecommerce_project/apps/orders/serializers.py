from rest_framework import serializers
from .models import Order, OrderItem
from .models import ProductVariant
from django.db import transaction


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'size', 'color', 'price']


class OrderItemSerializer(serializers.ModelSerializer):
    product_variant = ProductVariantSerializer(read_only=True)
    product_variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(),
        source='product_variant',
        write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'product_variant', 'product_variant_id', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, write_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'full_name', 'phone',
            'address_line1', 'address_line2', 'city',
            'postal_code', 'state', 'status',
            'razorpay_order_id', 'razorpay_payment_id',
            'razorpay_signature', 'created_at', 'updated_at',
            'order_items', 'items'
        ]
        read_only_fields = [
            'id', 'user', 'status',
            'razorpay_order_id', 'razorpay_payment_id',
            'razorpay_signature', 'created_at', 'updated_at',
            'items'
        ]

    def validate_order_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")

        for item in value:
            variant = item['product_variant']
            quantity = item['quantity']

            if variant.stock_quantity < quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock for {variant}. Available: {variant.stock_quantity}, requested: {quantity}."
                )

        return value

    def create(self, validated_data):
        order_items_data = validated_data.pop('order_items')
        user = self.context['request'].user
        order = Order.objects.create(user=user, **validated_data)

        for item_data in order_items_data:
            variant = item_data["product_variant"]
            qty = item_data["quantity"]

            OrderItem.objects.create(
                order=order,
                product_variant=variant,
                quantity=qty,
                price_at_order=variant.price  # ✅ freeze price snapshot
            )

        return order
