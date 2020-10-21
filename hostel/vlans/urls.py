from django.urls import path
from . import views

urlpatterns = [
    path('', views.vlan_list, name='vlans'),
    path('<int:vlan_id>/', views.vlan_view, name='vlan'),
    path('<int:vlan_id>/update/', views.vlan_update),
    path('add/', views.vlan_create, name='add_vlan'),
    path('search/', views.vlan_search, name='vlan_search'),
    path('delete/', views.vlan_delete, name='delete_vlan'),
    path('assign-to-service/', views.assign_to_service),
    path('create-for-service/', views.create_for_service),
]
