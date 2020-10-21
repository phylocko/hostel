import re

import networkx as nx
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404

from hostel.clients.models import Client, ClientSearch
from hostel.common.models import Service, City, BundleVlan, Bundle
from hostel.devices.models import Device
from hostel.ins.models import Incident
from hostel.nets.models import Net, NetSearch
from hostel.vlans.models import Vlan, VlanSearch


def route(request):
    page = request.GET.get('page', 'default')
    action = request.GET.get('action', 'view')

    if page == 'clients':
        if action == 'search':
            return search_clients(request)
        if action == 'get':
            return get_client(request)

    if page == 'ins':
        if action == 'get_clients':
            return ins_get_clients(request)
        if action == 'add_client':
            return ins_add_client(request)

    if page == 'devices':
        return devices(request)

    if page == 'vlans':
        if action == 'search':
            return search_vlans(request)
        if action == 'list':
            return vlan_list(request)
        if action == 'vis_graph':
            return vis_graph_vlan(request)

    if page == 'nets':
        if action == 'search':
            return search_nets(request)

    if page == 'ptr':
        return nets_ptr(request)

    if page == 'city':
        if action == 'list':
            return city_list(request)
        if action == 'vis_graph':
            return vis_graph_city(request)

    if page == "service":
        if action == "get":
            return get_service(request)

    if page == 'path_finder':
        return path_finder(request)

    if page == 'service_graphs':
        return service_graphs(request)

    return error_404()


def error_404():
    r = dict(error=404)
    return JsonResponse(r)


def service_graphs(request):
    services = request.GET.getlist('service', 'wix')

    services = Service.objects.filter(name__in=services, bundle_vlans__isnull=False) \
        .order_by('client__netname')

    clients = {}
    for s in services:
        netname = s.client.netname
        if netname not in clients:
            clients[netname] = {'services': {}}

        service_name = str(s)
        if service_name not in clients[netname]['services']:
            clients[netname]['services'][service_name] = []

        for bundle_vlan in s.bundle_vlans.all():
            clients[netname]['services'][service_name].append(bundle_vlan.bundle.mrtg_url())

    response = JsonResponse(data=clients)
    response["Access-Control-Allow-Origin"] = "*"
    return response


def path_finder(request):
    source_id = request.GET.get('source', None)
    target_id = request.GET.get('target', None)

    if not source_id or not target_id:
        return JsonResponse({'error': 'You must define source and target!'})

    source_bundle = Bundle.objects.get(pk=source_id)
    target_bundle = Bundle.objects.get(pk=target_id)

    G = nx.Graph()
    devices = Device.objects.filter(type__in=['switch', 'router'], status='+').distinct()
    G.add_nodes_from(devices)

    # create normal edges
    for device in devices:
        for bundle in device.bundles.filter(remote_device__isnull=False,
                                            remote_device__type__in=['switch', 'router']):
            remote_device = bundle.remote_device

            # check if remote device has link too:
            my_bundle = remote_device.bundles.filter(remote_device_id=device.pk).first()
            if my_bundle:
                G.add_edge(device, remote_device, weight=2)
                continue

    # creating fake links between routers
    routers = devices.filter(type='router')
    for source in routers:
        for target in routers:
            if not G.has_edge(source, target) and source is not target:
                G.add_edge(source, target, weight=1)

    source = source_bundle.device
    target = target_bundle.device

    path = nx.dijkstra_path(G, source=source, target=target)

    def get_data(i, path):

        current_device = path[i]

        if i == 0:
            prev_bundle = source_bundle
            next_device = path[i + 1]
            next_bundle = current_device.bundles.filter(remote_device=next_device).first()
        elif i == len(path) - 1:
            next_bundle = target_bundle
            prev_device = path[i - 1]
            prev_bundle = current_device.bundles.filter(remote_device=prev_device).first()
        else:
            prev_device = path[i - 1]
            next_device = path[i + 1]
            prev_bundle = current_device.bundles.filter(remote_device=prev_device).first()
            next_bundle = current_device.bundles.filter(remote_device=next_device).first()

        data = {'device': current_device.netname}

        data['type'] = current_device.type

        if current_device.type == 'switch':
            data['ports'] = [prev_bundle.name, next_bundle.name]

        elif current_device.type == 'router':
            params = {}
            if not prev_bundle:
                params['remote_address'] = prev_device.management_net.address
                params['interface'] = next_bundle.name

            if not next_bundle:
                params['remote_address'] = next_device.management_net.address
                params['interface'] = prev_bundle.name
            data['params'] = params

        return data

    device_path = []
    i = 0
    while i < len(path):
        data = get_data(i, path)
        device_path.append(data)
        i += 1

    return JsonResponse({'path': [device_path],
                         'source_bundle': '%s port %s' % (source_bundle.device.netname, source_bundle.name),
                         'target_bundle': '%s port %s' % (target_bundle.device.netname, target_bundle.name)
                         })


