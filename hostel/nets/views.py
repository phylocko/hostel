from .models import *
from hostel.devices.models import Device
from hostel.common.models import Service, City
from hostel.vlans.models import Vlan
from django.shortcuts import get_object_or_404, render, redirect
from django import forms
from .forms import NetForm
from hostel.common.views import service_view
from django.contrib import messages
from hostel.spy.models import Spy
import hostel.common.helper_functions as h
from django.contrib.auth.decorators import login_required, permission_required
from hostel.settings import LOGIN_URL


@login_required(login_url=LOGIN_URL)
def delete_net(request):
    net = get_object_or_404(Net, pk=request.POST.get('id'))
    Spy().log(object=net, action=Spy.DELETE, user=request.user)
    messages.add_message(request, messages.SUCCESS, "Сеть %s удалена" % net)

    if request.POST.get('delete_subnets', None):
        children = Net.objects.children_of(net)
        for child in children:
            if child.protected:
                messages.add_message(request, messages.ERROR, "Сеть %s защищена" % child)
            else:
                messages.add_message(request, messages.SUCCESS, "Сеть %s удалена" % child)
                Spy().log(object=child, action=Spy.DELETE, user=request.user)
                child.delete()

    if request.POST.get('delete_vlan', None):
        messages.add_message(request, messages.SUCCESS, "Vlan %s удален" % net.vlan)
        Spy().log(object=net.vlan, action=Spy.DELETE, user=request.user)
        net.vlan.delete()

    net.delete()
    return redirect(view_nodes)


@login_required(login_url=LOGIN_URL)
@permission_required('nets.add_net')
def add_net(request):
    context = {'app': 'nets', 'tab': 'add'}

    selected_address = request.GET.get("address", "")
    selected_netmask = request.GET.get("mask", "")
    selected_device = request.GET.get("device", "")
    selected_vlan = request.GET.get("vlan", "")
    return_to = request.GET.get('return_to')
    return_net = request.GET.get('return_net')

    vlans = Vlan.objects.filter(is_management=True).order_by("vlannum")
    vlans_choices = [("", "")]
    for vlan in vlans:
        choice = (vlan.pk, "%s - %s" % (vlan.vlannum, vlan.vname))
        vlans_choices.append(choice)

    initial = {
        'address': selected_address,
        'netmask': selected_netmask,
        'vlan': selected_vlan,
        'device': selected_device
    }
    form = NetForm(initial=initial)
    context['form'] = form

    if request.method == "POST":
        form = NetForm(request.POST)
        context['form'] = form

        if form.is_valid():
            try:
                form.save()
            except ValueError as e:
                messages.add_message(request, messages.ERROR, str(e))
            else:
                form.save()
                Spy().created(form.instance, form, request)
                if return_to == 'net' and return_net:
                    return redirect(view_net, net_id=return_net)
                return redirect(view_net, net_id=form.instance.pk)

    return render(request, 'bs3/nets/add_net.html', context)


@login_required(login_url=LOGIN_URL)
def assign_to_service(request):
    if request.method == "POST":  # Пришли данные для рабты
        service = get_object_or_404(Service, pk=request.POST.get('service_id'))
        net = get_object_or_404(Net, pk=request.POST.get('object_id'))

        Spy().log(object=net, user=request.user, action=Spy.CHANGE)
        net.service = service
        net.save()

        return redirect(service_view, service_id=service.pk)

    else:  # Данных в POST нет, просто выводим форму для добавления новой сети
        service = get_object_or_404(Service, pk=request.GET.get('service'))

    return_to, return_to_id = h.return_to(request, "net")

    context = {'service': service,
               'app': 'nets',
               'return_to': return_to,
               'return_to_id': return_to_id,
               }

    return render(request, 'bs3/nets/assign_net_to_service.html', context)


@login_required(login_url=LOGIN_URL)
def create_for_service(request):
    context = {'app': 'nets', 'tab': 'add', 'mode': 'edit'}
    service = get_object_or_404(Service, pk=request.GET.get('service_id'))
    context['service'] = service

    initial = {'allocated_for': 'service', 'rt': service.rt or None, 'status': '+'}

    params = service.params()
    if params.get('min_mask') == 32:
        suggested_hosts = service.suggested_hosts()
        suggested_nets = [{'address': x, 'netmask': 32} for x in suggested_hosts]
        context['suggested_nets'] = suggested_nets
    else:
        suggested_nets = service.suggested_nets()
        context['suggested_nets'] = suggested_nets
        if suggested_nets:
            suggested_net = suggested_nets[0]
            initial['address'] = suggested_net.address
            initial['netmask'] = suggested_net.netmask

    form = NetForm(initial=initial)
    context['form'] = form

    if request.method == "POST":  # Пришли данные для рабты
        form = NetForm(request.POST)
        if form.is_valid():

            form.instance.service = service
            try:
                form.save()
            except ValueError:
                messages.error(request, 'Сеть %s уже существует' % form.instance)
            else:
                return redirect(service_view, service_id=service.pk)

            return render(request, 'bs3/nets/add_net_to_service.html', context)

    return render(request, 'bs3/nets/add_net_to_service.html', context)


