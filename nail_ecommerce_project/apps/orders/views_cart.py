from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from .cart import Cart
from ..products.views_frontend import IsCustomerMixin
from .utils import create_razorpay_order
from ..products.models import ProductVariant
from .forms import CartShippingForm, OrderCreateForm
from logs.logger import get_logger

logger = get_logger(__name__)


class CartDetailView(LoginRequiredMixin, View):
    def get(self, request):
        if not getattr(request.user, 'is_customer', False):
            logger.warning(f"CartDetailView: Unauthorized access by {request.user}")
            raise PermissionDenied("Only customers can view cart.")

        cart = Cart(request)
        items = []
        total = Decimal("0.00")
        any_exceeds_stock = False

        for item in cart:
            variant = item['variant']
            product = variant.product
            quantity = item['quantity']
            available = variant.available_quantity
            unit_price = variant.price
            discounted_price = product.get_discounted_price(unit_price)
            subtotal = discounted_price * quantity
            total += subtotal

            exceeds_stock = quantity > available
            if exceeds_stock:
                any_exceeds_stock = True

            items.append({
                'product': product,
                'variant': variant,
                'quantity': quantity,
                'unit_price': unit_price,
                'discounted_price': discounted_price,
                'subtotal': subtotal,
                'variant_id': variant.id,
                'exceeds_stock': exceeds_stock,
                'available_quantity': available,
            })

        logger.info(f"CartDetailView: User {request.user} viewed cart ({len(cart)} items)")

        return render(request, 'orders/cart_detail.html', {
            'items': items,
            'total_price': total,
            'any_exceeds_stock': any_exceeds_stock,
        })


class CartCheckoutView(LoginRequiredMixin, View):
    def get(self, request):
        if not getattr(request.user, 'is_customer', False):
            logger.warning(f"CartCheckoutView: Unauthorized access by {request.user}")
            raise PermissionDenied("Only customers can checkout.")

        cart = Cart(request)
        items = []
        total = Decimal("0.00")

        for item in cart:
            variant = item['variant']
            product = variant.product
            quantity = item['quantity']
            unit_price = variant.price
            discounted_price = product.get_discounted_price(unit_price)
            subtotal = discounted_price * quantity
            total += subtotal

            logger.debug(
                f"[CART ITEM] {product.name} | qty: {quantity} | price: {unit_price} | "
                f"discounted: {discounted_price} | subtotal: {subtotal}"
            )

            if variant.available_quantity < quantity:
                messages.error(request,
                               f"Insufficient stock for {product.name} ({variant.size}/{variant.color}). "
                               f"Only {variant.available_quantity} left in stock.")
                return redirect('orders:cart_detail')

            items.append({
                'product': product,
                'variant': variant,
                'quantity': quantity,
                'unit_price': unit_price,
                'discounted_price': discounted_price,
                'subtotal': subtotal,
            })

        initial_data = {
            'full_name': request.user.full_name or '',
            'phone': request.user.phone_number or '',
            'address_line1': '',
            'address_line2': '',
            'city': '',
            'postal_code': '',
            'state': '',
            'use_for_home_service': True,  # default True if no address
        }

        address = getattr(request.user, 'address', None)
        if address:
            initial_data.update({
                'address_line1': address.address_line1,
                'address_line2': address.address_line2,
                'city': address.city,
                'postal_code': address.pincode,
                'state': address.state,
                'use_for_home_service': address.use_for_home_service,
            })

        form = CartShippingForm(initial=initial_data)
        logger.debug(f"[SANITY CHECK] Cart total before Razorpay order: ₹{total}")

        if total < Decimal('1.00'):
            logger.error(f"[FATAL] Cart total less than ₹1.00! This is not allowed.")
            logger.error(f"[CART_CHECKOUT ❌] Order total ({total}) is less than ₹1. Razorpay minimum requirement.")
            messages.error(request, "Order total must be at least ₹1 to proceed with payment.")
            return redirect('orders:cart_detail')

        razorpay_order = create_razorpay_order(total)
        logger.debug(f"[CART_CHECKOUT] Creating Razorpay Order: amount={total}, user={request.user.email}")
        logger.debug(f"[CART_CHECKOUT] Razorpay Order Response: {razorpay_order}")

        request.session['cart_razorpay_order_id'] = razorpay_order['id']
        request.session.modified = True

        pre_payment_cart_data = []

        for item in cart:
            variant = item['variant']
            product = variant.product
            quantity = item['quantity']
            unit_price = variant.price
            discounted_price = product.get_discounted_price(unit_price)

            pre_payment_cart_data.append({
                'variant_id': variant.id,
                'quantity': quantity,
                'price': str(discounted_price),  # ✅ Store correct discounted price
                'product_name': product.name,
            })

        request.session['pre_payment_cart'] = pre_payment_cart_data
        request.session.modified = True

        logger.debug(
            f"[CART ITEM] {product.name} | qty: {quantity} | discounted_price: {discounted_price} | subtotal: {subtotal}")

        logger.info(
            f"[CART_CHECKOUT] Rendering Razorpay modal for user {request.user.email} with order {razorpay_order['id']}")

        return render(request, 'orders/checkout_cart.html', {
            'form': form,
            'items': items,
            'total_price': total,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': int(total * 100),
        })


class AddToCartView(IsCustomerMixin, View):
    def post(self, request):
        logger.info("[CART_ADD] Add to cart triggered")
        logger.info(f"[CART_ADD] User: {request.user.email} (Authenticated: {request.user.is_authenticated})")
        logger.debug(f"[CART_ADD] Raw POST data: {request.POST}")

        variant_id = request.POST.get('variant_id')
        if not variant_id:
            logger.warning(f"[CART_ADD] No variant_id provided by user {request.user}")
            return redirect('products:product_list')

        variant = get_object_or_404(ProductVariant, pk=variant_id)
        quantity = int(request.POST.get('quantity', 1))

        if variant.available_quantity < quantity:
            messages.error(request, f"Only {variant.available_quantity} units available for {variant}.")
            logger.warning(
                f"[CART_ADD] Not enough stock for {variant} - Requested: {quantity}, Available: {variant.available_quantity}")
            return redirect('products:product_detail', slug=variant.product.slug)

        Cart(request).add(variant, quantity=quantity)
        logger.info(f"[CART_ADD] Variant {variant.id} (Qty: {quantity}) added to cart by {request.user.email}")
        logger.debug(f"[CART STATE AFTER ADD] {request.session.get('cart')}")

        product_url = reverse('products:product_detail', kwargs={'slug': variant.product.slug})
        return redirect(f"{product_url}?added=1")


class RemoveFromCartView(LoginRequiredMixin, View):
    def post(self, request, variant_id):
        if not getattr(request.user, 'is_customer', False):
            raise PermissionDenied("Only customers can modify cart.")

        variant = get_object_or_404(ProductVariant, pk=variant_id)
        Cart(request).remove(variant)

        logger.info(f"RemoveFromCartView: {variant} removed by {request.user}")
        return redirect('orders:cart_detail')
