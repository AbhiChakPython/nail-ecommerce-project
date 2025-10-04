from collections import defaultdict
from django.db.models import Count, Max
from decimal import Decimal
from nail_ecommerce_project.apps.orders.models import OrderItem
from django.db.models import F, ExpressionWrapper, DecimalField
from nail_ecommerce_project.apps.bookings.models import BookingStatus
from django.utils.timezone import make_aware, is_naive
from django.db.models import Sum, Value, CharField
from django.db.models.functions import TruncDate
import pandas as pd
from sklearn.cluster import KMeans
from django.contrib.auth import get_user_model
from nail_ecommerce_project.apps.orders.models import Order
from nail_ecommerce_project.apps.bookings.models import Booking
from logs.logger import get_logger
from nail_ecommerce_project.apps.products.models import ProductVariant

logger = get_logger(__name__)

User = get_user_model()


def get_sales_data(start_date, end_date):
    try:
        if is_naive(start_date):
            logger.warning(f"[function_name] start_date is naive: {start_date}")
            start_date = make_aware(start_date)

        if is_naive(end_date):
            logger.warning(f"[function_name] end_date is naive: {end_date}")
            end_date = make_aware(end_date)

        logger.info(f"[get_sales_data] Fetching sales data from {start_date} to {end_date}")

        # 🛍️ Orders
        order_items = (
            OrderItem.objects
            .filter(order__created_at__range=(start_date, end_date), order__status__in=['DELIVERED', 'PROCESSING'])
            .select_related('order', 'product_variant', 'product_variant__product')
            .values(
                'order_id', 'product_variant__product__name',
                'quantity', 'product_variant__price',
            )
        )

        df_orders = pd.DataFrame(order_items)

        logger.debug(f"[get_sales_data] Orders raw data:\n{df_orders.head()}")

        if not df_orders.empty:
            df_orders['revenue'] = df_orders['quantity'] * df_orders['product_variant__price']
            order_summary = {
                'count': int(df_orders['quantity'].sum()),
                'revenue': round(df_orders['revenue'].sum(), 2),
            }
            product_revenue = (
                df_orders.groupby('product_variant__product__name')['revenue']
                .sum().sort_values(ascending=False)
            )
            logger.debug(f"[get_sales_data] Product revenue breakdown:\n{product_revenue}")
        else:
            order_summary = {'count': 0, 'revenue': Decimal('0.00')}
            product_revenue = pd.Series(dtype='float64')

        # 💅 Bookings
        bookings = (
            Booking.objects
            .filter(date__range=(start_date, end_date), status=BookingStatus.COMPLETED_SERVICE)
            .select_related('service')
            .values('service__title', 'number_of_customers', 'service__price')
        )

        df_bookings = pd.DataFrame(bookings)
        logger.debug(f"[get_sales_data] Bookings raw data:\n{df_bookings.head()}")

        if not df_bookings.empty:
            df_bookings['total_price'] = df_bookings.apply(
                lambda row: get_booking_price(row['service__price'], row['number_of_customers']), axis=1
            )
            booking_summary = {
                'count': df_bookings.shape[0],
                'revenue': round(df_bookings['total_price'].sum(), 2),
            }
            booking_revenue = (
                df_bookings.groupby('service__title')['total_price']
                .sum().sort_values(ascending=False)
            )
            logger.debug(f"[get_sales_data] Booking revenue breakdown:\n{booking_revenue}")
        else:
            booking_summary = {'count': 0, 'revenue': Decimal('0.00')}
            booking_revenue = pd.Series(dtype='float64')

        # 🧾 Total Summary
        total_revenue = order_summary['revenue'] + booking_summary['revenue']
        estimated_profit = round(total_revenue * Decimal('0.25'), 2)
        logger.info(f"[get_sales_data] Final revenue: ₹{total_revenue}, Estimated profit: ₹{estimated_profit}")

        return {
            'orders': order_summary,
            'bookings': booking_summary,  # Summary only
            'totals': {
                'revenue': total_revenue,
                'estimated_profit': estimated_profit,
            },
            'product_chart': {
                'labels': list(product_revenue.index),
                'revenue': list(product_revenue.values),
            },
            'booking_chart': {
                'labels': list(booking_revenue.index),
                'revenue': list(booking_revenue.values),
            },
            'summary': {
                'orders': order_summary,
                'bookings': booking_summary,
                'totals': {
                    'revenue': total_revenue,
                    'estimated_profit': estimated_profit,
                }
            }
        }

    except Exception as e:
        logger.error(f"[Analytics] Failed to get sales data: {e}")
        return {
            'orders': {'count': 0, 'revenue': Decimal('0.00')},
            'bookings': {'count': 0, 'revenue': Decimal('0.00')},
            'totals': {'revenue': Decimal('0.00'), 'estimated_profit': Decimal('0.00')},
            'product_chart': {'labels': [], 'revenue': []},
            'booking_chart': {'labels': [], 'revenue': []},
            'summary': None,
        }


