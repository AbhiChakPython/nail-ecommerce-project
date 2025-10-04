from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from .cart import BuyNowCart
from .forms import BuyNowShippingForm
from .models import Order, OrderItem
from .utils import create_razorpay_order
from ..products.models import ProductVariant
from logs.logger import get_logger

logger = get_logger(__name__)


class BuyNowView(LoginRequiredMixin, View):
    def post(self, request):
        if not getattr(request.user, 'is_customer', False):
            logger.warning(f"Unauthorized BuyNow access by user: {request.user}")
            raise PermissionDenied("Only customers can place orders.")

        variant_id = request.POST.get("variant_id")
        quantity = int(request.POST.get("quantity", 1))
        variant = get_object_or_404(ProductVariant, pk=variant_id)

        if variant.available_quantity < quantity:
            messages.error(request, f"Only {variant.available_quantity} left in stock for {variant.product.name}")
            return redirect('products:product_detail', slug=variant.product.slug)

        # ✅ Save price to session so no backfill is required later
        discounted_price = variant.product.get_discounted_price(variant.price)

        request.session['buy_now'] = {
            'variant_id': variant.id,
            'quantity': quantity,
            'price': str(discounted_price)  # store correct discounted price
        }
        request.session.modified = True

        logger.info(f"[BuyNowView] {request.user} selected variant {variant_id} (qty: {quantity}, price: {variant.price})")
        return redirect('orders:checkout_buy_now')


class BuyNowCheckoutView(LoginRequiredMixin, View):
    def get(self, request):
        buy_now_data = request.session.get('buy_now')
        if not buy_now_data:
            messages.error(request, "No product selected for Buy Now.")
            return redirect('products:product_list')

        try:
            variant = ProductVariant.objects.get(id=buy_now_data['variant_id'])
        except ProductVariant.DoesNotExist:
            messages.error(request, "Selected product variant does not exist.")
            return redirect('products:product_list')

        quantity = int(buy_now_data.get('quantity', 1))
        unit_price = variant.product.get_discounted_price(variant.price)
        total_price = unit_price * quantity
        buy_now_cart = BuyNowCart(request)
        item = buy_now_cart.get_item()
        if not item:
            messages.error(request, "Buy Now item not found.")
            return redirect("products:product_list")
        request.session['pre_payment_buy_now'] = [  # Store as list of 1 dict to match cart format
            {
                'variant_id': item['variant'].id,
                'quantity': item['quantity'],
                'price': float(item['price']),
                'product_name': item['variant'].product.name,
            }
        ]
        razorpay_order = create_razorpay_order(total_price)

        logger.debug(f"[BUY_NOW CHECKOUT] Razorpay Order Created: {razorpay_order}")
        logger.debug(f"[BUY_NOW CHECKOUT] Session updated: buy_now_cart={request.session.get('buy_now')}")
        logger.debug(f"[BUY_NOW CHECKOUT] Prefill Info: name={request.user.full_name}, "
                     f"email={request.user.email}, phone={request.user.phone_number}")

        user = request.user
        address = getattr(user, 'address', None)
        initial_data = {
            'full_name': user.full_name or '',
            'phone': user.phone_number or '',
            'address_line1': address.address_line1 if address else '',
            'address_line2': address.address_line2 if address else '',
            'city': address.city if address else '',
            'postal_code': address.pincode if address else '',
            'state': address.state if address else '',
        }

        form = BuyNowShippingForm(initial=initial_data)
        logger.debug(f"[BUY_NOW CHECKOUT] Initial shipping data: {initial_data}")

        context = {
            'form': form,
            'variant': variant,
            'quantity': quantity,
            'unit_price': unit_price,
            'total_price': total_price,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': int(total_price * 100),
        }

        return render(request, 'orders/checkout_buy_now.html', context)

    def post(self, request):
        form = BuyNowShippingForm(request.POST)
        buy_now_data = request.session.get('buy_now')
        if not form.is_valid() or not buy_now_data:
            messages.error(request, "Please correct the errors.")
            return redirect('orders:checkout_buy_now')

        variant = get_object_or_404(ProductVariant, pk=buy_now_data['variant_id'])
        quantity = int(buy_now_data.get('quantity', 1))

        # ✅ Inventory validation
        if variant.available_quantity < quantity:
            messages.error(
                request,
                f"Only {variant.available_quantity} units left for {variant.product.name} ({variant.size}/{variant.color})"
            )
            logger.warning(
                f"[BUY_NOW] Insufficient stock for {variant} - Requested: {quantity}, Available: {variant.available_quantity}"
            )
            return redirect('products:product_detail', slug=variant.product.slug)

        # ✅ Proceed with order creation
        order = Order.objects.create(
            user=request.user,
            full_name=form.cleaned_data['full_name'],
            phone=form.cleaned_data['phone'],
            address_line1=form.cleaned_data['address_line1'],
            address_line2=form.cleaned_data['address_line2'],
            city=form.cleaned_data['city'],
            postal_code=form.cleaned_data['postal_code'],
            state=form.cleaned_data['state'],
            status='PENDING',
            razorpay_order_id=request.POST.get('razorpay_order_id'),
        )

        OrderItem.objects.create(
            order=order,
            product_variant=variant,
            quantity=quantity
        )

        order.razorpay_payment_id = request.POST.get('razorpay_payment_id')
        order.razorpay_signature = request.POST.get('razorpay_signature')
        order.save()

        request.session.pop('buy_now', None)
        return redirect('orders:order_success', order_id=order.id)

