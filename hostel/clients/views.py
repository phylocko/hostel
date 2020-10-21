from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect

import hostel.common.models as common_models
from hostel.tracker.models import Rt
from hostel.common.forms import LeaseForm
from hostel.docs.models import Agreement
from hostel.settings import LOGIN_URL
from hostel.spy.models import Spy
from .forms import ClientForm, ClientFilterForm, RequestServiceBGPForm, RequestServiceL2Form
from .models import Client, ClientSearch


@login_required(login_url=LOGIN_URL)
def export_services(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    services = common_models.Service.objects.filter(client=client).order_by('name').order_by('pk')
    links = request.GET.get('links', None)
    context = dict(client=client, services=services, links=links)
    return render(request, 'bs3/clients/export_services.html', context)


@login_required(login_url=LOGIN_URL)
def client_netname_view(request, netname):
    client = get_object_or_404(Client, netname=netname)
    return redirect(client_view, client_id=client.pk)


@login_required(login_url=LOGIN_URL)
def client_view(request, client_id):
    context = {'app': 'clients', 'mode': 'view'}

    client = get_object_or_404(Client, pk=client_id)
    context['client'] = client

    search_string = request.GET.get('search')
    context['search_string'] = search_string

    available_tabs = ['services', 'bgp', 'leases', 'companies', 'graphs', 'archive']
    default_tab = available_tabs[0]

    tab = request.GET.get('tab', default_tab)
    if tab not in available_tabs:
        tab = default_tab
    context['tab'] = tab

    if tab == 'services':
        services = client.services.all().order_by('name', 'pk')
        if search_string:
            services = common_models.ServiceSearch(queryset=services).search(search_string)
        context['services'] = services

    if tab == 'archive':
        archived_services = client.archived_services.all().order_by('name', 'pk')
        context['archived_services'] = archived_services

    elif tab == 'bgp':
        asns = client.asns.all().order_by('asn')
        context['asns'] = asns

    elif tab == 'leases':
        leases = common_models.Lease.objects.filter(organization=client).order_by('-created')
        if search_string:
            leases = common_models.LeaseSearch(queryset=leases).search(search_string)
        context['leases'] = leases

        initial = {'organization': client}
        lease_form = LeaseForm(initial=initial)
        context['lease_form'] = lease_form

    elif tab == 'graphs':
        context['bundles'] = client.bundles()

    logs = Spy.objects.filter(client=client).order_by('-time').prefetch_related('client', 'user')[0:100]
    context['logs'] = logs

    context['our_services_all'] = common_models.Ourservice.objects.all().order_by('name')
    context['our_services_as'] = common_models.Ourservice.objects.filter(tech_type='as')

    action = request.POST.get('action')
    if action == 'disturb_client':
        subject = request.POST.get('subject')
        email = request.POST.get('email')
        message = request.POST.get('message', '')
        message = message.strip()

        if not subject or not email:
            messages.add_message(request, messages.ERROR, 'Не указаны данные')
            return redirect(client_view, client_id=client.pk)

        try:
            tracker = Rt()
        except Rt.LoginError as e:
            messages.add_message(request, messages.ERROR, e)
            return redirect(client_view, client_id=client.pk)

        ticket_id = tracker.create_ticket(Subject=subject, Requestors=email)
        if request.user.profile.email:
            tracker.edit_ticket(ticket_id, AdminCc=request.user.profile.email)

        if message:
            tracker.reply(ticket_id, text=message)

        messages.add_message(request, messages.SUCCESS, 'Тикет RT#%s успешно создан.' % ticket_id)
        return redirect(client_view, client_id=client.pk)

    return render(request, 'bs3/clients/view_client.html', context)


def create_service_request(request, subject=None, message=None, parent_id=None):
    if not subject or not message:
        return

    try:
        tracker = Rt()
    except Rt.LoginError as e:
        messages.add_message(request, messages.ERROR, e)
        return

    ticket_id = tracker.create_ticket(Subject=subject)
    if request.user.profile.email:
        tracker.edit_ticket(ticket_id, AdminCc=request.user.profile.email)

    tracker.comment(ticket_id, text=message)

    if parent_id:
        tracker.edit_link(ticket_id, 'MemberOf', parent_id)

    return ticket_id


@login_required(login_url=LOGIN_URL)
@permission_required('clients.change_client')
def client_update(request, client_id):
    context = {'app': 'clients', 'mode': 'edit'}

    client = get_object_or_404(Client, pk=client_id)
    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            old_object = Client.objects.get(pk=client.pk)
            Spy().changed(client, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные клиента обновлены')
            return redirect(client_view, client_id=form.instance.pk)

    else:
        form = ClientForm(instance=client)

    context['form'] = form
    context['client'] = client
    context['our_services_common'] = common_models.Ourservice.objects.filter(tech_type='common')
    context['our_services_as'] = common_models.Ourservice.objects.filter(tech_type='as')

    return render(request, 'bs3/clients/update_client.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('clients.add_client')
def client_create(request):
    context = {'app': 'clients', 'tab': 'add'}

    form = ClientForm(request.POST or None)
    if form.is_valid():
        form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, "Клиент успешно создан")
        return redirect(client_view, client_id=form.instance.pk)

    context['form'] = form

    return render(request, 'bs3/clients/add_client.html', context)


@login_required(login_url=LOGIN_URL)
def client_list(request):
    context = {'app': 'clients', 'tab': 'filter'}

    clients = Client.objects.all().order_by('-updated')[0:20]

    filter_form = ClientFilterForm(request.GET or None, initial={})
    if filter_form.is_valid():

        clients = Client.objects.all().order_by('netname')
        filter_form = ClientFilterForm(request.GET)
        if filter_form.is_valid():

            clients = Client.objects.all()

            search_string = filter_form.cleaned_data.get('search_string')
            if search_string:
                clients = ClientSearch().search(search_string)

            netname = filter_form.cleaned_data.get('netname')
            if netname:
                clients = clients.filter(netname__icontains=netname)

            manager = filter_form.cleaned_data.get('manager')
            if manager:
                clients = clients.filter(manager__in=manager)

            cities = filter_form.cleaned_data.get('cities')
            if cities:
                clients = clients.filter(city__in=cities)

            status = filter_form.cleaned_data.get('status')
            if status == '+':
                clients = clients.filter(enabled=True)
            elif status == '-':
                clients = clients.filter(enabled=False)

    context['filter_form'] = filter_form
    context['clients'] = clients

    return render(request, 'bs3/clients/client_filter.html', context)


@login_required(login_url=LOGIN_URL)
def client_delete(request):
    client = get_object_or_404(Client, pk=request.POST.get('id'))
    Spy().log(object=client, form=None, user=request.user, action=Spy.DELETE)
    client.delete()
    messages.add_message(request, messages.SUCCESS, 'Клиент «%s» удален' % client.netname)
    return redirect(client_list)


@login_required(login_url=LOGIN_URL)
def request_service(request, client_id):
    context = {'app': 'clients'}

    client = get_object_or_404(Client, pk=client_id)
    context['client'] = client

    tab = request.GET.get('tab', 'bgp')
    context['tab'] = tab

    if tab == 'bgp':

        initial = {'contacts': client.contacts, 'parent_rt': client.ticket or ''}
        form = RequestServiceBGPForm(initial=initial)
        context['form'] = form

        if request.POST:
            form = RequestServiceBGPForm(request.POST)
            if form.is_valid():

                # service caption
                service_names = []
                services_with_types = []
                if form.cleaned_data['inet2_requested']:
                    service_names.append('Inet2')
                    services_with_types.append('Inet2 ' + form.cleaned_data['inet2_type'])

                if form.cleaned_data['wix_requested']:
                    service_names.append('W-IX')
                    services_with_types.append('W-IX ' + form.cleaned_data['wix_type'])
                if form.cleaned_data['bgpinet_requested']:
                    service_names.append('BGP Internet')
                    services_with_types.append('BGP Internet ' + form.cleaned_data['bgpinet_type'])

                service_caption = ' + '.join(service_names)

                subject = '{services} для {netname} ({clientname})'.format(services=service_caption,
                                                                           netname=client.netname,
                                                                           clientname=client.clientname)
                if form.cleaned_data['mode'] == 'test':
                    subject = 'Тест ' + subject

                # composing the message
                message = ''

                # client
                message += '0. Клиент: %s | ' % client.clientname

                # services
                message += '1. Услуги: %s | ' % ', '.join(services_with_types)
                if form.cleaned_data['mode'] == 'commerce':
                    message += 'Сразу в коммерцию\n'
                elif form.cleaned_data['mode'] == 'test':
                    message += 'Тест %s дней\n' % form.cleaned_data['test_period']

                # physics
                message += '2. Физика: %s\n' % form.cleaned_data['ports']

                # contacts
                message += '3. Контакты: %s\n' % form.cleaned_data['contacts']
                if form.cleaned_data['comment']:
                    message += 'Комментарий:\n'
                    message += '%s' % form.cleaned_data['comment']

                # Create RT Ticket
                ticket_id = create_service_request(request, subject, message, parent_id=form.cleaned_data['parent_rt'])
                if ticket_id:
                    messages.success(request, 'Заявка успешно создана, RT#%s' % ticket_id)
                else:
                    messages.error(request, 'Произошла ошибка при создании тикета.')
                return redirect(client_view, client_id=client.pk)

            else:
                messages.error(request, 'Форма содержит ошибки')
                context['form'] = form

    elif tab == 'l2':

        l2_initial = {'contacts': client.contacts, 'parent_rt': client.ticket or ''}
        form = RequestServiceL2Form(initial=l2_initial)
        context['form'] = form

        if request.POST:
            form = RequestServiceL2Form(request.POST)
            if form.is_valid():

                subject = 'Организация L2-канала для %s' % client.clientname

                # composing the message
                message = ''

                # client
                message += '0. Клиент: %s | ' % client.clientname

                # services
                message += '1. Услуга: L2 %s\n' % form.cleaned_data['service_type']

                # physics
                message += '2. Физика: %s\n' % form.cleaned_data['ports']

                # addresses
                message += '3. Точки включения: %s\n' % form.cleaned_data['addresses']

                # contacts
                message += '4. Контакты: %s\n' % form.cleaned_data['contacts']
                if form.cleaned_data['comment']:
                    message += form.cleaned_data['comment']

                # Create RT Ticket
                ticket_id = create_service_request(request, subject, message, parent_id=form.cleaned_data['parent_rt'])
                if ticket_id:
                    messages.success(request, 'Заявка успешно создана, RT#%s' % ticket_id)
                else:
                    messages.error(request, 'Произошла ошибка при создании тикета.')
                return redirect(client_view, client_id=client.pk)

            else:
                messages.error(request, 'Форма содержит ошибки')
                context['form'] = form
    return render(request, 'bs3/clients/request_service.html', context)
