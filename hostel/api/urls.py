from django.urls import path
from . import views as common_views
from .bundles import views as bundles_views
from .ports import views as ports_views
from .rs import views as rs_views
from .vlans import views as vlans_views
from .devices import views as devices_views
from .ins import views as ins_views
from .asns import views as asns_view
from .phones import views as phones_views
from .map import views as map_views

urlpatterns = [

    # Unsorted (dump)
    path('', common_views.route, name="api"),

    # Devices
    path('devices/search/', devices_views.devices_search),
    path('devices/<int:device_id>/bundles/', devices_views.devices_bundles),

    # Bundles
    path('bundles/search/', bundles_views.bundles_search),

    # Ports
    path('ports/search/', ports_views.ports_search),

    # RS
    path('rs/peers/', rs_views.peers),

    # as
    path('as/list/', asns_view.as_list),

    # Vlans
    path('vlans/bundles/', vlans_views.bundles),

    # INS
    path('ins/<int:incident_id>/', ins_views.incident),

    # Phones
    path('phones/<int:phone_id>/', phones_views.phone_id),  # по идее, добавляется только через register_call
    path('phones/number/<number>/', phones_views.phone_number),
    path('phones/register_call/', phones_views.register_call),
    path('phones/update_call/', phones_views.update_call),
    path('phones/bot_message_id/<bot_message_id>/', phones_views.bot_message_phone),

    path('map/', map_views.vis_graph_map),
]
