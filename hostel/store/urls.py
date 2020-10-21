from django.urls import path
from . import views

urlpatterns = [
    path('', views.entry_list, name='store'),
    path('<int:entry_id>/', views.entry_view, name='entry'),
    path('<int:entry_id>/update/', views.entry_update),
    path('add/', views.entry_create, name='add_entry'),
    path('delete/', views.entry_delete, name='delete_entry'),
]
