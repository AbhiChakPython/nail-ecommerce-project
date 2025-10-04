from decimal import Decimal, InvalidOperation
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from .models import Order, OrderItem
from .forms import OrderCreateForm
from .cart import Cart, BuyNowCart
from .utils import send_order_placed_email, deduct_variant_stock
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
import razorpay
from .utils import deduct_variant_stock
from django.conf import settings
from logs.logger import get_logger
from ..products.models import ProductVariant

logger = get_logger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class CartCallbackView(View):
    def post(self, request, *args, **kwargs):
        logger.warning("[CALLBACK] CartCallbackView hit")

        payment_id = request.POST.get('razorpay_payment_id')
        signature = request.POST.get('razorpay_signature')
        order_id = request.POST.get('razorpay_order_id')
        user = request.user

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
        except razorpay.errors.SignatureVerificationError as e:
            logger.warning(f"[CALLBACK] Cart payment signature failed: {e}")
            return redirect('orders:order_failed')

        pre_cart = request.session.get('pre_payment_cart')
        if not pre_cart:
            logger.error("[CALLBACK] pre_payment_cart missing.")
            return redirect('orders:order_failed')

        order = Order.objects.create(
            user=user,
            full_name=user.full_name,
            phone=user.phone_number,
            address_line1=user.address,
            status='CONFIRMED',
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
        )

        for item in pre_cart:
            variant = ProductVariant.objects.get(pk=item['variant_id'])
            OrderItem.objects.create(order=order, product_variant=variant, quantity=item['quantity'])

        Cart(request).clear()
        request.session.pop('pre_payment_cart', None)

        try:
            send_order_placed_email(order)
        except Exception as e:
            logger.error(f"Email sending failed for order {order.id}: {e}")

        logger.info(f"[CALLBACK] Cart order {order.id} created and confirmed.")
        return redirect('orders:order_success', order_id=order.id)


@method_decorator(csrf_exempt, name='dispatch')
class BuyNowCallbackView(View):
    def post(self, request, *args, **kwargs):
        logger.warning("[CALLBACK] BuyNowCallbackView hit")

        payment_id = request.POST.get('razorpay_payment_id')
        signature = request.POST.get('razorpay_signature')
        order_id = request.POST.get('razorpay_order_id')
        user = request.user

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
        except razorpay.errors.SignatureVerificationError as e:
            logger.warning(f"[CALLBACK] BuyNow signature verification failed: {e}")
            return redirect('orders:order_failed')

        pre_buy_now = request.session.get('pre_payment_buy_now')
        if not pre_buy_now:
            logger.error("[CALLBACK] pre_payment_buy_now missing.")
            return redirect('orders:order_failed')

        item = pre_buy_now[0]
        variant = ProductVariant.objects.get(pk=item['variant_id'])

        order = Order.objects.create(
            user=user,
            full_name=user.full_name,
            phone=user.phone_number,
            address_line1=user.address,
            status='CONFIRMED',
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
        )

        OrderItem.objects.create(order=order, product_variant=variant, quantity=item['quantity'])

        request.session.pop('buy_now', None)
        request.session.pop('pre_payment_buy_now', None)

        try:
            send_order_placed_email(order)
        except Exception as e:
            logger.error(f"Email sending failed for order {order.id}: {e}")

        logger.info(f"[CALLBACK] BuyNow order {order.id} created and confirmed.")
        return redirect('orders:order_success', order_id=order.id)


class OrderSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'orders/order_success.html'

    def get(self, request, *args, **kwargs):
        order_id = kwargs.get('order_id')
        try:
            order = Order.objects.get(pk=order_id)
        except Order.DoesNotExist:
            logger.error(f"OrderSuccessView: Order ID {order_id} not found.")
            return redirect('orders:order_failed')

        if order.user != request.user:
            logger.warning(f"User {request.user} tried to access order {order_id} not owned by them.")
            return redirect('orders:order_failed')

        # ✅ Clear session cart just in case
        Cart(request).clear()
        logger.info(f"OrderSuccessView: Cleared cart and showing success page for order {order.id} (User: {request.user})")

        return self.render_to_response({'order': order})


class OrderFailedView(TemplateView):
    template_name = 'orders/order_failed.html'

    def get(self, request, *args, **kwargs):
        logger.warning(f"OrderFailedView accessed by user {request.user}")
        return self.render_to_response({})