def devices(request):
    requestor = request.GET.get('requestor', 'mrtg')

    if not requestor in ["mrtg", "dns", "zabbix"]:
        requestor = "mrtg"

    if requestor == "mrtg":
        return mrtg_devices(request)

    if requestor == "dns":
        return named_devices(request)

    if requestor == "zabbix":
        return zabbix_devices(request)


def named_devices(request):
    devices_qs = Device.objects.filter(status="+",
                                       management_net__isnull=False,
                                       management_net__netmask=32) \
        .prefetch_related('management_net') \
        .order_by('netname')

    r = {
        'addresses': []
    }

    for device in devices_qs:
        r['addresses'].append({"address": device.management_net.address,
                               "name": device.netname,
                               "type": device.type,
                               "devtype": devtype_adapter(device),
                               "vendor": device.vendor})

    r['params'] = {"count": len(r['addresses'])}

    return JsonResponse(r)


def zabbix_devices(request):
    devices_qs = Device.objects.filter(status="+",
                                       management_net__isnull=False,
                                       store_entry__isnull=False)

    r = dict()
    r['addresses'] = []

    for device in devices_qs:
        if not device.management_net is None:
            try:
                city = device.datacenter.city.name
            except:
                city = None

            r['addresses'].append({"address": device.management_net.address,
                                   "name": device.netname,
                                   "vendor": device.store_entry.vendor,
                                   "type": device.type,
                                   "model": device.store_entry.model,
                                   "city": city})

    r['params'] = {"count": len(r['addresses'])}

    return JsonResponse(r)


def mrtg_devices(request):
    devices_qs = Device.objects.filter(status="+", management_net__isnull=False).order_by('netname')

    device_list = []

    for device in devices_qs:
        if device.type in ["router", "switch"]:
            device_list.append(device)

    output_fmt = get_format(request)

    if output_fmt == "text":
        devices_txt = ""
        for device in devices_qs:
            if devtype_adapter(device):
                devices_txt += "%s %s %s\n" % (device.netname, devtype_adapter(device) or "unknown", device.community)

        return HttpResponse(devices_txt, content_type='text/plain')

    else:
        r = dict()
        r['devices'] = []
        for device in devices_qs:
            if devtype_adapter(device):
                r['devices'].append({'id': device.pk,
                                     'netname': device.netname,
                                     'devtype': devtype_adapter(device),
                                     'community': device.community})

        r['params'] = {'count': len(r['devices'])}

        return JsonResponse(r)


def get_format(request):
    output_fmt = request.GET.get('format', 'text')
    if output_fmt not in ['json', 'text']:
        output_fmt = "text"
    return output_fmt


def devtype_adapter(device):
    if not device.type:
        return None

    if not device.store_entry:
        return None

    if device.store_entry.vendor in ["extreme", "dlink", "mikrotik"]:
        return device.store_entry.vendor

    if device.store_entry.vendor == "cisco":
        if device.type == "switch":
            return "ciscoswitch"
        if device.type == "router":
            return "ciscorouter"

    if device.store_entry.vendor == "juniper":
        if device.type == "switch":
            return "juniperswitch"
        if device.type == "router":
            return "juniperrouter"

    return None


def nets_ptr(request):
    nets = Net.objects.filter(netmask__gte=16).order_by('netmask')

    r = dict()
    r['nets'] = []

    for net in nets:
        net_data = dict(address=net.address, netmask=net.netmask, address_value=net.ipaddress_from)

        net_data['ptr'] = net.ptr

        # null ptr
        if net.ptr == "":
            net_data['ptr'] = None

        # null client:
        net_data['client'] = None

        if net.service:
            if net.service.client:
                net_data['client'] = net.service.client.netname

        r['nets'].append(net_data)

    r['params'] = {"count": len(r['nets'])}
    return JsonResponse(r)


def search_vlans(request):
    search_string = request.GET.get('search_string', None)

    if search_string is None:
        vlans = Vlan.objects.filter(status='+')
    else:
        vlans = VlanSearch().search(search_string)

    filter = request.GET.get('filter', None)

    if filter == "free":
        free_vlans = []
        for vlan in vlans:
            if vlan.service is None:
                free_vlans.append(vlan)
        vlans = free_vlans

    return JsonResponse(dict(vlans=serialize_vlans(vlans)))


