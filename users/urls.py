from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.index,       name='users_index'),
    path('create',                  views.create,      name='users_create'),
    path('<int:user_id>/update',    views.update_role, name='users_update'),
    path('<int:user_id>/deactivate',views.deactivate,  name='users_deactivate'),
    path('<int:user_id>/reactivate',views.reactivate,  name='users_reactivate'),
]
