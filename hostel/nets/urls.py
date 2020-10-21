from django.urls import path
from . import views

urlpatterns = [
    path('', views.view_nodes, name='nets'),
    path('<int:net_id>/', views.view_net, name='view_net'),
    path('<int:net_id>/update/', views.update_net, name='update_net'),
    path('add/', views.add_net, name='add_net'),
    path('delete/', views.delete_net, name='delete_net'),
    path('search/', views.search_nets, name='search_net'),
    path('assign-to-service/', views.assign_to_service),
    path('create-for-service/', views.create_for_service),
    path('root-nets/', views.view_root_nets, name='root-nets'),
]
