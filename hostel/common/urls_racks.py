from django.urls import path
from . import views

urlpatterns = [
    path('', views.rack_list, name='racks'),
    path('<int:rack_id>/', views.rack_view, name='rack'),
    path('<int:rack_id>/update/', views.rack_update, name='rack_update'),
    path('create/', views.rack_create, name='create_rack'),
]
