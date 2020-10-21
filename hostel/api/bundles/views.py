from django.http import JsonResponse
from hostel.common.models import BundleSearch


def bundles_search(request):
    default_limit = 100
    limit = request.GET.get('limit', default_limit)
    try:
        limit = int(limit)
    except ValueError:
        limit = default_limit

    search_string = request.GET.get('search', '')

    bundles = []
    for bundle in BundleSearch().search(search_string)[0:limit]:
        bundle_data = {'id': bundle.id,
                       'name': bundle.name,
                       'description': bundle.description,
                       'is_lag': bundle.is_lag}
        if bundle.device:
            bundle_data['device_netname'] = bundle.device.netname
        bundles.append(bundle_data)

    return JsonResponse({'bundles': bundles})
