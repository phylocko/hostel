from django.http import JsonResponse
from hostel.vlans.models import Vlan


def bundles(request):
    tag = request.GET.get('tag')
    vlan_name = request.GET.get('name')

    vlan = None

    if tag:
        try:
            vlan = Vlan.objects.get(vlannum=tag)
        except Vlan.DoesNotExist:
            pass

    elif vlan_name:
        try:
            vlan = Vlan.objects.get(vname=vlan_name)
        except Vlan.DoesNotExist:
            pass

    if not vlan:
        return JsonResponse({'error': 'Requested vlan not found'})

    vlan_data = {
        'tag': vlan.vlannum,
        'name': vlan.vname,
    }

    bundle_vlan_data = []

    for bundle_vlan in vlan.bundlevlan_set.all().order_by('bundle__iface_index').order_by('bundle__device__netname'):
        bundle_vlan_data.append({
            'device': bundle_vlan.bundle.device.netname,
            'bundle': bundle_vlan.bundle.name,
            'description': bundle_vlan.bundle.description,
            'mode': bundle_vlan.mode,
        })

    return JsonResponse({'vlan': vlan_data, 'bundle_vlans': bundle_vlan_data})
