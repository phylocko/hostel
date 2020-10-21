from django.urls import path
from . import views

urlpatterns = [
    path('', views.burst_home, name='burst'),
    path('sets/', views.burst_sets_view, name='burst_sets'),
    path('sets/add/', views.burst_set_add, name='add_burst_set'),
    path('sets/<int:burst_set_id>', views.burst_set_interfaces_view, name='burst_set'),
    path('sets/<int:burst_set_id>/update/', views.burst_set_update_view, name='burst_set_update'),
    path('sets/<int:burst_set_id>/calculate/', views.burst_set_calculate_view, name='burst_set_calculate'),
    path('calculate/', views.calculate, name='calculate'),
]
