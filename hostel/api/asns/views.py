from django.http import JsonResponse, Http404
from django.db.models import Q, Count
from django.db.models.functions import Now

from hostel.common.models import Autonomoussystem
from hostel.nets.models import Net


def as_list(request):
    r = {
        'asns': [],
        'params': {}
    }

    asns = Autonomoussystem.objects.all().annotate(Count('services'))

    for asn in asns:

        if not asn.is_white():
            continue

        asn_object = {
            'id': asn.pk,
            'asn': asn.asn,
            'as_set': asn.asset,
            'as_list': asn.aslist,
            'asset6': asn.asset6,
            'netname': asn.engname,
            'client_id': asn.client_id,
            'services': asn.services__count,
        }
        r['asns'].append(asn_object)

    r['params']['count'] = len(r['asns'])

    return JsonResponse(r)
