from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_list, name='clients'),
    path('netname/<netname>', views.client_netname_view, name='client_netname'),
    path('<int:client_id>/', views.client_view, name='client'),
    path('<int:client_id>/update/', views.client_update, name='update_client'),
    path('<int:client_id>/export_services/', views.export_services, name='export_services'),
    path('<int:client_id>/request_service/', views.request_service, name='request_service'),
    path('add/', views.client_create, name='add_client'),
    path('delete/', views.client_delete, name='delete_client'),
]
