from django.urls import path
from . import views

urlpatterns = [
    path('<int:service_id>/', views.archiverd_service_view, name='archived_service'),
]
