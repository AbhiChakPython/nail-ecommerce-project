from django.urls import path
from nail_ecommerce_project.apps.analytics.views_frontend import DashboardView, export_csv_view
from logs.logger import get_logger
logger = get_logger(__name__)


app_name = "analytics"

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/export/csv/', export_csv_view, name='export_csv'),
]
