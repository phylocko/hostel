from django.urls import path
from . import views

urlpatterns = [
    path('entries/', views.entry_list, name='store_entries'),
    path('entries/<int:entry_id>/', views.entry_view, name='entry'),
    path('entries/<int:entry_id>/update/', views.entry_update, name='entry_update'),
    path('entries/add/', views.entry_create, name='add_entry'),

    path('parts/', views.part_list, name='store_parts'),
    path('parts/<int:part_id>/', views.part_view, name='part'),
    path('parts/<int:part_id>/update/', views.part_update, name='part_update'),
    path('part/add/', views.part_create, name='add_part'),

]
