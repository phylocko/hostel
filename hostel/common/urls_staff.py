from django.urls import path
from . import views

urlpatterns = [
    path('', views.employes_view, name='employes'),
    path('<int:employee_id>/', views.employee_view, name='employee'),
]