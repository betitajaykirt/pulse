from django.urls import path
from . import views

urlpatterns = [
    path('submit/',                     views.submit_report,    name='submit_report'),
    path('my/',                         views.my_reports,       name='my_reports'),
    path('records/',                    views.case_records,     name='case_records'),
    path('records/<int:report_id>/validate/', views.validate_report, name='validate_report'),
    path('records/<int:report_id>/confirm/',  views.confirm_case,     name='confirm_case'),
    path('confirm-cases/',                  views.admin_confirmation_panel, name='admin_confirmation_panel'),
    path('incidents/',                  views.incident_reports, name='incident_reports'),
    path('api/recent/',                 views.api_recent_reports, name='api_recent_reports'),
]
