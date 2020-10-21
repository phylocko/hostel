from django.urls import path
from . import views

urlpatterns = [
    path('', views.spy_list, name='spy'),
]