def vlan_list(request):
    vlans = Vlan.objects.all()
    return JsonResponse(dict(vlans=serialize_vlans(vlans)))


def city_list(request):
    cities_qs = City.objects.all()
    cities = {}
    for city in cities_qs:
        city_dict = {'pk': city.pk,
                     'name': city.name,
                     'eng_name': city.engname}
        cities[city.pk] = city_dict
    return JsonResponse(cities)


def vis_graph_city(request):
    city_id = request.GET.get('city_id')
    if not city_id:
        return JsonResponse(dict(status='error', error='No city_id given'))

    bundlevlans = BundleVlan.objects.filter(bundle__device__datacenter__city__pk=city_id) \
        .prefetch_related('bundle',
                          'bundle__device',
                          'bundle__device__datacenter',
                          'bundle__device__datacenter__city')

    # Getting nodes
    nodes = []  # {id: 1, label: 'Москва'}
    for bundle_vlan in bundlevlans:
        node = _get_node_form_bundle(bundle_vlan.bundle)
        node['group'] = bundle_vlan.bundle.device.datacenter.pk
        if node not in nodes:
            nodes.append(node)

    # Getting edges
    edges = []  # {from: 1, to: 9}
    for bundle_vlan in bundlevlans:
        # if link is backbone:
        if bundle_vlan.bundle.remote_device:
            edge = {'from': bundle_vlan.bundle.device.pk, 'to': bundle_vlan.bundle.remote_device.pk, 'length': 200}

            if bundle_vlan.bundle.device.datacenter == bundle_vlan.bundle.remote_device.datacenter:
                edge['length'] = 5

            if edge['from'] > edge['to']:
                edge['from'], edge['to'] = edge['to'], edge['from']
            if edge not in edges:
                edges.append(edge)

    return JsonResponse(dict(status='success', nodes=nodes, edges=edges))


def vis_graph_vlan(request):
    vlan_id = request.GET.get('vlan_id')
    if not vlan_id:
        return JsonResponse(dict(status='error', error='No vlan-id given'))

    vlan = Vlan.objects.get(vlannum=vlan_id)
    bundlevlans = vlan.bundlevlan_set.all().prefetch_related('vlan', 'bundle')

    # Getting nodes
    nodes = []  # {id: 1, label: 'Москва'}
    for bundle_vlan in bundlevlans:
        node = _get_node_form_bundle(bundle_vlan.bundle)
        if node not in nodes:
            nodes.append(node)

    # Getting edges
    edges = []  # {from: 1, to: 9}
    for bundle_vlan in bundlevlans:
        # if link is backbone:
        if bundle_vlan.bundle.remote_device:
            edge = {'from': bundle_vlan.bundle.device.pk, 'to': bundle_vlan.bundle.remote_device.pk}
            if edge['from'] > edge['to']:
                edge['from'], edge['to'] = edge['to'], edge['from']
            if edge not in edges:
                edges.append(edge)
        # if link is client's
        else:
            nodes.append(dict(label=bundle_vlan.bundle.description,
                              id=bundle_vlan.bundle.pk + 10000,
                              type='client',
                              borderWidth=0,
                              color='#ffffff',
                              shape='box',
                              font={
                                  'color': '#9eb5c0',
                              }))
            edges.append({'from': bundle_vlan.bundle.device.pk, 'to': bundle_vlan.bundle.pk + 10000})

    return JsonResponse(dict(status='success', nodes=nodes, edges=edges))


def _get_node_form_bundle(bundle):
    if bundle.device.type == 'router':
        shape = 'dot'
    elif bundle.device.type == 'switch':
        shape = 'box'
    else:
        shape = 'star'

    node = dict(id=bundle.device.pk,
                label=bundle.device.netname,
                type='device',
                shape=shape,
                color='#ebebeb',
                shapeProperties={'borderRadius': 0},
                # group=city,
                )
    try:
        node['title'] = bundle.device.datacenter.address
    except AttributeError:
        node['title'] = 'Площадка не указана'

    return node


def search_nets(request):
    filter = request.GET.get('search_string', None)
    if filter is None:
        nets = Net.objects.filter(status='+')
    else:
        nets = NetSearch().search(filter)

    return JsonResponse(dict(nets=serialize_nets(nets)))


