from django.urls import path
from . import views

urlpatterns = [
    path('', views.autonomoussystem_list, name='autonomous_systems'),
    path('<int:autonomoussystem_id>/', views.autonomoussystem_view, name='autonomous_system'),
    path('<int:autonomoussystem_id>/update/', views.autonomoussystem_update, name='update_autonomous_system'),
    path('create/', views.autonomoussystem_create, name='create_autonomous_system'),

]