@login_required(login_url=LOGIN_URL)
def view_net(request, net_id):
    context = {'add': 'nets'}

    net = get_object_or_404(Net, pk=net_id)
    context['net'] = net

    children = Net.objects.children_of(net)
    children = Nets(children, root_net=net).filled_nodes()
    context['children'] = children

    parents = Net.objects.parents_of(net).order_by('netmask')
    context['parents'] = parents

    logs = Spy.objects.filter(object_name='net', object_id=net.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/nets/view_net.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('nets.change_net')
def update_net(request, net_id):
    return_to = request.GET.get('return_to')

    net = get_object_or_404(Net, pk=net_id)
    if request.method == "POST":
        form = NetForm(request.POST, instance=net)
        if form.is_valid():
            try:
                form.save()
            except ValueError as e:
                messages.add_message(request, messages.ERROR, str(e))
            else:
                Spy().changed(instance=form.instance, old_instance=net, form=form, request=request)
                messages.add_message(request, messages.SUCCESS, "Данные сети обновлены")
                if return_to == 'nets':
                    return redirect(view_nodes)
                else:
                    return redirect(view_net, net_id=net.pk)
    else:
        form = NetForm(instance=net)

    context = {'form': form, 'net': net}
    return render(request, 'bs3/nets/update_net.html', context)


def get_children(net):
    children = Net.objects.filter(ipaddress_from__gte=net.ipaddress_from,
                                  ipaddress_to__lte=net.ipaddress_to,
                                  netmask__gt=net.netmask).order_by('ipaddress_from')
    return children


@login_required(login_url=LOGIN_URL)
def search_nets(request):
    nets = []
    original_search_string = request.GET.get('search', None)

    root_nets = get_root_nets()

    if original_search_string is not None:
        nets = NetSearch().search(original_search_string)

    return render(request, 'bs3/nets/search_nets.html', {'nets': nets,
                                                     'root': 0,
                                                     'root_nets': root_nets,
                                                     'tab': 'search',
                                                     'app': 'nets',
                                                     'search_string': original_search_string or ""})


@login_required(login_url=LOGIN_URL)
def view_nodes(request):
    root_id = request.GET.get("root", None)

    root_net = None
    root_nets = get_root_nets()

    if not root_id and root_nets:
        root_id = request.COOKIES.get('root_net', root_nets[0].pk)

    if root_id:
        if root_id == "0":
            nets = Net.objects.all().prefetch_related('device', 'vlan')
        else:
            try:
                root_net = Net.objects.get(pk=root_id)
            except Net.DoesNotExist:
                root_net = root_nets[0]
            nets = Net.objects.filter(ipaddress_from__gte=root_net.ipaddress_from,
                                      ipaddress_to__lte=root_net.ipaddress_to,
                                      netmask__gte=root_net.netmask)
    else:
        nets = Net.objects.all().prefetch_related('device', 'vlan')

    if root_net:
        nodes = Nets(nets, root_net=root_net).filled_nodes()
    else:
        nodes = Nets(nets).filled_nodes()
    response = render(request, 'bs3/nets/nets.html', {'nodes': nodes,
                                                  'app': 'nets',
                                                  'root': root_net,
                                                  'root_nets': root_nets})

    if root_id:
        root_id == int(root_id)
    else:
        root_id = 0
    response.set_cookie('root_net', root_id)

    return response


def view_root_nets(request):
    mode = request.GET.get('mode', 'view')

    if request.method == "GET":
        root_nets = get_root_nets()

        root_nets_txt = ""
        for net in root_nets:
            root_nets_txt += (str(net)) + "\n"

        return render(request, 'bs3/nets/root_nets.html', {'mode': mode, 'tab': 'settings',
                                                       'root_nets_txt': root_nets_txt,
                                                       'root_nets': root_nets})

    else:
        root_nets_data = request.POST.get('root_nets', "").strip()
        root_nets_txt = root_nets_data.strip()

        root_nets = []

        for l in root_nets_data.splitlines():
            p = l.split("/")
            if len(p) < 2:
                messages.add_message(request, messages.ERROR, 'Неправильный формат сети: "%s"' % l)
                return render(request, 'bs3/nets/root_nets.html',
                              {'mode': mode, 'tab': 'settings', 'root_nets_txt': root_nets_txt,
                               'root_nets': root_nets})
            else:
                address = p[0].strip()
                netmask = int(p[1].strip())
                try:
                    root_net = Net.objects.filter(address=address, netmask=netmask).first()
                except:
                    root_net = None
                    messages.add_message(request, messages.ERROR, 'Неправильный формат сети: "%s"!' % l)
                    return render(request, 'bs3/nets/root_nets.html', {'mode': mode, 'tab': 'settings',
                                                                   'root_nets_txt': root_nets_txt,
                                                                   'root_nets': root_nets})

                if root_net:
                    root_nets.append(root_net)
                else:
                    messages.add_message(request, messages.ERROR, 'Сеть не существует: "%s"' % l)
                    return render(request, 'bs3/nets/root_nets.html', {'mode': mode,
                                                                   'root_nets_txt': root_nets_txt,
                                                                   'root_nets': root_nets})

        with open('root_nets.txt', 'w') as f:
            for net in root_nets:
                f.write(net.network + '\n')
        messages.add_message(request, messages.SUCCESS, 'Табы обновлены')
    return redirect(view_root_nets)


def get_root_nets():
    tabs = []
    try:
        with open('root_nets.txt', 'r') as f:
            for l in f.readlines():
                tabs.append(l)
    except:
        f = open('root_nets.txt', 'w')
        f.write("")
        f.close()
        tabs = []

    root_nets = []
    for tab in tabs:
        p = tab.split('/')
        try:
            root_net = Net.objects.filter(address=p[0], netmask=int(p[1])).first()
        except:
            root_net = None

        if root_net:
            root_nets.append(root_net)

    return root_nets