def get_booking_price(price, num_customers):
    try:
        logger.debug(f"[get_booking_price] Price: {price}, Customers: {num_customers}")
        base_price = Decimal(price)
        if 2 <= num_customers <= 5:
            final_price = base_price * Decimal('0.95')
        else:
            final_price = base_price
        logger.debug(f"[get_booking_price] Final computed price: {final_price}")
        return final_price
    except Exception as e:
        logger.warning(f"Failed to compute booking price: {e}")
        return Decimal('0.00')


def get_customer_segments(start_date, end_date):
    """
    Returns top customer insights based on orders and bookings within the date range.
    """
    if is_naive(start_date):
        logger.warning(f"[function_name] start_date is naive: {start_date}")
        start_date = make_aware(start_date)

    if is_naive(end_date):
        logger.warning(f"[function_name] end_date is naive: {end_date}")
        end_date = make_aware(end_date)
    logger.info(f"[get_customer_segments] Generating segments from {start_date} to {end_date}")

    order_data = (
        Order.objects.filter(created_at__range=(start_date, end_date))
        .values('user__id', 'user__full_name', 'user__email')
        .annotate(
            total_spent=Sum('items__product_variant__price'),
            order_count=Count('id'),
            last_order=Max('created_at')
        )
    )
    logger.debug(f"[get_customer_segments] Order data count: {order_data.count()}")

    booking_data = (
        Booking.objects.filter(created_at__range=(start_date, end_date))
        .values('customer__id', 'customer__full_name', 'customer__email')
        .annotate(
            total_spent=Sum('service__price'),
            booking_count=Count('id'),
            last_booking=Max('created_at')
        )
    )
    logger.debug(f"[get_customer_segments] Booking data count: {booking_data.count()}")

    customer_dict = defaultdict(lambda: {
        'name': '',
        'email': '',
        'total_spent': 0,
        'order_count': 0,
        'booking_count': 0,
        'last_activity': None
    })

    # Merge Order Data
    for entry in order_data:
        user_id = entry['user__id']
        customer_dict[user_id]['name'] = entry['user__full_name']
        customer_dict[user_id]['email'] = entry['user__email']
        customer_dict[user_id]['total_spent'] += entry['total_spent'] or 0
        customer_dict[user_id]['order_count'] += entry['order_count']
        customer_dict[user_id]['last_activity'] = entry['last_order']

    # Merge Booking Data
    for entry in booking_data:
        user_id = entry['customer__id']
        customer_dict[user_id]['name'] = entry['customer__full_name']
        customer_dict[user_id]['email'] = entry['customer__email']
        customer_dict[user_id]['total_spent'] += entry['total_spent'] or 0
        customer_dict[user_id]['booking_count'] += entry['booking_count']
        current_last = customer_dict[user_id]['last_activity']
        new_last = entry['last_booking']
        customer_dict[user_id]['last_activity'] = max(current_last, new_last) if current_last else new_last

    # Convert to sorted list by spend
    customer_segments = sorted(customer_dict.values(), key=lambda x: x['total_spent'], reverse=True)
    logger.debug(f"[get_customer_segments] Top 5 customers: {customer_segments[:5]}")

    return customer_segments


