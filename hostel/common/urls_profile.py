from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile_view, name='profile'),
    path('change-password/', views.change_profile_password, name='change-password'),
]