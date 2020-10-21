from django.urls import path
from . import views

urlpatterns = [
    path('', views.device_list, name='devices'),
    path('<int:device_id>/', views.device_view, name='device'),
    path('<int:device_id>/update/', views.device_update),
    path('add/', views.device_create, name='add_device'),
    path('search/', views.device_search, name='search_device'),
    path('delete/', views.device_delete, name='delete_device'),
]

