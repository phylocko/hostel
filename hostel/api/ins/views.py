from hostel.ins.models import Incident
from django.shortcuts import get_object_or_404
from django.http import JsonResponse


def incident(request, incident_id):
    incident = get_object_or_404(Incident, pk=incident_id)

    incident_data = {
        'pk': incident.pk,
        'name': incident.name,
        'rt': incident.rt,
        'provider_tt': incident.provider_tt,
        'type': incident.type,
        'provider_netname': incident.provider.netname,
        'provider_id': incident.provider.pk,
        'time_start': incident.time_start.strftime('%Y-%m-%d %H:%M'),
        'time_end': incident.time_end.strftime('%Y-%m-%d %H:%M'),
        'closed': incident.closed,
    }

    return JsonResponse(incident_data)
