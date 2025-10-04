import plotly
from django.http import HttpResponse
import csv
from datetime import datetime
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
import plotly.express as px
from django.utils.timezone import make_aware, is_naive
import json
import plotly.graph_objs as go

from nail_ecommerce_project.apps.analytics.models import ReportLog, AnalyticsExportLog
from nail_ecommerce_project.apps.analytics.utils import get_sales_data, get_customer_segments, get_customer_clusters, \
    get_time_series_forecast, get_top_products_vs_services, get_low_stock_products, get_forecast_data
from logs.logger import get_logger

logger = get_logger(__name__)


def superuser_required(view_func):
    return login_required(user_passes_test(lambda u: u.is_superuser)(view_func))


@method_decorator(superuser_required, name='dispatch')
class DashboardView(View):
    def get(self, request):
        try:
            start_date_str = request.GET.get('start_date')
            end_date_str = request.GET.get('end_date')

            # 🗓️ Default: last 30 days
            if not (start_date_str and end_date_str):
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=30)
                logger.info("No date filter provided. Using default: last 30 days.")
            else:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            if is_naive(start_date := datetime.combine(start_date, datetime.min.time())):
                start_date = make_aware(start_date)
            if is_naive(end_date := datetime.combine(end_date, datetime.max.time())):
                end_date = make_aware(end_date)

            logger.info(f"[DashboardView] Using timezone-aware start_date: {start_date}, end_date: {end_date}")

            data = get_sales_data(start_date, end_date)

            # 🔢 Plotly product revenue chart
            product_chart = go.Figure(data=[
                go.Bar(x=data['product_chart']['labels'], y=data['product_chart']['revenue'],
                       marker_color='rgba(236, 72, 153, 0.8)')
            ])
            product_chart.update_layout(title='Product Revenue', margin=dict(t=30))
            product_chart_json = f"<script>Plotly.newPlot('product-chart', {json.dumps(product_chart, cls=plotly.utils.PlotlyJSONEncoder)});</script>"

            # 🔢 Plotly booking revenue chart
            booking_chart = go.Figure(data=[
                go.Pie(labels=data['booking_chart']['labels'], values=data['booking_chart']['revenue'], hole=0.4)
            ])
            booking_chart.update_layout(title='Booking Revenue')
            booking_chart_json = f"<script>Plotly.newPlot('booking-chart', {json.dumps(booking_chart, cls=plotly.utils.PlotlyJSONEncoder)});</script>"

            # 🚀 Customer Clusters (KMeans)
            customer_data = get_customer_clusters(start_date, end_date)

            # Revenue by Customer (Pie)
            customer_pie = go.Figure(data=[
                go.Pie(labels=customer_data['names'], values=customer_data['revenue'], hole=0.4)
            ])
            customer_pie.update_layout(title='Top Customer Revenue Share')
            customer_pie_json = f"<script>Plotly.newPlot('customer-pie', {json.dumps(customer_pie, cls=plotly.utils.PlotlyJSONEncoder)});</script>"

            # Chart 4: Visit Frequency (Bar)
            visit_bar = go.Figure(data=[
                go.Bar(x=customer_data['names'], y=customer_data['visits'], marker_color='rgba(139, 92, 246, 0.8)')
            ])
            visit_bar.update_layout(title='Customer Visit Frequency', margin=dict(t=30))
            visit_bar_json = f"<script>Plotly.newPlot('visit-bar', {json.dumps(visit_bar, cls=plotly.utils.PlotlyJSONEncoder)});</script>"

            # 🧠 Customer Segments
            customer_segments = get_customer_segments(start_date, end_date)

            context = {
                'sales_data': data['summary'],
                'product_chart_json': product_chart_json,
                'booking_chart_json': booking_chart_json,
                'customer_pie_json': customer_pie_json,
                'visit_bar_json': visit_bar_json,
                'customer_segments': customer_segments,
            }

            context.update({
                'start_date': start_date,
                'end_date': end_date,
                'request': request,
            })

            # Add inside the try block, after other context prep
            order_df, booking_df = get_time_series_forecast(start_date, end_date)

            forecast_order_chart = go.Figure()
            forecast_order_chart.add_trace(go.Scatter(x=order_df['created_at'], y=order_df['count'],
                                                      mode='lines+markers', name='Orders',
                                                      line=dict(color='rgba(236, 72, 153, 0.9)')))
            forecast_order_chart.update_layout(title='Daily Product Orders')

            forecast_booking_chart = go.Figure()
            forecast_booking_chart.add_trace(go.Scatter(x=booking_df['created_at'], y=booking_df['count'],
                                                        mode='lines+markers', name='Bookings',
                                                        line=dict(color='rgba(139, 92, 246, 0.9)')))
            forecast_booking_chart.update_layout(title='Daily Service Bookings')

            forecast_order_chart_json = f"<script>Plotly.newPlot('forecast-order', {json.dumps(forecast_order_chart, cls=plotly.utils.PlotlyJSONEncoder)});</script>"
            forecast_booking_chart_json = f"<script>Plotly.newPlot('forecast-booking', {json.dumps(forecast_booking_chart, cls=plotly.utils.PlotlyJSONEncoder)});</script>"

            # Add to context
            context.update({
                'forecast_order_chart_json': forecast_order_chart_json,
                'forecast_booking_chart_json': forecast_booking_chart_json
            })

            # Product vs Service Comparison
            comparison_data = get_top_products_vs_services(start_date, end_date)

            comparison_chart = go.Figure()
            comparison_chart.add_trace(go.Bar(
                x=comparison_data['product']['labels'],
                y=comparison_data['product']['revenue'],
                name='Products',
                marker_color='rgba(236, 72, 153, 0.9)'
            ))
            comparison_chart.add_trace(go.Bar(
                x=comparison_data['service']['labels'],
                y=comparison_data['service']['revenue'],
                name='Services',
                marker_color='rgba(34, 197, 94, 0.8)'
            ))
            comparison_chart.update_layout(barmode='group', title='Top 5 Products vs Services Revenue')

            comparison_chart_json = f"<script>Plotly.newPlot('product-service-comparison', {json.dumps(comparison_chart, cls=plotly.utils.PlotlyJSONEncoder)});</script>"

            context.update({
                'comparison_chart_json': comparison_chart_json
            })

            # 🚨 Low Stock Report
            low_stock_data = get_low_stock_products()
            context['low_stock_data'] = low_stock_data

            # 📈 Forecast Chart
            df = get_forecast_data(start_date, end_date)

            if not df.empty:
                forecast_chart = px.line(
                    df,
                    x='date',
                    y='revenue',
                    color='type',
                    markers=True,
                    title='Revenue Over Time'
                )
                forecast_chart.update_layout(margin=dict(t=30, b=20))
                forecast_chart_json = f"<script>Plotly.newPlot('forecast-chart', {json.dumps(forecast_chart, cls=plotly.utils.PlotlyJSONEncoder)});</script>"
            else:
                forecast_chart_json = ""

            context['forecast_chart_json'] = forecast_chart_json

            ReportLog.objects.create(
                user=request.user,
                report_type='SALES',
                notes=f"Dashboard viewed for {start_date} to {end_date}"
            )

            logger.debug(f"Product chart data: {data['product_chart']}")
            logger.debug(f"Booking chart data: {data['booking_chart']}")
            logger.debug(f"Customer pie chart: names={customer_data['names']}, revenue={customer_data['revenue']}")

            return render(request, 'analytics/dashboard.html', context)


        except Exception as e:

            logger.error(f"DashboardView error: {e}")

            end_date = datetime.today().date()

            start_date = end_date - timedelta(days=30)

            return render(request, 'analytics/dashboard.html', {
                'sales_data': None,
                'start_date': start_date,
                'end_date': end_date,
                'request': request
            })


