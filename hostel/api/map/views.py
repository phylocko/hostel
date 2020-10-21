from django.http import JsonResponse

from hostel.common.models import Bundle
from hostel.devices.models import Device


def vis_graph_map(request):
    nodes = []

    device_types = ['router']
    switches = request.GET.get('switches', False)
    if switches:
        device_types.append('switch')

    device_city_map = {}

    devices = Device.objects.filter(type__in=device_types, status='+', datacenter__isnull=False)
    for device in devices:

        device_city_map[device.pk] = device.datacenter.city.pk

        if device.type == 'router':
            node = {
                "id": device.pk,
                "label": device.netname,
                "type": "device",
                "shape": "dot",
                "color": "#ebebeb",
                "shapeProperties": {
                    "borderRadius": 0
                },
                "title": device.datacenter.city.name,
                "group": device.datacenter.city.pk,
            }
        else:
            node = {
                "id": device.pk,
                "label": device.netname,
                "type": "device",
                "shape": "box",
                "color": "#ebebeb",
                "shapeProperties": {
                    "borderRadius": 0
                },
                "title": device.datacenter.city.name,
                "group": device.datacenter.city.pk,
            }
        nodes.append(node)

    edge_set = set()
    for bundle in Bundle.objects.filter(device__in=devices, remote_device__in=devices):
        from_id = bundle.device_id
        to_id = bundle.remote_device_id
        if from_id < to_id:
            from_id, to_id = to_id, from_id
        if from_id == to_id:
            continue
        edge_set.add((from_id, to_id))

    edges = []
    for id_from, id_to in edge_set:
        edge_length = 1 if device_city_map[id_from] == device_city_map[id_to] else 300
        edges.append({'from': id_from, 'to': id_to, 'length': edge_length})

    # edges = [{'from': x[0], 'to': x[1]} for x in edge_set]
    return JsonResponse(dict(status='success', nodes=nodes, edges=edges))
