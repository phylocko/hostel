from hostel.clients.models import Client
from hostel.common.models import City, Service, Datacenter
from hostel.devices.models import Device
from django.contrib.auth.models import User


def filter_services(params):
    city_ids = params.getlist('cities')
    service_names = params.getlist('services')
    services = Service.objects.filter(name__in=service_names, cities__in=city_ids, status__in=['+', '?'])
    return services


def inject_choices(form, field_name, choices, required=False, multi=False):
    if multi:
        height = len(choices) * 18
        form.fields[field_name].choices = choices
        form.fields[field_name].widget.attrs = {'class': 'form-control', 'style': 'height: %spx' % height}
    else:
        form.fields[field_name].choices = choices
        form.fields[field_name].widget.attrs = {'class': 'form-control'}

    form.fields[field_name].required = required
    return form


def return_to(request, default):
    page = request.GET.get("return_to", default)
    pk = request.GET.get("return_to_id", 0)
    return page, pk
