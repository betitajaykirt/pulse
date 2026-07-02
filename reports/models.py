from django.db import models


class BarangayRiskLog(models.Model):
    RISK_LEVEL_CHOICES = [
        ('Low', 'Low'),
        ('Moderate', 'Moderate'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]

    barangay = models.CharField(max_length=100)
    syndrome = models.CharField(max_length=100)
    anomaly_score = models.FloatField(default=0.0)
    temporal_score = models.FloatField(default=0.0)
    environmental_score = models.FloatField(default=0.0)
    spatial_score = models.FloatField(default=0.0)
    final_risk_score = models.FloatField(default=0.0)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='Low')
    is_active_alert = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'barangay_risk_logs'
        ordering = ['-final_risk_score', '-created_at']
        indexes = [
            models.Index(fields=['barangay', 'syndrome']),
            models.Index(fields=['is_active_alert', '-created_at']),
        ]

    def __str__(self):
        return f'{self.barangay} - {self.syndrome} ({self.risk_level})'
