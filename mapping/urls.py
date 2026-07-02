from django.urls import path
from . import views

urlpatterns = [
    path('',           views.map_view,          name='map_view'),
    path('api/data/',  views.api_barangay_data, name='api_barangay_data'),
    path('api/cases/', views.api_cases,         name='api_cases'),
]
