from django.contrib import admin

from .models import BarangayRiskLog


@admin.register(BarangayRiskLog)
class BarangayRiskLogAdmin(admin.ModelAdmin):
  list_display = (
    'barangay', 'syndrome', 'risk_level', 'final_risk_score',
    'is_active_alert', 'created_at',
  )
  list_filter = ('risk_level', 'is_active_alert', 'barangay', 'syndrome')
  search_fields = ('barangay', 'syndrome')
  ordering = ('-created_at',)