def get_customer_clusters(start_date=None, end_date=None):
    try:
        if is_naive(start_date):
            logger.warning(f"[function_name] start_date is naive: {start_date}")
            start_date = make_aware(start_date)

        if is_naive(end_date):
            logger.warning(f"[function_name] end_date is naive: {end_date}")
            end_date = make_aware(end_date)

        users = User.objects.filter(role='customer')
        data = []

        if start_date and end_date:
            from datetime import datetime
            from django.utils import timezone

            start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
            end_dt = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
        else:
            start_dt = end_dt = None
        logger.info(f"[get_customer_clusters] Clustering customers between {start_dt} and {end_dt}")

        for user in users:
            orders = Order.objects.filter(user=user)
            bookings = Booking.objects.filter(customer=user)

            if start_dt and end_dt:
                orders = orders.filter(created_at__range=(start_dt, end_dt))
                bookings = bookings.filter(created_at__range=(start_dt, end_dt))

            for o in orders:
                try:
                    val = o.total_price
                    logger.debug(f"[DEBUG] Order #{o.id} total_price = ₹{val}")
                except Exception as e:
                    logger.error(f"[DEBUG] Error accessing total_price for Order #{o.id}: {e}")

            total_order_amount = sum(o.total_price for o in orders)
            order_count = orders.count()
            booking_count = bookings.count()
            total_value = total_order_amount
            total_visits = order_count + booking_count
            avg_order_value = (total_order_amount / order_count) if order_count else 0

            if total_visits == 0:
                continue

            data.append({
                'user_id': user.id,
                'name': user.get_full_name() or user.username,
                'total_value': float(total_value),
                'frequency': total_visits,
                'avg_order_value': float(avg_order_value)
            })
        logger.debug(f"[get_customer_clusters] Prepared {len(data)} customer data points for clustering")

        if not data:
            return {
                'df': None,
                'labels': [],
                'cluster_data': [],
                'names': [],
                'revenue': [],
                'visits': []
            }

        df = pd.DataFrame(data)
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(df[['total_value', 'frequency', 'avg_order_value']])
        logger.debug(f"[get_customer_clusters] Cluster assignment result:\n{df[['name', 'cluster']]}")

        return {
            'df': df,
            'labels': df['cluster'].unique().tolist(),
            'cluster_data': df.to_dict(orient='records'),
            'names': df['name'].tolist(),
            'revenue': df['total_value'].tolist(),
            'visits': df['frequency'].tolist()
        }

    except Exception as e:
        logger.error(f"[Customer Segmentation] Failed to cluster users: {e}")
        return {
            'df': None,
            'labels': [],
            'cluster_data': [],
            'names': [],
            'revenue': [],
            'visits': []
        }


def get_time_series_forecast(start_date, end_date):
    try:
        if is_naive(start_date):
            logger.warning(f"[function_name] start_date is naive: {start_date}")
            start_date = make_aware(start_date)

        if is_naive(end_date):
            logger.warning(f"[function_name] end_date is naive: {end_date}")
            end_date = make_aware(end_date)

        logger.info(f"[get_time_series_forecast] Fetching time series data from {start_date} to {end_date}")

        # Orders data
        order_qs = Order.objects.filter(created_at__range=(start_date, end_date))
        order_df = pd.DataFrame(list(order_qs.values('created_at', 'id')))
        order_df['created_at'] = pd.to_datetime(order_df['created_at']).dt.date
        order_df = order_df.groupby('created_at').size().reset_index(name='count')

        # Bookings data
        booking_qs = Booking.objects.filter(created_at__range=(start_date, end_date))
        booking_df = pd.DataFrame(list(booking_qs.values('created_at', 'id')))
        booking_df['created_at'] = pd.to_datetime(booking_df['created_at']).dt.date
        booking_df = booking_df.groupby('created_at').size().reset_index(name='count')

        logger.debug(f"[get_time_series_forecast] Orders daily breakdown:\n{order_df}")
        logger.debug(f"[get_time_series_forecast] Bookings daily breakdown:\n{booking_df}")

        return order_df, booking_df

    except Exception as e:
        logger.error(f"[Forecast] Error in get_time_series_forecast: {e}")
        return pd.DataFrame(), pd.DataFrame()


