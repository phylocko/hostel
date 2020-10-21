from django.urls import path
from . import views

urlpatterns = [
    # agreements
    path('', views.view_agreements, name='agreements'),
    path('<int:agreement_id>/', views.view_agreement, name='agreement'),
    path('<int:agreement_id>/update/', views.update_agreement, name='update_agreement'),

    path('<int:agreement_id>/applications/', views.view_agreement_applications, name='agreement_applications'),
    path('<int:agreement_id>/orders/', views.view_agreement_orders, name='agreement_orders'),
    path('<int:agreement_id>/preview/', views.view_agreement_preview, name='agreement_preview'),

    path('delete_agreement_file/', views.delete_agreement_file),

    path('applications/<int:application_id>/', views.view_application, name='application'),
    path('applications/<int:application_id>/update/', views.update_application, name='update_application'),

    path('add_agreement/', views.add_agreement, name='add_agreement'),
    path('<int:agreement_id>/applications/add/', views.add_application, name='add_application'),
    path('search/', views.search_agreement, name='search_agreement'),
    path('delete_agreement/', views.delete_agreement, name='delete_agreement'),
    path('delete_application/', views.delete_application, name='delete_application'),
]
