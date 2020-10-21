from django.urls import path
from . import views

urlpatterns = [
    path('', views.datacenter_list, name='datacenters'),
    path('<int:datacenter_id>/', views.datacenter_view, name='datacenter'),
    path('<int:datacenter_id>/update/', views.datacenter_update, name='update_datacenter'),
    path('create/', views.datacenter_create, name='create_datacenter'),
    path('delete/', views.datacenter_delete, name='delete_datacenter'),
]