def get_top_products_vs_services(start_date, end_date):
    try:
        if is_naive(start_date):
            logger.warning(f"[function_name] start_date is naive: {start_date}")
            start_date = make_aware(start_date)

        if is_naive(end_date):
            logger.warning(f"[function_name] end_date is naive: {end_date}")
            end_date = make_aware(end_date)

        logger.info(
            f"[get_top_products_vs_services] Comparing top products and services from {start_date} to {end_date}")

        # Product sales
        revenue_expr = ExpressionWrapper(F('product_variant__price') * F('quantity'), output_field=DecimalField())
        product_sales = (
            OrderItem.objects
            .filter(order__created_at__range=(start_date, end_date))
            .values('product_variant__product__name')
            .annotate(
                revenue=Sum(revenue_expr),
                quantity=Sum('quantity')
            )
            .order_by('-revenue')[:5]
        )

        # Service bookings
        service_sales = (
            Booking.objects.filter(created_at__range=(start_date, end_date))
            .values('service__title')
            .annotate(
                revenue=Sum('service__price'),
                count=Count('id')
            )
            .order_by('-revenue')[:5]
        )

        product_names = [p['product_variant__product__name'] for p in product_sales]
        product_revenues = [float(p['revenue']) for p in product_sales]

        service_names = [s['service__title'] for s in service_sales]
        service_revenues = [float(s['revenue']) for s in service_sales]

        logger.debug(f"[get_top_products_vs_services] Top 5 Products: {list(zip(product_names, product_revenues))}")
        logger.debug(f"[get_top_products_vs_services] Top 5 Services: {list(zip(service_names, service_revenues))}")

        return {
            'product': {'labels': product_names, 'revenue': product_revenues},
            'service': {'labels': service_names, 'revenue': service_revenues},
        }

    except Exception as e:
        logger.error(f"[Analytics] Product vs Service Comparison failed: {e}")
        return {
            'product': {'labels': [], 'revenue': []},
            'service': {'labels': [], 'revenue': []}
        }


def get_low_stock_products(threshold=5):
    try:
        logger.info(f"[get_low_stock_products] Checking stock below threshold: {threshold}")

        low_stock_items = (
            ProductVariant.objects.filter(stock_quantity__lt=threshold)
            .select_related('product')
            .values(
                'product__name',
                'size',
                'color',
                'stock_quantity',
                'price'
            )
            .order_by('stock_quantity')
        )
        logger.debug(f"[get_low_stock_products] Found {len(low_stock_items)} low stock items.")

        return list(low_stock_items)
    except Exception as e:
        logger.error(f"[Analytics] Low stock check failed: {e}")
        return []


def get_forecast_data(start_date, end_date):
    try:
        if is_naive(start_date):
            logger.warning(f"[get_forecast_data] Naive start_date: {start_date}")
            start_date = make_aware(start_date)
        if is_naive(end_date):
            logger.warning(f"[get_forecast_data] Naive end_date: {end_date}")
            end_date = make_aware(end_date)

        logger.info(f"[get_forecast_data] Generating forecast chart data from {start_date} to {end_date}")

        # --- Orders ---
        order_qs = (
            Order.objects.filter(created_at__range=(start_date, end_date))
            .annotate(trunc_date=TruncDate('created_at'))
            .values('trunc_date')
            .annotate(
                revenue=Sum('items__price_at_order'),
                type=Value('Orders', output_field=CharField())
            )
            .order_by('trunc_date')
        )

        # --- Bookings ---
        bookings = (
            Booking.objects.filter(created_at__range=(start_date, end_date))
            .annotate(trunc_date=TruncDate('created_at'))
        )

        # Calculate total revenue per trunc_date manually
        booking_data = {}
        for b in bookings:
            key = b.trunc_date
            revenue = b.get_final_price()
            booking_data.setdefault(key, Decimal('0.00'))
            booking_data[key] += revenue

        logger.debug(f"[get_forecast_data] Aggregated booking revenue: {booking_data}")

        # Convert to list of dicts
        booking_qs = [
            {'trunc_date': k, 'revenue': v, 'type': 'Bookings'}
            for k, v in sorted(booking_data.items())
        ]

        # --- Convert to DataFrame ---
        df_orders = pd.DataFrame(order_qs)
        df_bookings = pd.DataFrame(booking_qs)

        df = pd.concat([df_orders, df_bookings], ignore_index=True)
        df.rename(columns={"trunc_date": "date"}, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df['revenue'] = df['revenue'].fillna(0)

        logger.debug(f"[get_forecast_data] Final DataFrame:\n{df}")

        return df

    except Exception as e:
        logger.error(f"[Analytics] Forecast data error: {e}")
        return pd.DataFrame()
