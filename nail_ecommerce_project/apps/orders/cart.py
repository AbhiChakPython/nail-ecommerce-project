from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from nail_ecommerce_project.apps.products.models import ProductVariant
from logs.logger import get_logger
logger = get_logger(__name__)


class Cart:
    SESSION_KEY = 'cart'

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(self.SESSION_KEY)
        if cart is None:
            cart = self.session[self.SESSION_KEY] = {}
        self.cart = cart

    def add(self, variant: ProductVariant, quantity=1):
        if quantity <= 0:
            logger.warning(f"[CART] Attempt to add variant {variant} with non-positive quantity: {quantity}")
            return  # or raise ValueError("Quantity must be at least 1")

        if not isinstance(variant.price, (int, float, Decimal)):
            logger.error(f"[CART] Invalid price type for variant {variant}. Not adding to cart.")
            return

        try:
            price = Decimal(variant.price)
            if price <= 0:
                logger.warning(f"[CART] Attempt to add variant {variant} with non-positive price: {price}")
                return  # or raise ValueError("Price must be greater than 0")
        except (ValueError, TypeError, InvalidOperation):
            logger.exception(f"[CART] Failed to convert price to Decimal for variant {variant}")
            return

        vid = str(variant.pk)
        if vid not in self.cart:
            self.cart[vid] = {'quantity': 0, 'price': str(price)}

        self.cart[vid]['quantity'] += quantity
        self.save()
        logger.info(f"[CART] Added variant {variant} (x{quantity}) to cart with price ₹{price}")

    def remove(self, variant: ProductVariant):
        vid = str(variant.pk)
        if vid in self.cart:
            del self.cart[vid]
            self.save()
            logger.info(f"[CART] Removed variant {variant} from cart.")

    def clear(self):
        self.cart = {}  # ✅ Clear internal cart dict
        if self.SESSION_KEY in self.session:
            del self.session[self.SESSION_KEY]
            logger.info("[CART] Cleared cart from session.")
        self.session.modified = True

    def save(self):
        self.session[self.SESSION_KEY] = self.cart
        self.session.modified = True

    def __iter__(self):
        # Get all variant IDs currently in the cart session
        variant_ids = list(self.cart.keys())

        # Fetch all related ProductVariant objects from the database
        variants = ProductVariant.objects.filter(pk__in=variant_ids)
        variant_map = {str(variant.pk): variant for variant in variants}

        # Iterate over items stored in the session cart
        for vid, item in self.cart.items():
            variant = variant_map.get(vid)

            # If variant is no longer valid in DB, skip it
            if not variant:
                logger.warning(f"[CART] Variant ID {vid} not found in database. Skipping item.")
                continue

            # Extract quantity and price safely
            quantity = item.get('quantity', 0)
            try:
                price = Decimal(item.get('price', '0.00'))
            except (ValueError, TypeError):
                logger.error(f"[CART] Invalid price format in session for variant {vid}. Defaulting to 0.00")
                price = Decimal('0.00')

            # Yield structured cart item
            yield {
                'variant': variant,
                'quantity': quantity,
                'price': price,
                'total_price': price * quantity,
            }

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        total = Decimal('0.00')
        for item in self.cart.values():
            try:
                total += Decimal(item['price']) * item['quantity']
            except (ValueError, TypeError, InvalidOperation):
                logger.exception(f"[CART] Failed to compute total for item: {item}")
                continue
        return total

    def get_items_as_json_serializable(self):
        """
        Returns cart items in a JSON-serializable format
        useful for session storage or debugging.
        """
        items = []
        for item in self:
            items.append({
                'variant_id': item['variant'].id,
                'product_name': item['variant'].product.name,
                'quantity': item['quantity'],
                'price': float(item['price']),
            })
        return items


class BuyNowCart:
    SESSION_KEY = 'buy_now'

    def __init__(self, request):
        self.session = request.session
        self.data = self.session.get(self.SESSION_KEY)
        if not isinstance(self.data, dict):
            logger.warning("[BUY_NOW] Session data corrupted or invalid. Resetting buy_now session.")
            self.data = None
            self.session.pop(self.SESSION_KEY, None)
            self.session.modified = True

    def __bool__(self):
        return bool(self.get_item())

    def get_item(self):
        if not self.data:
            return None

        try:
            variant = ProductVariant.objects.get(pk=self.data['variant_id'])
            quantity = self.data.get('quantity', 1)
            if not isinstance(quantity, int) or quantity <= 0:
                logger.warning(f"[BUY_NOW] Invalid quantity found: {quantity}. Defaulting to 1")
                quantity = 1

            if 'price' not in self.data:
                # Backfill price using current price if missing
                price = variant.price
                rounded_price = str(price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                self.data['price'] = rounded_price  # Update session too
                self.session[self.SESSION_KEY] = self.data
                self.session.modified = True
                logger.warning(f"[BUY_NOW] 'price' missing from session. Recovered using variant.price")

            try:
                price = Decimal(self.data['price'])
            except (ValueError, TypeError, InvalidOperation):
                logger.exception("[BUY_NOW] Invalid price in session data.")
                self.clear()
                return None

            return {
                'variant': variant,
                'quantity': quantity,
                'price': price,
                'total_price': price * quantity
            }

        except ProductVariant.DoesNotExist:
            logger.error("[BUY_NOW] Variant not found while retrieving item")
            return None

    def clear(self):
        self.data = {}  # ✅ Clear internal BuyNowCart state
        if self.SESSION_KEY in self.session:
            del self.session[self.SESSION_KEY]
            logger.info("[BUY_NOW] Cleared Buy Now cart from session.")
        self.session.modified = True

    def get_variant(self):
        try:
            return ProductVariant.objects.get(pk=self.data['variant_id'])
        except (TypeError, KeyError, ProductVariant.DoesNotExist):
            return None

    def get_quantity(self):
        return self.data.get('quantity', 1) if self.data else 1