from decimal import Decimal
import razorpay
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from logs.logger import get_logger

logger = get_logger(__name__)


def create_razorpay_order(amount, currency='INR'):
    try:
        assert isinstance(amount, (int, float, Decimal)), "Amount must be a number"
        amount = Decimal(amount).quantize(Decimal("0.01"))  # ⬅ ensures 2 decimal places
        amount_in_paise = int(amount * 100)

        if amount_in_paise < 100:
            raise ValueError(f"Order amount {amount} must be at least ₹1.00 (i.e., 100 paise) for Razorpay.")

        logger.debug(f"[RAZORPAY CREATE] Creating Razorpay order with:")
        logger.debug(f"  - Amount: ₹{amount} ({amount_in_paise} paise)")
        logger.debug(f"  - Currency: {currency}")
        logger.debug(f"  - API Key: {settings.RAZORPAY_KEY_ID}")

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        response = client.order.create({
            'amount': amount_in_paise,
            'currency': currency,
            'payment_capture': '1'
        })

        logger.info(f"[RAZORPAY CREATE ✅] Razorpay order created: {response}")
        return response

    except Exception as e:
        logger.exception(f"[RAZORPAY CREATE ❌] Failed to create Razorpay order: {e}")
        raise


def deduct_variant_stock(order):
    for item in order.items.select_related('product_variant'):
        variant = item.product_variant
        old_stock = variant.stock_quantity

        if old_stock < item.quantity:
            raise ValueError(
                f"Cannot deduct stock: Variant {variant.id} has only {old_stock} units, "
                f"but order item requires {item.quantity}.")

        variant.stock_quantity = max(0, old_stock - item.quantity)
        variant.save(update_fields=["stock_quantity"])

        logger.info(
            f"[STOCK DEDUCTED] Order #{order.id} | Variant ID: {variant.id} | "
            f"{old_stock} → {variant.stock_quantity} (Deducted: {item.quantity})"
        )


def send_order_placed_email(order):
    subject = f"Order #{order.id} Placed Successfully"
    to_email = order.user.email
    context = {'order': order}

    text_content = render_to_string('orders/emails/order_placed.txt', context)
    html_content = render_to_string('orders/emails/order_placed.html', context)

    try:
        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Order placed email sent to {to_email} for order #{order.id}")
    except Exception as e:
        logger.error(f"Failed to send order placed email to {to_email}: {e}")


def send_order_confirmed_email(order):
    subject = f"Order #{order.id} Confirmed"
    to_email = order.user.email
    context = {'order': order}

    text_content = render_to_string('orders/emails/order_confirmed.txt', context)
    html_content = render_to_string('orders/emails/order_confirmed.html', context)

    try:
        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Order confirmation email sent to {to_email} for order #{order.id}")
    except Exception as e:
        logger.error(f"Failed to send confirmation email to {to_email}: {e}")
