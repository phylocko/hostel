from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

from hostel.common.views import home, login_page, logout_page

urlpatterns = [

    # home
    path('', home, name="home"),

    # app: common
    path('autonomous_systems/', include('hostel.common.urls_autonomous_systems')),
    path('bundles/', include('hostel.common.urls_bundles')),
    path('cities/', include('hostel.common.urls_cities')),
    path('datacenters/', include('hostel.common.urls_datacenters')),
    path('groups/', include('hostel.common.urls_groups')),
    path('leases/', include('hostel.common.urls_leases')),
    path('users/', include('hostel.common.urls_users')),
    path('profile/', include('hostel.common.urls_profile')),
    path('service/', include('hostel.common.urls_services')),
    path('archived_services/', include('hostel.common.urls_archived_services')),
    path('staff/', include('hostel.common.urls_staff')),
    path('cc/', include('hostel.common.urls_cc')),

    path('clients/', include('hostel.clients.urls')),
    path('companies/', include('hostel.companies.urls')),
    path('devices/', include('hostel.devices.urls')),
    path('vlans/', include('hostel.vlans.urls')),
    path('nets/', include('hostel.nets.urls')),
    path('ins/', include('hostel.ins.urls')),
    path('store/', include('hostel.store.urls')),
    path('docs/', include('hostel.docs.urls')),
    path('search/', include('hostel.search.urls')),
    path('spy/', include('hostel.spy.spy_urls')),
    path('path_finder/', include('hostel.path_finder.urls')),
    path('map/', include('hostel.common.map_urls')),
    path('racks/', include('hostel.common.urls_racks')),

    # app: api
    path('api/', include('hostel.api.urls')),

    # authentication
    path('login/', login_page, name='login'),
    path('logout/', logout_page, name='logout'),

]

if 'django.contrib.staticfiles' in settings.INSTALLED_APPS and settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
