from django.urls import path
from . import views

urlpatterns = [
    path('', views.vlan_list, name='vlans'),
    path('<int:vlan_id>/', views.vlan_view, name='vlan'),
    path('<int:vlan_id>/services/', views.vlan_services_view, name='vlan_services'),
    path('<int:vlan_id>/nets/', views.vlan_nets_view, name='vlan_nets'),
    path('<int:vlan_id>/leases/', views.vlan_leases_view, name='vlan_leases'),
    path('<int:vlan_id>/leases/choose/', views.vlan_choose_lease_view, name='vlan_choose_lease'),
    path('<int:vlan_id>/leases/create/', views.vlan_create_lease_view, name='vlan_create_lease'),
    path('<int:vlan_id>/bundles/', views.vlan_bundles_view, name='vlan_bundles'),
    path('<int:vlan_id>/map/', views.vlan_map_view, name='vlan_map'),


    path('<int:vlan_id>/update/', views.vlan_update),
    path('add/', views.vlan_create, name='add_vlan'),
    path('search/', views.vlan_search, name='vlan_search'),
    path('delete/', views.vlan_delete, name='delete_vlan'),
    path('assign-to-service/', views.assign_to_service),
    path('create-for-service/', views.create_for_service),
]
