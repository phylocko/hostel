from django.urls import path
from . import api, views

urlpatterns = [
    path('', views.select_bundles, name='select_bundles'),
    path('select_path', views.select_path, name='select_path'),

    # api
    path('api/suggested_paths/', api.suggested_paths, name='api_device_paths'),
    path('api/full_path/', api.full_path, name='api_full_path'),
]