def get_client(request):
    by = request.GET.get('by', 'netname')
    value = request.GET.get('value', None)

    if not value:
        return error_404()

    if by == "netname":
        try:
            client = Client.objects.get(netname=value)
        except:
            return error_404()
        return serialize_client(client)

    if by == "email":
        try:
            client = Client.objects.filter(
                Q(email__icontains=value) | Q(maillist__icontains=value) | Q(contacts__icontains=value)).order_by(
                "status").first()
        except:
            return error_404()
        if client:
            return serialize_client(client)
        else:
            client = get_client_by_domain(value)

        if client:
            return serialize_client(client)

    return error_404()


def get_client_by_domain(email):
    COMMON_MAILS = [
        'mail.ru',
        'gmail.com',
        'yandex.ru',
        'ya.ru',
        'bk.ru',
        'inbox.ru',
        'rambler.ru',
    ]

    domain_re = re.compile("@[A-z0-9-_]{3,20}\.[A-z0-9]{1,9}")
    group = domain_re.search(email)
    if not group:
        return None

    domain = group.group()[1:]

    if domain in COMMON_MAILS:
        return None

    # trying to find via website
    client = Client.objects.filter(url__icontains=domain).first()

    # trying to find via email
    if not client:
        client = Client.objects.filter(email__icontains=domain).first()

    # trying to find via contacts
    if not client:
        client = Client.objects.filter(contacts__icontains=domain).first()

    # trying to find via maillist
    if not client:
        client = Client.objects.filter(maillist__icontains=domain).first()

    return client


def search_clients(request):
    filter = request.GET.get('filter', None)
    if filter is None:
        clients = Client.objects.none()
    else:
        clients = ClientSearch().api_search(filter)

    return JsonResponse(dict(clients=serialize_clients(clients)))


def ins_add_client(request):
    incident = get_object_or_404(Incident, pk=request.GET.get('id'))
    client_id = request.GET.get('client', None)
    if client_id is not None:
        incident.clients.add(client_id)
        return JsonResponse(dict(result='ok'))
    else:
        return JsonResponse(dict(error='Client Not Passed'))


def ins_get_clients(request):
    incident = get_object_or_404(Incident, pk=request.GET.get('id'))
    clients = incident.clients.all()

    # TODO Это — временная штука, а вообще нужно будет юзать Angilar, и от API получать только JSON!
    if not request.GET.get('html_rows', None) is None:
        return render(request, 'bs3/ins/clientTableRows.html', {'clients': clients, 'incident': incident})
    else:
        return JsonResponse(dict(clients=serialize_clients(clients)))


def get_service(request):
    service_id = request.GET.get('id', None)
    if not service_id:
        JsonResponse([])
    else:
        try:
            service = Service.objects.get(pk=service_id)
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Serivce with id %s doesn\'t exist'})

        service_ports = []
        bundles = Bundle.objects.filter(bundlevlan__in=service.bundle_vlans.all())
        for bundle in bundles:
            service_ports.append({
                'name': bundle.name,
                'description': bundle.description,
                'device': bundle.device.netname,
            })

        service_vlans = []
        for vlan in service.vlan.all():
            service_vlans.append({
                'tag': vlan.vlannum,
                'name': vlan.vname,
            })

        service_nets = []
        for net in service.net.all():
            service_nets.append({
                'network': net.network,
            })

        data = {
            'name': service.name,
            'type': service.servicetype,
            'ports': service_ports,
            'vlans': service_vlans,
            'nets': service_nets,
        }

        return JsonResponse(data)


def serialize_client(client):
    manager_username = None
    if client.manager:
        manager_username = client.manager.username

    response_data = dict(
        netname=client.netname,
        clientname=client.clientname,
        email=client.email,
        maillist=client.maillist,
        manager=manager_username,
        id=client.pk,
        engname=client.engname,
        city=getattr(client.city, "engname", None),
        is_cunsomer=client.is_consumer,
        is_provider=client.is_provider,
        ebanled=client.enabled,
        ticket=client.ticket,
    )
    return JsonResponse(response_data)


def serialize_clients(clients):
    response_data = {}
    for client in clients:
        client_data = dict(id=client.pk,
                           netname=client.netname,
                           clientname=client.clientname,
                           email=client.email)
        response_data[client.pk] = client_data

    return response_data


def serialize_vlans(vlans):
    response_data = {}
    for vlan in vlans:
        vlan_data = dict(id=vlan.pk,
                         vlannum=vlan.vlannum,
                         vname=vlan.vname,
                         is_p2p=vlan.is_management,
                         comment=vlan.comment)

        response_data[vlan.pk] = vlan_data

    return response_data


def serialize_nets(nets):
    response_data = {}
    for net in nets:
        net_data = dict(id=net.pk,
                        network=net.network,
                        description=net.description,
                        status=net.status)

        response_data[net.pk] = net_data

    return response_data
