from urllib.parse import urlencode

from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.views.generic import ListView
from django.views import View
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from .models import Order
from .utils import send_order_confirmed_email
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect
from django.urls import reverse
from ..products.models import ProductVariant
from django.core.paginator import Paginator
from django.db.models import Q
from logs.logger import get_logger

logger = get_logger(__name__)


class AdminOrderListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Order
    template_name = 'orders/admin_order_list.html'
    context_object_name = 'orders'
    queryset = Order.objects.all().select_related('user').prefetch_related(
        'items__product_variant__product').order_by('-created_at')
    paginate_by = 5

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        search = self.request.GET.get('search', '').strip()
        active_tab = self.request.GET.get('tab', 'orders')

        # Only filter orders if we're in the "orders" tab
        if active_tab == 'orders':
            if status:
                queryset = queryset.filter(status=status)

            if search:
                # Normalize "Order #50" → "50"
                if search.lower().startswith("order #"):
                    search = search[7:].strip()

                if search.isdigit():
                    queryset = queryset.filter(id=int(search))
                else:
                    queryset = queryset.filter(
                        Q(user__full_name__icontains=search) |
                        Q(user__email__icontains=search)
                    )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Order.STATUS_CHOICES

        # Get filter params
        search_query = self.request.GET.get('search', '')
        availability_filter = self.request.GET.get('availability', '')

        active_tab = self.request.GET.get('tab', 'orders')
        context['active_tab'] = active_tab
        context['search_query'] = search_query
        context['availability_filter'] = availability_filter

        # Inventory filtering
        variant_queryset = ProductVariant.objects.select_related('product')
        if search_query:
            variant_queryset = variant_queryset.filter(product__name__icontains=search_query)
        if availability_filter == 'available':
            variant_queryset = variant_queryset.filter(product__is_available=True)
        elif availability_filter == 'out_of_stock':
            variant_queryset = variant_queryset.filter(product__is_available=False)
        elif availability_filter == 'low_stock':
            variant_queryset = variant_queryset.filter(stock_quantity__lte=3)
        variant_queryset = variant_queryset.order_by('product__name')

        # Paginate inventory results
        variant_paginator = Paginator(variant_queryset, 5)
        variant_page = self.request.GET.get('variant_page')
        context['variant_page_obj'] = variant_paginator.get_page(variant_page)

        # Low stock alert
        context['low_stock_variants'] = ProductVariant.objects.select_related('product').filter(stock_quantity__lte=3)

        # 🚨 Unified empty search logic for Orders tab
        context['invalid_order_search'] = False
        context['no_orders_found'] = False

        if active_tab == 'orders' and not context['orders']:
            # Only run this if the order list is empty
            search_input = search_query.lower().strip()
            if search_input.startswith("order #"):
                try:
                    order_id = int(search_input.replace("order #", "").strip())
                    if not Order.objects.filter(id=order_id).exists():
                        context['invalid_order_search'] = True
                except ValueError:
                    context['invalid_order_search'] = True
            else:
                context['no_orders_found'] = True

        return context


class UpdateOrderStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        new_status = request.POST.get("status")

        if new_status not in dict(Order.STATUS_CHOICES):
            messages.error(request, "Invalid status selected.")
            return redirect('orders_admin:order_list')

        old_status = order.status

        # 🚫 Prevent any changes if already CANCELLED or DELIVERED
        if old_status in ["CANCELLED", "DELIVERED"]:
            messages.warning(request, f"Order #{order.id} is already {old_status}. Status cannot be changed.")
            logger.warning(f"[ORDER STATUS BLOCKED] Attempt to change Order #{order.id} (already {old_status}) to {new_status}")
            return redirect('orders_admin:order_list')

        # ✅ Prevent confirming if stock is insufficient
        if old_status != new_status and new_status == "CONFIRMED":
            for item in order.items.all():
                variant = item.product_variant
                if item.quantity > variant.stock_quantity:
                    logger.warning(f"[INVENTORY] Not enough stock to confirm Order #{order.id} for variant {variant}")
                    messages.error(request, f"Not enough stock for {variant}. Confirmation aborted.")
                    return redirect('orders_admin:order_list')

        order.status = new_status
        order.save()

        # ✅ Handle stock changes
        if old_status != new_status:
            if new_status == "CONFIRMED":
                for item in order.items.all():
                    variant = item.product_variant
                    variant.stock_quantity = max(0, variant.stock_quantity - item.quantity)
                    variant.save(update_fields=["stock_quantity"])
                    logger.info(f"[ORDER] Deducted {item.quantity} from {variant} (Order #{order.id} CONFIRMED)")

                try:
                    send_order_confirmed_email(order)
                    logger.info(f"[ADMIN] Confirmation email sent for Order #{order.id}")
                except Exception as e:
                    logger.error(f"[ADMIN] Failed to send confirmation email for Order #{order.id}: {e}")

        messages.success(request, f"Order #{order.id} status updated to {new_status}.")

        query_params = {
            'tab': request.GET.get('tab', 'orders'),
            'page': request.GET.get('page'),
            'search': request.GET.get('search'),
            'status': request.GET.get('status'),
        }

        # Clean up None values
        clean_query = {k: v for k, v in query_params.items() if v}

        # Redirect with preserved context
        return redirect(f"{reverse('orders_admin:order_list')}?{urlencode(clean_query)}")


@method_decorator(csrf_exempt, name='dispatch')
class ManageInventoryView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        variants = ProductVariant.objects.select_related('product').all().order_by('product__name')
        return render(request, 'orders/admin_order_list.html', {
            'variants': variants,
            'active_tab': 'inventory',  # ✅ Stay on inventory tab
        })

    def post(self, request):
        variant_id = request.POST.get("variant_id")
        action = request.POST.get("action")
        manual_quantity = request.POST.get("manual_stock_quantity")

        try:
            variant = ProductVariant.objects.select_related('product').get(id=variant_id)
        except ProductVariant.DoesNotExist:
            messages.error(request, "Variant not found.")
            return HttpResponseRedirect(reverse('orders_admin:order_list'))

        # Prefer manual input if valid
        if manual_quantity is not None:
            try:
                quantity = int(manual_quantity)
                if quantity >= 0:
                    variant.stock_quantity = quantity
            except ValueError:
                messages.error(request, "Invalid stock quantity.")
                query_params = {
                    'tab': request.GET.get('tab', 'inventory'),
                    'variant_page': request.GET.get('variant_page'),
                    'search': request.GET.get('search'),
                    'availability': request.GET.get('availability'),
                }
                clean_query = {k: v for k, v in query_params.items() if v}
                return redirect(f"{reverse('orders_admin:order_list')}?{urlencode(clean_query)}")
        else:
            # Increment/decrement logic
            if action == "increase":
                variant.stock_quantity += 1
            elif action == "decrease" and variant.stock_quantity > 0:
                variant.stock_quantity -= 1

        variant.save(update_fields=["stock_quantity"])

        # ✅ Automatically update availability after any stock change
        variant.update_availability_status()

        logger.info(f"[INVENTORY] Updated variant {variant} by {request.user}")
        messages.success(request, f"Updated inventory for {variant}")

        query_params = {
            'tab': request.GET.get('tab', 'inventory'),
            'variant_page': request.GET.get('variant_page'),
            'search': request.GET.get('search'),
            'availability': request.GET.get('availability'),
        }

        # Clean up None values
        clean_query = {k: v for k, v in query_params.items() if v}

        # Redirect to inventory tab with preserved context
        return redirect(f"{reverse('orders_admin:order_list')}?{urlencode(clean_query)}")