from django.db import models

class AppNotification(models.Model):
    alert_id = models.IntegerField(null=True, blank=True)
    disease = models.CharField(max_length=150)
    barangay_name = models.CharField(max_length=100)
    severity_level = models.CharField(max_length=50) # Moderate, High, Critical
    
    final_risk_score = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    anomaly_score = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    environmental_factor = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    
    spatial_metric = models.TextField(null=True, blank=True)
    temporal_metric = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app_notifications'
        managed = True

class AppNotificationRead(models.Model):
    notification = models.ForeignKey(AppNotification, on_delete=models.CASCADE, related_name='reads')
    user_id = models.IntegerField()
    user_type = models.CharField(max_length=50) # e.g. role or table identifier
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app_notification_reads'
        managed = True
        unique_together = ('notification', 'user_id', 'user_type')
