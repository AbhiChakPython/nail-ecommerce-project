from django.db import models
from django.contrib.auth import get_user_model
from logs.logger import get_logger
logger = get_logger(__name__)

User = get_user_model()


class ReportLog(models.Model):
    REPORT_TYPES = [
        ('SALES', 'Sales Summary'),
        ('EXPORT', 'CSV Export'),
        ('SEGMENT', 'Customer Segmentation'),
        ('PREDICT', 'Booking Prediction'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_report_type_display()} by {self.user} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class AnalyticsExportLog(models.Model):
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE)
    export_type = models.CharField(max_length=50)  # e.g. 'sales', 'customer_segmentation'
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.admin_user} | {self.export_type} | {self.timestamp}"