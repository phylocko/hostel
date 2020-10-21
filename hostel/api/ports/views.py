from django.http import JsonResponse
from hostel.common.models import PortSearch


def ports_search(request):
    default_limit = 100
    limit = request.GET.get('limit', default_limit)
    try:
        limit = int(limit)
    except ValueError:
        limit = default_limit

    search_string = request.GET.get('search', '')

    results = []
    ports = PortSearch().search(search_string)
    ports = ports.filter(bundle__isnull=False)
    for p in ports:
        print(p.bundle, p, sep=' | ')

    for port in ports[0:limit]:
        port_data = {'id': port.id,
                     'name': port.name,
                     'bundle_name': port.bundle.name,
                     'description': port.description,
                     'device_netname': port.bundle.device.netname
                     }
        results.append(port_data)

    return JsonResponse({'ports': results})
