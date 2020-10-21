from django.http import JsonResponse
from hostel.devices.models import Device, DeviceSearch


def devices_search(request):
    default_limit = 100
    limit = request.GET.get('limit', default_limit)
    try:
        limit = int(limit)
    except ValueError:
        limit = default_limit

    search_string = request.GET.get('search', '')

    devices = []
    for device in DeviceSearch().search(search_string)[0:limit]:
        device_data = {'id': device.pk,
                       'netname': device.netname,
                       'version': device.version,
                       'status': device.status,
                       'is_managed': device.is_managed}
        devices.append(device_data)
    return JsonResponse({'devices': devices})


def devices_bundles(request, device_id):
    response = {'bundles': []}

    try:
        device = Device.objects.get(pk=device_id)
    except Device.DoesNotExist:
        return JsonResponse(response)

    bundles = device.bundles.all()
    for bundle in bundles:
        response['bundles'].append({
            'name': bundle.name,
            'description': bundle.description,
            'mrtg_name': bundle.mrtg_name()
        })
    return JsonResponse(response)
