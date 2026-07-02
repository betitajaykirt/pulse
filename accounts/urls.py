from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.login_view,                name='login'),
    path('login',                   views.login_view,                name='login_alt'),
    path('logout',                  views.logout_view,               name='logout'),
    path('first-login/set-password', views.first_login_set_password, name='first_login_set_password'),
]
