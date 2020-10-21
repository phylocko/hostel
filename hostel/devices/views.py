from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import render, get_object_or_404, redirect, reverse

from hostel.common.models import BurstSet, BundleSearch
from hostel.nets.models import Net
from hostel.settings import LOGIN_URL
from hostel.spy.models import Spy
from hostel.store.models import Entry
from .forms import DeviceForm, CreateDeviceForm
from .models import Device, DeviceSearch


@login_required(login_url=LOGIN_URL)
def device_view(request, device_id):
    tab = request.GET.get('tab', 'bundles')
    context = {'app': 'devices', 'mode': 'view', 'tab': tab}

    device = get_object_or_404(Device, pk=device_id)
    context['device'] = device

    bursts = BurstSet.objects.filter(bundles__in=device.bundles.all()).distinct()
    context['bursts'] = bursts

    logs = Spy.objects.filter(object_name='device', object_id=device.pk).order_by('-time')
    context['logs'] = logs

    bundles = device.bundles.all().prefetch_related('remote_device', 'ports') \
        .annotate(vlans_count=Count('bundlevlan', distinct=True)) \
        .annotate(ports_count=Count('ports', distinct=True))
    search_string = request.GET.get('search')
    if search_string:
        bundles = BundleSearch(queryset=bundles).local_search(search_string)
        context['search_string'] = search_string
    context['bundles'] = bundles

    return render(request, 'bs3/devices/device_view.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('devices.change_device')
def device_update(request, device_id):
    tab = request.GET.get('tab', 'bundles')

    context = {'app': 'devices', 'mode': 'edit', 'tab': tab}
    device = get_object_or_404(Device, pk=device_id)
    management_nets = Net.objects.filter(device=device, netmask=32).order_by('ipaddress_from')
    store_entries = Entry.objects.filter(
        Q(device__isnull=True) |
        Q(device=device)
    )

    if request.method == "POST":
        form = DeviceForm(request.POST, instance=device)
        form.fields['management_net'].queryset = management_nets
        form.fields['store_entry'].queryset = store_entries
        if form.is_valid():
            old_object = Device.objects.get(pk=device.pk)
            Spy().changed(device, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные девайса обновлены')
            url = reverse(device_view, args=[device.pk])
            url += '?tab=%s' % tab
            return redirect(url)
    else:
        form = DeviceForm(instance=device)
        form.fields['management_net'].queryset = management_nets
        form.fields['store_entry'].queryset = store_entries

    context['form'] = form
    context['device'] = device

    return render(request, 'bs3/devices/device_update.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('devices.add_device')
def device_create(request):
    context = {'app': 'devices', 'tab': 'add', 'mode': 'edit'}

    form = CreateDeviceForm(request.POST or None)
    if form.is_valid():
        device = form.save()
        Spy().created(form.instance, form, request)
        ipaddress = form.cleaned_data.get('ipaddress')
        if ipaddress:
            net = Net(address=ipaddress, netmask=32, status='+',
                      device=device, description='%s management' % device.netname)
            net.save()

            device.management_net = net
            device.save()
            Spy().created(instance=net, request=request)
            messages.success(request, 'Сеть %s создана' % net)

        messages.add_message(request, messages.SUCCESS, "Device успешно создан")
        return redirect(device_view, device_id=form.instance.pk)

    context['form'] = form
    return render(request, 'bs3/devices/device_create.html', context)


@login_required(login_url=LOGIN_URL)
def device_list(request):
    context = {'app': 'devices', 'tab': 'devices'}

    devices = Device.objects.prefetch_related('net', 'datacenter', 'datacenter__city',
                                              'store_entry').all().order_by("netname")

    if request.GET:
        search_string = request.GET.get('search')
        context['search_string'] = search_string
        if search_string:
            devices = DeviceSearch().search(search_string)
            context['listing'] = devices
            return render(request, 'bs3/devices/device_list.html', context)

    paginator = Paginator(devices, request.user.pagination_count)
    page = request.GET.get('page', 1)
    devices = paginator.get_page(page)

    context['listing'] = devices

    return render(request, 'bs3/devices/device_list.html', context)


@login_required(login_url=LOGIN_URL)
def device_search(request):
    context = {'tab': 'search', 'app': 'devices'}
    search_string = request.GET.get('search', None)
    devices = DeviceSearch().search(search_string)
    context['devices'] = devices
    context['search_string'] = search_string
    return render(request, 'bs3/devices/device_list.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('devices.delete_device')
def device_delete(request):
    device = get_object_or_404(Device, pk=request.POST.get('id'))
    Spy().log(object=device, form=None, user=request.user, action=Spy.DELETE)
    device.delete()
    messages.add_message(request, messages.SUCCESS, 'Device удален')
    return redirect(device_list)
