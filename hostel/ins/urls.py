from django.urls import path
from . import views

urlpatterns = [
    path('', views.incident_review, name='ins'),
    path('closed/', views.closed_ins, name='closed_ins'),
    path('<int:incident_id>/', views.incident_view, name='incident'),
    path('last_changed/', views.last_changed_incident, name='last_changed_ins'),

    path('<int:incident_id>/choose_clients/', views.choose_clients, name='choose_ins_clients'),
    path('<int:incident_id>/choose_subservices/', views.choose_subservices, name='choose_ins_subservices'),

    path('<int:incident_id>/notification/<int:notification_id>/', views.notification_view, name='notification'),
    path('<int:incident_id>/notification/<int:notification_id>/<netname>/',
         views.client_notification_view,
         name='client_notification'),

    path('<int:incident_id>/choose_leases/', views.choose_leases, name='choose_ins_leases'),
    path('<int:incident_id>/update/', views.incident_update),
    path('add/', views.incident_create, name='add_incident'),
    path('from_rt/', views.incident_create_from_rt, name='incident_from_rt'),
    path('outages/', views.outages, name='outages'),

    path('calc/', views.calc, name='calc'),
]
