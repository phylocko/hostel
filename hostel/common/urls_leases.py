from django.urls import path
from . import views

urlpatterns = [
    path('', views.lease_list, name='leases'),

    path('<int:lease_id>/', views.lease_view, name='lease'),

    path('<int:lease_id>/update/', views.lease_update, name='update_lease'),
    path('create/', views.lease_create, name='create_lease'),
    path('delete/', views.lease_delete, name='delete_lease'),
    path('search/', views.lease_search, name='search_lease'),
    path('choose-for-service/', views.lease_choose_for_service, name='choose-lease-for-service'),
    path('release_lease/', views.lease_release_from_service, name='release_lease'),

    path('<int:lease_id>/choose_doc/', views.choose_doc_for_lease, name='choose_doc_for_lease'),

    # lease groups
    path('groups/', views.lease_groups, name='lease_groups'),
    path('groups/<int:group_id>/', views.lease_group_view, name='lease_group'),
    path('groups/<int:group_id>/update/', views.lease_group_update, name='update_lease_group'),
    path('groups/add/', views.lease_group_create, name='create_lease_group'),
]
