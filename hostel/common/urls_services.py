from django.urls import path
from . import views

urlpatterns = [
    path('', views.view_services, name='services'),
    path('<int:service_id>/', views.service_view, name='service'),
    path('<int:service_id>/update/', views.service_update, name='update_service'),
    path('create/', views.service_create, name='create_service'),
    path('<int:service_id>/choose_doc/', views.choose_doc_for_service, name='choose_doc_for_service'),

    path('<int:service_id>/subservices/<int:subservice_id>/update/', views.subservice_update, name='update_subservice'),
    path('<int:service_id>/subservices/<int:subservice_id>/', views.subservice_view, name='subservice'),

    path('<int:service_id>/subservices/<int:subservice_id>/create_vlan/',
         views.subservice_create_vlan_view,
         name='subservice_create_vlan'),

    path('<int:service_id>/subservices/<int:subservice_id>/choose_vlan/',
         views.subservice_choose_vlan_view,
         name='subservice_choose_vlan'),

    path('<int:service_id>/subservices/<int:subservice_id>/choose_lease/',
         views.subservice_choose_lease_view,
         name='subservice_choose_lease'),

    path('<int:service_id>/subservices/<int:subservice_id>/create_lease/',
         views.subservice_create_lease_view,
         name='subservice_create_lease'),

    path('<int:service_id>/create_subservice/', views.subservice_create, name='create_subservice'),

]
