import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404

from hostel.common.models import Service, BundleVlan
from hostel.common.views import service_view
from hostel.settings import LOGIN_URL
from hostel.spy.models import Spy
from .forms import VlanForm
from .models import Vlan, VlanSearch


# == Vlan ==
@login_required(login_url=LOGIN_URL)
def vlan_view(request, vlan_id):
    context = {'app': 'vlans'}

    tab = request.GET.get('tab', 'services')
    if tab not in {'services', 'nets', 'bundles', 'map'}:
        tab = 'services'
    context['tab'] = tab

    vlan = get_object_or_404(Vlan, pk=vlan_id)
    context['vlan'] = vlan

    logs = Spy.objects.filter(object_name='vlan', object_id=vlan.pk).order_by('-time')
    context['logs'] = logs

    bundle_vlans = BundleVlan.objects.filter(vlan=vlan)
    context['bundle_vlans'] = bundle_vlans

    return render(request, 'bs3/vlans/vlan_view.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('vlans.change_vlan')
def vlan_update(request, vlan_id):
    context = {'app': 'vlans', 'mode': 'edit'}
    vlan = get_object_or_404(Vlan, pk=vlan_id)
    if request.method == "POST":
        form = VlanForm(request.POST, instance=vlan)
        if form.is_valid():
            old_object = Vlan.objects.get(pk=vlan.pk)
            Spy().changed(vlan, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные Vlan обновлены')
            return redirect(vlan_view, vlan_id=form.instance.pk)
    else:
        form = VlanForm(instance=vlan)
    context['form'] = form
    context['vlan'] = vlan
    return render(request, 'bs3/vlans/vlan_update.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('vlans.add_vlan')
def vlan_create(request):
    context = {'app': 'vlans', 'tab': 'add'}
    vlan_id = request.GET.get('vlanid', None)
    form = VlanForm(request.POST or None, initial={'vlannum': vlan_id})
    if form.is_valid():
        form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, "Vlan успешно создан")
        return redirect(vlan_view, vlan_id=form.instance.pk)
    print(form.errors)
    context['form'] = form
    return render(request, 'bs3/vlans/vlan_create.html', context)


@login_required(login_url=LOGIN_URL)
def vlan_list(request):
    context = {'app': 'vlans'}

    vlans = Vlan.objects.all().prefetch_related('service').order_by('vlannum').annotate(Count('nets'))

    search_string = request.GET.get('search')
    if search_string:
        context['search_string'] = search_string
        vlans = VlanSearch(queryset=vlans).search(search_string)
        context['vlans'] = vlans

    else:

        # generating free ranges between vlans
        free_ranges = []
        position = 1
        vlans_with_ranges = []
        for vlan in vlans:
            if vlan.vlannum > position:
                free_range = (position, vlan.vlannum - 1)
                vlans_with_ranges.append(free_range)
                free_ranges.append(free_range)
            vlans_with_ranges.append(vlan)
            position = vlan.vlannum + 1
        if position < 4096:
            free_range = (position, 4096)
            vlans_with_ranges.append(free_range)
            free_ranges.append(free_range)

        context['vlans'] = vlans_with_ranges

        if len(free_ranges) > 10:
            start = random.randint(0, len(free_ranges) - 10)
            free_ranges = free_ranges[start:start + 10]
        context['free_ranges'] = free_ranges

    return render(request, 'bs3/vlans/vlan_list.html', context)


@login_required(login_url=LOGIN_URL)
def vlan_search(request):
    context = {'tab': 'search', 'app': 'vlans'}
    search_string = request.GET.get('search', None)
    vlans = VlanSearch().search(search_string)
    context['vlans'] = vlans
    context['search_string'] = search_string
    return render(request, 'bs3/vlans/vlan_list.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('vlans.delete_vlan')
def vlan_delete(request):
    vlan = get_object_or_404(Vlan, pk=request.POST.get('id'))
    Spy().log(object=vlan, form=None, user=request.user, action=Spy.DELETE)
    vlan.delete()
    messages.add_message(request, messages.SUCCESS, 'Vlan удален')
    return redirect(vlan_list)


@login_required(login_url=LOGIN_URL)
@permission_required('vlans.add_vlan')
def create_for_service(request):
    if request.method == "POST":  # Пришли данные для рабты
        form = VlanForm(request.POST)
        service = get_object_or_404(Service, pk=request.POST.get('service_id'))
        free_vlans = service.get_free_vlans()

        if form.is_valid():
            # TODO: Проверка данных на соответствие требованиям услуги
            form.save()
            if form.instance.pk:
                form.instance.service = service
                Spy().log(object=form.instance, form=form, user=request.user, action=Spy.CREATE)
                Spy().log(object=service, user=request.user, action=Spy.CREATE)
                form.instance.save()
                # TODO: add success message
            else:
                pass
            # TODO: add an error message
            return redirect(service_view, service_id=service.pk)

        else:
            service = get_object_or_404(Service, pk=request.GET.get('service'))

    else:  # Данных в POST нет, просто выводим форму для добавления новой сети
        service = get_object_or_404(Service, pk=request.GET.get('service'))

        rt = request.GET.get('rt')

        free_vlans = service.get_free_vlans()

        recommended_vlan = ''
        if free_vlans:
            recommended_vlan = free_vlans[0].vlannum
        form = VlanForm(initial={'rt': rt,
                                 'vlannum': recommended_vlan,
                                 'vname': '%s_' % service.client.netname})

    context = {'form': form,
               'service': service,
               'free_vlans': free_vlans[:134],
               'app': 'vlans'}

    return render(request, 'bs3/vlans/add_vlan_to_service.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('vlans.change_vlan')
def assign_to_service(request):
    if request.method == "POST":  # Пришли данные для рабты
        service = get_object_or_404(Service, pk=request.POST.get('service_id'))

        vlan_id = request.POST.get('vlan_id')

        if not vlan_id.isdigit():
            messages.add_message(request, messages.ERROR, "Не определен влан")
            return redirect("../vlans/?page=vlan&action=assigntoservice&service=%s" % service.pk)

        vlan = get_object_or_404(Vlan, pk=request.POST.get('vlan_id'))
        Spy().log(object=service, user=request.user, action=Spy.CHANGE)
        vlan.service = service
        vlan.save()

        messages.add_message(request, messages.SUCCESS, "Влан %s добавлен к услуге %s" % (vlan, service))

        return redirect(service_view, service_id=service.pk)

    else:  # Данных в POST нет, просто выводим форму для добавления новой сети
        service = get_object_or_404(Service, pk=request.GET.get('service'))
    context = {'service': service,
               'app': 'vlans'}

    return render(request, 'bs3/vlans/assign_vlan_to_service.html', context)
