from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
import re
from django.core.paginator import Paginator
from .models import Order
from logs.logger import get_logger

logger = get_logger(__name__)


class CustomerOrderListView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        search_query = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '')
        page = request.GET.get('page', 1)

        orders = Order.objects.filter(user=user).prefetch_related('items__product_variant__product')
        invalid_order_search = False
        no_orders_found = False

        # Determine if search_query is order number or product name
        order_id = self.extract_order_id(search_query)

        if search_query:
            if order_id:
                orders = orders.filter(id=order_id)
            else:
                # Search in product names (partial match)
                orders = orders.filter(items__product_variant__product__name__icontains=search_query)
                if not orders.exists():
                    invalid_order_search = True
        if status_filter:
            orders = orders.filter(status=status_filter)

        if not orders.exists() and not invalid_order_search:
            no_orders_found = True

        paginator = Paginator(orders.distinct(), 10)
        page_obj = paginator.get_page(page)

        return render(request, 'orders/order_list.html', {
            'orders': page_obj.object_list,
            'page_obj': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
            'invalid_order_search': invalid_order_search,
            'no_orders_found': no_orders_found,
        })

    def extract_order_id(self, search_term):
        # Match 'Order #49', '49', 'order no 49', etc.
        match = re.search(r'\b(\d{1,6})\b', search_term)
        return int(match.group(1)) if match else None


class UserCancelOrderView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)

        if order.status not in ['PENDING', 'PROCESSING']:
            messages.error(
                request,
                f"❌ Order #{order.id} cannot be cancelled because it is currently in '{order.status}' stage."
            )
            return redirect('orders:order_list')

        if order.status == 'CANCELLED':
            messages.info(
                request,
                f"ℹ️ Order #{order.id} has already been cancelled."
            )
            return redirect('orders:order_list')

        # Proceed with centralized cancellation
        order.cancel_order(by_customer=True)

        messages.success(
            request,
            f"✅ Order #{order.id} has been successfully cancelled. Stage: {order.status}."
        )
        return redirect('orders:order_list')