@method_decorator(csrf_exempt, name='dispatch')
class CartPaymentVerifyView(LoginRequiredMixin, View):
    def post(self, request):
        logger.warning("[CALLBACK] CartPaymentVerifyView triggered")
        logger.warning(f"[CALLBACK USER DEBUG] request.user: {request.user} (Authenticated: {request.user.is_authenticated})")
        logger.warning(f"[CALLBACK SESSION DEBUG] session_key: {request.session.session_key}")
        logger.debug(f"[CALLBACK SESSION CONTENTS] cart: {request.session.get('cart')}")

        razorpay_order_id = request.POST.get('razorpay_order_id')
        payment_id = request.POST.get('razorpay_payment_id')
        signature = request.POST.get('razorpay_signature')

        expected_razorpay_id = request.session.get('cart_razorpay_order_id')
        if expected_razorpay_id and expected_razorpay_id != razorpay_order_id:
            logger.warning(f"[SECURITY] Mismatched Razorpay order ID. Expected: {expected_razorpay_id}, Got: {razorpay_order_id}")
            messages.error(request, "Order validation failed. Please try again.")
            return redirect('orders:order_failed')

        if not all([razorpay_order_id, payment_id, signature]):
            logger.error("[ERROR] Missing Razorpay fields in POST data.")
            return redirect('orders:order_failed')

        cart = Cart(request)
        logger.debug(f"[CART CHECK] Cart contents before processing: {cart.cart}")

        pre_payment_cart = request.session.get('pre_payment_cart')
        if not pre_payment_cart:
            logger.error("[CALLBACK] No pre-payment cart found in session.")
            messages.error(request, "Session expired or cart missing.")
            return redirect('orders:cart_detail')

        form = OrderCreateForm(request.POST)
        if not form.is_valid():
            logger.warning("[FORM] Order form is invalid.")
            messages.error(request, "Please correct your details.")
            return redirect('orders:checkout_cart')

        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature,
            })
            logger.info("[RAZORPAY] Signature verified successfully")

            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    full_name=form.cleaned_data['full_name'],
                    phone=form.cleaned_data['phone'],
                    address_line1=form.cleaned_data['address_line1'],
                    address_line2=form.cleaned_data['address_line2'],
                    city=form.cleaned_data['city'],
                    postal_code=form.cleaned_data['postal_code'],
                    state=form.cleaned_data['state'],
                    status='ORDERED',
                    razorpay_order_id=razorpay_order_id,
                    razorpay_payment_id=payment_id,
                    razorpay_signature=signature
                )
                logger.info(f"[ORDER CREATED] Order #{order.id} created for user {request.user.email}")

                for item in pre_payment_cart:
                    variant = ProductVariant.objects.get(pk=item['variant_id'])

                    if variant.stock_quantity < item['quantity']:
                        raise ValueError(
                            f"Not enough stock for variant {variant.id}. Requested: {item['quantity']}, Available: {variant.stock_quantity}"
                        )

                    quantity = item['quantity']
                    price = Decimal(item['price'])

                    OrderItem.objects.create(
                        order=order,
                        product_variant=variant,
                        quantity=quantity,
                        price_at_order=price
                    )
                    logger.debug(f"[ORDER ITEM] Created: {quantity} × {variant} @ ₹{price}")

                deduct_variant_stock(order)  # ✅ Centralized stock deduction
                cart.clear()
                send_order_placed_email(order)
                return render(request, 'orders/order_success.html', {'order': order})

        except razorpay.errors.SignatureVerificationError:
            return redirect('orders:order_failed')
        except Exception as e:
            logger.exception(f"[EXCEPTION] {str(e)}")
            return redirect('orders:order_failed')


@method_decorator(csrf_exempt, name='dispatch')
class BuyNowPaymentVerifyView(LoginRequiredMixin, View):
    def post(self, request):
        razorpay_order_id = request.POST.get('razorpay_order_id')
        payment_id = request.POST.get('razorpay_payment_id')
        signature = request.POST.get('razorpay_signature')

        if not all([razorpay_order_id, payment_id, signature]):
            return redirect('orders:order_failed')

        cart = BuyNowCart(request)
        variant = cart.get_variant()
        quantity = cart.get_quantity()

        if not variant or not quantity:
            logger.warning("[BUY NOW] Variant or quantity missing in session.")
            return redirect('products:product_list')

        form = OrderCreateForm(request.POST)
        if not form.is_valid():
            logger.warning("[BUY NOW] Invalid order form.")
            return redirect('orders:checkout_buy_now')

        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature,
            })

            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    full_name=form.cleaned_data['full_name'],
                    phone=form.cleaned_data['phone'],
                    address_line1=form.cleaned_data['address_line1'],
                    address_line2=form.cleaned_data['address_line2'],
                    city=form.cleaned_data['city'],
                    postal_code=form.cleaned_data['postal_code'],
                    state=form.cleaned_data['state'],
                    status='ORDERED',
                    razorpay_order_id=razorpay_order_id,
                    razorpay_payment_id=payment_id,
                    razorpay_signature=signature
                )

                item = cart.get_item()
                price = Decimal(item.get('price', variant.price))  # fallback if 'price' missing

                OrderItem.objects.create(
                    order=order,
                    product_variant=variant,
                    quantity=quantity,
                    price_at_order=price
                )
                logger.debug(f"[BUY NOW ITEM] {quantity} × {variant} @ ₹{price}")

                deduct_variant_stock(order)
                cart.clear()
                send_order_placed_email(order)
                return render(request, 'orders/order_success.html', {'order': order})

        except razorpay.errors.SignatureVerificationError:
            logger.error("[RAZORPAY] Signature verification failed.")
            return redirect('orders:order_failed')

        except Exception as e:
            logger.exception(f"[BUY NOW CALLBACK ERROR] {str(e)}")
            return redirect('orders:order_failed')
