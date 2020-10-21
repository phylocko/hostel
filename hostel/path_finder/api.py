from django.http import JsonResponse
from .models import PathFinder


def suggested_paths(request):
    source_id = request.GET.get('source_id', None)
    target_id = request.GET.get('target_id', None)
    exclude_netnames = request.GET.getlist('exclude_netname')

    data = PathFinder().suggest_paths(source_id, target_id, exclude_netnames)
    return JsonResponse(data)


def full_path(request):
    source_id = request.GET.get('source_id', None)
    target_id = request.GET.get('target_id', None)

    if not source_id or not target_id:
        return JsonResponse({'error': 'Undefined source_id or target_id'})

    selected_string = request.GET.get('requested_path', '')
    requested_path = selected_string.split()

    if requested_path:
        bundle_path = PathFinder().full_path(source_id, target_id, requested_path)
        return JsonResponse(bundle_path)
    else:
        return JsonResponse({'error': 'requested_path is empty'})
