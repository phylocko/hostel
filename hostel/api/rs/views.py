from django.http import JsonResponse, Http404
from django.db.models import Q
from django.db.models.functions import Now
import datetime

from hostel.common.models import Ourservice, Autonomoussystem
from hostel.nets.models import Net


def peers(request):
    r = {}
    r['nets'] = []
    r['params'] = {}

    available_services = ['inet2', 'wix', 'homeix']
    service_name = request.GET.get('service', None)
    if service_name not in available_services:
        raise Http404('Wrong service name: %s' % service_name)

    our_service = Ourservice.objects.get(name=service_name)
    root_net = Net.objects.get(pk=our_service.root_net)

    nets = Net.objects.filter(
        ipaddress_from__gte=root_net.ipaddress_from,
        ipaddress_to__lte=root_net.ipaddress_to,
        service__client__enabled=True,
        service__start_time__lte=Now(),
        service__name=service_name,
        service__asn__isnull=False,
        netmask=32,
        status='+'
    )

    nets = nets.filter(
        Q(service__status='on') |
        Q(service__status='test', service__end_time__gte=Now())
    )

    nets = nets.prefetch_related('service', 'service__asn', 'service__cities', 'service__client')

    for net in nets:

        community = None
        if net.city is not None:
            community = net.city.community
        elif net.service.client.city is not None:
            community = net.service.client.city.community

        net_object = {
            'service_name': net.service.name,
            'service_type': net.service.servicetype,
            'clientid': net.service.client.pk,
            'address': net.address,
            'ipv6_address': net.address6,
            'mac': net.mac or '',
            'peer-as': net.service.asn.asn,
            'as-set': net.service.asn.asset or None,
            'as-set6': net.service.asn.asset6 or None,
            'netname': net.service.asn.engname or net.service.client.netname,
            'community': community,
        }
        r['nets'].append(net_object)

    r['params']['count'] = len(r['nets'])

    return JsonResponse(r)
