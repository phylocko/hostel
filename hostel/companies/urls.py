from django.urls import path
from . import views

urlpatterns = [
    path('', views.company_list, name='companies'),
    path('add/', views.company_create, name='add_company'),
    path('<int:company_id>/', views.company_view, name='company'),
    path('<int:company_id>/update/', views.company_update, name='update_company'),
]
