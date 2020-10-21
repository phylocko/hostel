from django.urls import path
from . import views

urlpatterns = [
    path('', views.group_list, name='groups'),
    path('<int:group_id>/', views.group_view, name='group'),
    path('<int:group_id>/update/', views.group_update, name='update_group'),
    path('add/', views.group_create, name='create_group'),
]
