from django.urls import path
from . import views

urlpatterns = [
    path('numbers/', views.number_list_view, name='numbers'),
    path('numbers/<int:number_id>/', views.number_view, name='number'),
    path('numbers/<int:number_id>/update/', views.update_number_view, name='update_number'),
    path('calls/', views.call_list_view, name='calls'),
]
