from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('logs/', views.system_logs_view, name='system_logs'),
    path('alerts/', views.alerts_inbox_view, name='alerts_inbox'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('api/analytics/', views.api_analytics_data, name='api_analytics'),
    path('api/alerts/aptas/', views.api_alerts_aptas, name='api_alerts_aptas'),
    path('api/alerts/<int:alert_id>/acknowledge/', views.api_alert_acknowledge, name='api_alert_acknowledge'),
    path('outbreak-thresholds/', views.outbreak_thresholds_view, name='outbreak_thresholds'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/notifications/<int:notif_id>/read/', views.api_notification_read, name='api_notification_read'),
    path('nurse/', views.nurse_dashboard_view, name='nurse_dashboard'),
    path('nurse/api/dispatch-task/', views.api_dispatch_task, name='api_dispatch_task'),
    path('nurse/manage-bhws/', views.manage_bhws_view, name='manage_bhws'),
    path('nurse/bhw-reports/', views.bhw_reports_view, name='bhw_reports'),
    path('bhw/tasks/', views.bhw_tasks_view, name='bhw_tasks'),
    path('bhw/api/task/<int:task_id>/done/', views.api_task_mark_done, name='api_task_mark_done'),
    path('bhw/api/task/<int:task_id>/in-progress/', views.api_task_acknowledge, name='api_task_acknowledge'),
]

