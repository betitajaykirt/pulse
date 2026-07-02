from django.urls import path
from . import profile_views

urlpatterns = [
    path('',              profile_views.profile_show,         name='profile'),
    path('update',        profile_views.profile_update,       name='profile_update'),
    path('photo',         profile_views.profile_upload_photo, name='profile_photo'),
    path('avatar/<str:filename>', profile_views.serve_avatar, name='serve_avatar'),
]
