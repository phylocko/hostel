from django.urls import path
from . import views

urlpatterns = [
    path('', views.bundle_list, name='bundles'),
    path('<int:bundle_id>/', views.bundle_view, name='bundle'),
    path('search/', views.bundle_search, name='search_bundles'),
]
