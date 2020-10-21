import datetime

from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import render, redirect

import hostel.common.models as common_models
from hostel.spy.models import Spy
from hostel.vlans.models import Vlan
from .forms import ServiceForm
from .models import PathFinder, PathNotFound


def select_bundles(request):
    source = ''
    target = ''
    source_bundle = None
    target_bundle = None

    if request.GET:
        source = request.GET.get('source', None)
        target = request.GET.get('target', None)

        if source.isdecimal():
            try:
                source_bundle = common_models.Bundle.objects.get(pk=source)
            except common_models.Bundle.DoesNotExist:
                messages.add_message(request, messages.ERROR, 'Не удается найти Source Bundle')
        elif source:
            source = source.replace('port', ' ')
            try:
                source_netname, source_name = source.split()
            except ValueError:
                source_netname, source_name = None, None
            try:
                source_bundle = common_models.Bundle.objects.get(device__netname=source_netname, name=source_name)
            except common_models.Bundle.DoesNotExist:
                messages.add_message(request, messages.ERROR, 'Не удается найти Source Bundle')
        else:
            messages.add_message(request, messages.ERROR, 'Не указан Source Bundle')

        if target.isdecimal():
            try:
                target_bundle = common_models.Bundle.objects.get(pk=target)
            except common_models.Bundle.DoesNotExist:
                messages.add_message(request, messages.ERROR, 'Не удается найти Target Bundle')
        elif target:
            target = target.replace('port', ' ')
            try:
                target_netname, target_name = target.split()
            except ValueError:
                target_netname, target_name = None, None

            try:
                target_bundle = common_models.Bundle.objects.get(device__netname=target_netname, name=target_name)
            except common_models.Bundle.DoesNotExist:
                messages.add_message(request, messages.ERROR, 'Не удается найти Target Bundle')
        else:
            messages.add_message(request, messages.ERROR, 'Не указан Target Bundle')

    context = {
        'source': source,
        'target': target,
        'source_bundle': source_bundle,
        'target_bundle': target_bundle,
    }
    return render(request, 'bs3/path_finder/wizard/select_bundles.html', context)


def select_path(request):
    context = {}

    # getting by bundle_id
    source_id = request.GET.get('source_id', None)
    target_id = request.GET.get('target_id', None)

    if source_id:
        source_bundle = common_models.Bundle.objects.get(pk=source_id)
    if target_id:
        target_bundle = common_models.Bundle.objects.get(pk=target_id)

    # getting vlan_id
    vlan_id = request.GET.get('vlan_id', None)
    vlan_name = request.GET.get('vlan_name', None)
    context['vlan_id'] = vlan_id
    context['vlan_name'] = vlan_name

    exclude_string = request.GET.get('exclude_netnames', '')
    exclude_netnames = exclude_string.split()

    if not source_id or not target_id:
        messages.add_message(request, messages.ERROR, 'Не указаны Source ID или Target ID')
        return redirect(select_bundles)

    suggested_paths = PathFinder().suggest_paths(source_id, target_id, exclude_netnames)

    requested_path_string = request.GET.get('requested_path', '')
    requested_path = requested_path_string.split()
    context['requested_path'] = requested_path

    forced_path_string = request.GET.get('forced_path', '')
    forced_path = forced_path_string.split()
    if forced_path and forced_path not in suggested_paths['paths']:
        suggested_paths['paths'].append(forced_path)
        requested_path = forced_path
        context['requested_path'] = forced_path
        context['forced_path'] = forced_path

    if requested_path:
        try:
            full_path = PathFinder().full_path(source_id, target_id, requested_path)
        except PathNotFound:
            full_path = None
            messages.add_message(request, messages.ERROR, 'Путь через %s не существует' % ' -> '.join(requested_path))
        context['full_path'] = full_path

    context['suggested_paths'] = suggested_paths
    context['source_bundle'] = source_bundle
    context['target_bundle'] = target_bundle
    context['exclude_netnames'] = exclude_netnames

    initial = {}
    if vlan_id:
        try:
            vlan = Vlan.objects.get(vlannum=vlan_id, service__isnull=True, is_management=False)
            initial = {'vlan': vlan}
        except Vlan.DoesNotExist:
            initial = {'vlan_id': vlan_id, 'vlan_name': vlan_name}
            vlan = None

    service_form = ServiceForm(initial=initial)

    if request.POST:
        service_form = ServiceForm(request.POST)
        if service_form.is_valid():
            client = service_form.cleaned_data['client']

            service = common_models.Service()
            service.client = client
            service.status = 'on'
            service.name = 'l2'
            service.rt = service_form.cleaned_data['rt']
            service.comment = service_form.cleaned_data['comment']
            service.servicetype = service_form.cleaned_data['service_type']
            service.description = service_form.cleaned_data['description']
            service.start_time = datetime.datetime.now()
            service.end_time = datetime.datetime.now()
            service.save()
            for city in service_form.cleaned_data['cities']:
                service.cities.add(city)
            Spy().created(service, service_form, request, client)
            messages.add_message(request, messages.SUCCESS, 'Услуга %s успешно создана' % service)

            if service_form.cleaned_data['vlan']:
                vlan = service_form.cleaned_data['vlan']
                vlan.service = service
                vlan.save()
                messages.add_message(request, messages.SUCCESS, 'Влан %s привязан к услуге %s' % (vlan, service))
            elif service_form.cleaned_data['vlan_id'] and service_form.cleaned_data['vlan_name']:
                vlan = Vlan()
                vlan.vlannum = service_form.cleaned_data['vlan_id']
                vlan.vname = service_form.cleaned_data['vlan_name']
                vlan.rt = service_form.cleaned_data['rt']
                vlan.service = service
                try:
                    vlan.save()
                except IntegrityError:
                    messages.add_message(request, messages.ERROR, 'Влан с id %s или названием %s '
                                                                  'уже существует' % (vlan.vlannum, vlan.vname))
                else:
                    messages.add_message(request, messages.SUCCESS, 'Влан %s успешно создан' % vlan)
            return redirect('service', service_id=service.pk)

    context['service_form'] = service_form

    return render(request, 'bs3/path_finder/wizard/select_path.html', context)
