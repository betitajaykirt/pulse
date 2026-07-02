from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('logs/', views.system_logs_view, name='system_logs'),
    path('alerts/', views.alerts_inbox_view, name='alerts_inbox'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('api/analytics/', views.api_analytics_data, name='api_analytics'),
]
