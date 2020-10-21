from django.urls import path
from . import views

urlpatterns = [
    path('', views.city_list, name='cities'),
    path('<int:city_id>/', views.city_view, name='city'),
    path('<int:city_id>/update/', views.city_update),
    path('create/', views.city_create, name='create_city'),
    path('delete/', views.city_delete, name='delete_city'),
]
