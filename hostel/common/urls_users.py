from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_list_view, name='users'),
    path('<int:user_id>/', views.view_user, name='user'),
    path('<int:user_id>/update/', views.update_user, name='update_user'),
    path('create/', views.create_user, name='create_user'),
    path('set_password/', views.set_user_password, name='set_user_password'),
]