@superuser_required
def export_csv_view(request):
    try:
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        if not (start_date_str and end_date_str):
            logger.warning("Export CSV: Missing date parameters.")
            return HttpResponse("Missing date parameters", status=400)

        # Convert to date objects
        raw_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        raw_end = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # Convert to aware datetime
        start_dt = make_aware(datetime.combine(raw_start, datetime.min.time()))
        end_dt = make_aware(datetime.combine(raw_end, datetime.max.time()))

        logger.info(f"[Export CSV] Using timezone-aware range: {start_dt} to {end_dt}")

        data = get_sales_data(start_dt, end_dt)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{raw_start}_{raw_end}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Type', 'Item', 'Total Revenue'])

        # 📦 Products
        product_labels = data.get('product_chart', {}).get('labels', [])
        product_revenue = data.get('product_chart', {}).get('revenue', [])
        for name, rev in zip(product_labels, product_revenue):
            writer.writerow(['Product', name, rev])

        # 💅 Services / Bookings
        booking_labels = data.get('booking_chart', {}).get('labels', [])
        booking_revenue = data.get('booking_chart', {}).get('revenue', [])
        for name, rev in zip(booking_labels, booking_revenue):
            writer.writerow(['Service', name, rev])

        # ✅ Log export success
        AnalyticsExportLog.objects.create(
            admin_user=request.user,
            export_type='sales',
            success=True
        )

        logger.info(f"[Export CSV] Export successful for {raw_start} to {raw_end}")
        return response

    except Exception as e:
        logger.exception(f"[Export CSV] Error during CSV export: {e}")

        # ❌ Log failure
        AnalyticsExportLog.objects.create(
            admin_user=request.user,
            export_type='sales',
            success=False,
            error_message=str(e)
        )

        return HttpResponse("Error generating CSV", status=500)
