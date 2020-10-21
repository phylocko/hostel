import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render, get_object_or_404, reverse

from hostel.common.models import Service
from hostel.settings import LOGIN_URL
from hostel.spy.models import Spy
from hostel.tracker.models import Rt
from .forms import *
from .models import InsSearch, Incident, Notification, NotificationMessage
from hostel.service.email import MailError


@login_required(login_url=LOGIN_URL)
def incident_view(request, incident_id):
    context = {'app': 'ins'}
    incident = get_object_or_404(Incident, pk=incident_id)
    context['incident'] = incident

    impact_time, text_parsed = incident.parse_intervals(incident.fiber)
    context['impact_time'] = impact_time
    context['text_parsed'] = text_parsed

    tab = request.GET.get('tab', 'services')
    context['tab'] = tab

    notifications = Notification.objects.filter(incident=incident).order_by('-date_added')
    notification_form = NotificationForm(incident=incident)
    context['notifications'] = notifications
    context['notification_form'] = notification_form

    context['warnings'] = incident.warnings()

    if request.POST:
        action = request.POST.get('action')

        if action == 'delete_service':
            service_id = request.POST.get('service_id')
            service = common_models.Service.objects.get(pk=service_id)
            incident.services.remove(service)
            url = reverse(incident_view, args=[incident.pk])
            url += '?tab=%s' % tab
            return redirect(url)

        if action == 'delete_subservice':
            subservice_id = request.POST.get('subservice_id')
            subservice = get_object_or_404(incident.subservices, pk=subservice_id)
            incident.subservices.remove(subservice)
            url = reverse(incident_view, args=[incident.pk])
            url += '?tab=%s' % tab
            return redirect(url)

        if action == 'copy_ins':

            copy_clients = request.POST.get('copy_clients')
            copy_services = request.POST.get('copy_services')
            copy_subservices = request.POST.get('copy_subservices')
            copy_leases = request.POST.get('copy_leases')

            clients = incident.clients.all()
            services = incident.services.all()
            subservices = incident.subservices.all()
            leases = incident.leases.all()

            incident.pk = None
            incident.creator = request.user.profile
            incident.save()

            if copy_clients:
                for client in clients:
                    incident.clients.add(client)

            if copy_services:
                for service in services:
                    incident.services.add(service)

            if copy_subservices:
                for subservice in subservices:
                    incident.subservices.add(subservice)

            if copy_leases:
                for lease in leases:
                    incident.leases.add(lease)

            messages.add_message(request, messages.SUCCESS, 'Инцидент скопирован')
            return redirect(incident_view, incident_id=incident.pk)

        if action == 'delete_client':
            client_id = request.POST.get('client_id')
            client = get_object_or_404(Client, pk=client_id)
            incident.clients.remove(client)
            url = reverse(incident_view, args=[incident.pk])
            url += '?tab=%s' % tab
            return redirect(url)

        if action == 'delete_lease':
            lease_id = request.POST.get('lease_id')
            lease = get_object_or_404(common_models.Lease, pk=lease_id)
            incident.leases.remove(lease)
            url = reverse(incident_view, args=[incident.pk])
            url += '?tab=%s' % tab
            return redirect(url)

        if action == 'delete_incident':
            Spy().log(object=incident, form=None, user=request.user, action=Spy.DELETE)
            incident.delete()
            messages.add_message(request, messages.SUCCESS, 'INS удален')
            return redirect(reverse('ins'))

        if action == 'get_services_from_leases':
            services = Service.objects \
                .filter(lease__in=incident.leases.all()) \
                .exclude(pk__in=incident.services.all()) \
                .distinct()
            if services:
                for service in services:
                    incident.services.add(service)
                messages.success(request, 'Услуги успешно добавлены [%s]' % services.count())
            else:
                if incident.services.count():
                    messages.success(request, 'Услуг, кроме уже добалвенных, не обнаружено')
                else:
                    messages.warning(request, 'Услуг не обнаружено')
            url = reverse(incident_view, args=[incident.pk])
            url += '?tab=%s' % tab
            return redirect(url)

        if action == 'get_subservices_from_leases':
            subservices = common_models.SubService.objects.filter(
                leases__in=incident.leases.all()
            ).exclude(
                pk__in=incident.subservices.all()
            ).distinct()

            if subservices:
                for subservice in subservices:
                    incident.subservices.add(subservice)
                messages.success(request, 'Услуги успешно добавлены [%s]' % subservices.count())
            else:
                messages.warning(request, 'Услуг не обнаружено')

            url = reverse(incident_view, args=[incident.pk])
            url += '?tab=%s' % tab
            return redirect(url)

        if action == 'disturb_provider':
            subject = request.POST.get('subject')
            message = request.POST.get('message')
            email = request.POST.get('email')

            try:
                tracker = Rt()
            except Rt.LoginError as e:
                messages.add_message(request, messages.ERROR, e)
                return redirect(incident_view, incident_id=incident.pk)

            ticket_id = tracker.create_ticket(Subject=subject, Requestors=email)
            if request.user.profile.email:
                tracker.edit_ticket(ticket_id, AdminCc=request.user.profile.email, CF_ins=str(incident.pk))

            if message:
                tracker.reply(ticket_id, text=message)

            incident.ticket = ticket_id
            incident.save()
            messages.add_message(request, messages.SUCCESS,
                                 'Тикет RT#%s успешно создан и привязан к инциденту' % ticket_id)
            return redirect(incident_view, incident_id=incident.pk)

        if action == 'rt_fill_ins':

            if not incident.ticket:
                messages.warning(request, '#RT не указан в INS')
                return redirect(incident_view, incident_id=incident.pk)

            try:
                tracker = Rt()
            except Rt.LoginError as e:
                messages.add_message(request, messages.ERROR, e)
                return redirect(incident_view, incident_id=incident.pk)

            ticket = tracker.tracker.get_ticket(incident.ticket)

            ticket_changes = {}

            rt_ins = ticket.get('CF.{INS}')
            ins_id = str(incident.pk)

            rt_start = ticket.get('CF.{maintenance_start}')
            ins_start = incident.time_start.strftime('%Y-%m-%d %H:%M:%S')

            rt_end = ticket.get('CF.{maintenance_start}')
            ins_end = incident.time_end.strftime('%Y-%m-%d %H:%M:%S')

            # CF_ins
            if rt_ins:
                if ins_id != rt_ins:
                    ticket_changes['CF_ins'] = ins_id
            else:
                ticket_changes['CF_ins'] = ins_id

            # CF_maintenance_start
            ticket_changes['CF_maintenance_start'] = ins_start

            # CF_maintenance_end
            ticket_changes['CF_maintenance_end'] = ins_end

            tracker.edit_ticket(incident.ticket, **ticket_changes)
            messages.success(request, 'Тикет RT обновлен')
            return redirect(incident_view, incident_id=incident.pk)

        if action == 'add_notification':
            notification_form = NotificationForm(request.POST, incident=incident)
            context['notification_form'] = notification_form
            if notification_form.is_valid():

                clients_count = incident.clients.count()
                services_count = incident.services.count()
                subservices_count = incident.subservices.count()
                message_text = notification_form.cleaned_data['text']

                # if no clients or services
                if not any([clients_count, services_count, subservices_count]):
                    messages.error(request, 'Не указаны клиенты или услуги')

                # clients and '%services%' in text
                if clients_count > 0 and Notification.SERVICES_TEMPLATE in message_text:
                    error_text = 'Нельзя отправить письма по клиентам: "%s" в тексте' % Notification.SERVICES_TEMPLATE
                    messages.error(request, error_text)
                    url = reverse(incident_view, args=[incident.pk])
                    url += '?tab=messages'
                    return redirect(url)

                notification_form.instance.who_added = request.user.profile
                notification = notification_form.save()
                notification.email_all()

                if incident.rt:
                    comment_text = 'Отправлено оповещение:\r\n\r\n--\r\n'
                    comment_text += notification.text
                    tracker = Rt()
                    tracker.comment(incident.rt, text=comment_text)

                messages.success(request, 'Уведомление добавлено')
                url = reverse(incident_view, args=[incident.pk])
                url += '?tab=messages'
                return redirect(url)

    logs = Spy.objects.filter(object_name='incident', object_id=incident.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/ins/incident.html', context)


@login_required(login_url=LOGIN_URL)
def last_changed_incident(request):
    last_incident = Incident.objects.all().order_by('-updated').first()
    if last_incident:
        return redirect(reverse('incident', args=[last_incident.pk]))
    messages.warning(request, 'Инцидентов еще нет')
    return redirect(reverse('ins'))


@login_required(login_url=LOGIN_URL)
@permission_required('ins.change_incident')
def incident_update(request, incident_id):
    context = {'app': 'ins'}
    incident = get_object_or_404(Incident, pk=incident_id)

    form = InsForm(instance=incident)

    if request.POST:
        form = InsForm(request.POST, instance=incident)
        if form.is_valid():
            old_object = Incident.objects.get(pk=incident.pk)
            Spy().changed(form.instance, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные Incident обновлены')
            return redirect(incident_view, incident_id=form.instance.pk)

    context['form'] = form
    context['incident'] = incident

    logs = Spy.objects.filter(object_name='incident', object_id=incident.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/ins/incident_update.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('ins.add_incident')
def incident_create(request):
    context = {'tab': 'add', 'app': 'ins'}

    initial = {
        'time_start': datetime.now().replace(minute=0, second=0).strftime('%Y-%m-%d %H:%M:%S'),
        'time_end': datetime.now().replace(minute=0, second=0).strftime('%Y-%m-%d %H:%M:%S')
    }

    for field in InsForm.Meta.fields:
        value = request.GET.get(field, '')
        if value:
            if field == 'fiber':
                value = value.replace(', ', ', \n').strip()
            initial[field] = value

    form = InsForm(request.POST or None, initial=initial)

    if form.is_valid():
        form.instance.creator = request.user
        form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, "INS успешно создан")
        return redirect(incident_view, incident_id=form.instance.pk)
    context['form'] = form
    return render(request, 'bs3/ins/incident_create.html', context)


@login_required(login_url=LOGIN_URL)
def incident_create_from_rt(request):
    context = {'app': 'ins'}

    initial = {'name': 'Плановые работы подрядчика', 'type': 'work'}

    form = InsFromRTForm(request.POST or None, initial=initial)
    context['form'] = form

    if form.is_valid():

        incident = Incident()

        name = form.cleaned_data['name']
        incident.name = name

        incident_type = form.cleaned_data['incident_type']
        incident.type = incident_type

        ticket_id = form.cleaned_data['rt']
        incident.rt = ticket_id

        try:
            tracker = Rt()
        except Rt.LoginError as e:
            messages.add_message(request, messages.ERROR, e)
            return redirect(incident_create_from_rt)

        ticket = tracker.tracker.get_ticket(ticket_id)
        maintenance_start = ticket.get('CF.{maintenance_start}')
        maintenance_end = ticket.get('CF.{maintenance_end}')
        clientname = ticket.get('CF.{ClientName}')

        if not maintenance_start or not maintenance_end:
            messages.error(request, 'Тикет не содержит даты начала и окончания')
            return render(request, 'bs3/ins/incident_create_from_rt.html', context)

        time_start = datetime.strptime(maintenance_start, '%Y-%m-%d %H:%M:%S') + timedelta(hours=3)
        time_end = datetime.strptime(maintenance_end, '%Y-%m-%d %H:%M:%S') + timedelta(hours=3)
        incident.time_start = time_start
        incident.time_end = time_end

        if clientname:
            try:
                client = Client.objects.get(netname=clientname)
            except Client.DoesNotExist:
                messages.warning(request, 'Не существует клиента %s' % clientname)
            else:
                incident.provider = client
        else:
            messages.warning(request, 'Тикет не содержит ClientName')

        incident.save()
        return redirect(incident_view, incident_id=incident.pk)

    return render(request, 'bs3/ins/incident_create_from_rt.html', context)


@login_required(login_url=LOGIN_URL)
def incident_review(request):
    tab = request.GET.get('tab')

    incidents = Incident.objects.filter(deleted=False, closed=False).order_by('-time_start')
    search_string = request.GET.get('search', '')
    if search_string:
        incidents = InsSearch(queryset=incidents).search(search_string)

    incident_groups = {}
    for t in ['work', 'failure', 'other']:
        incident_groups[t] = incidents.filter(type=t)

    context = {'incident_groups': incident_groups, 'app': 'ins', 'tab': 'review', 'search_string': search_string}
    return render(request, 'bs3/ins/incident_review.html', context)


@login_required(login_url=LOGIN_URL)
def closed_ins(request):
    incidents = Incident.objects.filter(deleted=False, closed=True).order_by('-created')
    search_string = request.GET.get('search', '')
    if search_string:
        incidents = InsSearch(queryset=incidents).search(search_string).order_by('created')

    p = request.GET.get('page', 1)
    paginator = Paginator(incidents, request.user.pagination_count)
    page = paginator.page(p)

    context = {'listing': page,
               'app': 'ins',
               'tab': 'closed',
               'paginator': paginator,
               'p': page,
               'search_string': search_string}

    return render(request, 'bs3/ins/incident_list.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('ins.change_incident')
def choose_clients(request, incident_id):
    context = {'app': 'ins'}
    incident = get_object_or_404(Incident, pk=incident_id)
    context['incident'] = incident
    filter_form = ClientFilterForm()

    if request.POST:
        action = request.POST.get('action', None)

        services = common_models.Service.objects.filter(status__in=['on', 'test'])
        services = services.filter(client__enabled=True)
        services = services.order_by('client__netname')

        if action == 'filter_services':

            filter_form = ClientFilterForm(request.POST)

            if filter_form.is_valid():

                if filter_form.has_changed():
                    if filter_form.cleaned_data['from_leases']:
                        services = services.filter(lease__in=incident.leases.all())
                else:
                    services = common_models.Service.objects.none()

                if filter_form.cleaned_data['client']:
                    services = services.filter(client__in=filter_form.cleaned_data['client'])

                if filter_form.cleaned_data['city']:
                    services = services.filter(cities__in=filter_form.cleaned_data['city'])

                if filter_form.cleaned_data['service_name']:
                    names = [x.name for x in filter_form.cleaned_data['service_name']]
                    services = services.filter(name__in=names)

                if filter_form.cleaned_data['device']:
                    services = services.filter(bundle_vlans__bundle__device__in=filter_form.cleaned_data['device'])

                if filter_form.cleaned_data['device_negative']:
                    services = services.exclude(
                        bundle_vlans__bundle__device__in=filter_form.cleaned_data['device_negative'])

                if filter_form.cleaned_data['keywords']:
                    services = services.filter(Q(pk__icontains=filter_form.cleaned_data['keywords']) |
                                               Q(description__icontains=filter_form.cleaned_data['keywords']) |
                                               Q(name__icontains=filter_form.cleaned_data['keywords']) |
                                               Q(comment__icontains=filter_form.cleaned_data['keywords']))
                    if filter_form.cleaned_data['keywords'].isdecimal():
                        services = services.filter(pk=int(filter_form.cleaned_data['keywords']))

                services = services.distinct()

                context['services'] = services
                clients = []
                for s in services:
                    if s.client not in clients:
                        clients.append(s.client)
                context['clients'] = clients

        if action == 'add_clients':
            client_ids = request.POST.getlist('client')
            clients = Client.objects.filter(pk__in=client_ids)
            for c in clients:
                incident.clients.add(c)

            messages.add_message(request, messages.SUCCESS, 'Клиенты добавлены в INS')
            url = reverse(incident_view, args=[incident.pk])
            url += '?tab=clients'
            return redirect(url)

        if action == 'add_services':
            service_ids = request.POST.getlist('service')
            services = common_models.Service.objects.filter(pk__in=service_ids)
            for service in services:
                incident.services.add(service)
            messages.add_message(request, messages.SUCCESS, 'Услуги добавлены в INS')
            url = reverse(incident_view, args=[incident.pk])
            url += '?tab=services'
            return redirect(url)

    context['filter_form'] = filter_form

    return render(request, 'bs3/ins/choose_clients.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('ins.change_incident')
def choose_subservices(request, incident_id):
    context = {'app': 'ins'}
    incident = get_object_or_404(Incident, pk=incident_id)
    context['incident'] = incident
    filter_form = ClientFilterForm()

    subservices = common_models.SubService.objects.none()
    context['subservices'] = subservices

    if request.POST:
        action = request.POST.get('action', None)

        if action == 'filter_services':

            filter_form = ClientFilterForm(request.POST)
            if filter_form.is_valid():

                if filter_form.has_changed():
                    subservices = common_models.SubService.objects.all() \
                        .filter(service__status__in=['on', 'test']) \
                        .filter(service__client__enabled=True) \
                        .order_by('service__client__netname')

                if filter_form.cleaned_data['client']:
                    clients = filter_form.cleaned_data['client']
                    subservices = subservices.filter(service__client__in=clients)

                if filter_form.cleaned_data['city']:
                    cities = filter_form.cleaned_data['city']
                    subservices = subservices.filter(cities__in=cities)

                if filter_form.cleaned_data['service_name']:
                    names = filter_form.cleaned_data['service_name']
                    names = [x.name for x in names]
                    subservices = subservices.filter(service__name__in=names)

                if filter_form.cleaned_data['keywords']:
                    search_string = filter_form.cleaned_data['keywords']
                    subservices = common_models.SubServiceSearch(queryset=subservices).search(search_string)

                subservices = subservices.distinct()
                context['subservices'] = subservices

        if action == 'add_subservices':
            subservice_ids = request.POST.getlist('subservice')
            subservices = common_models.SubService.objects.filter(pk__in=subservice_ids)
            for subservice in subservices:
                incident.subservices.add(subservice)
            messages.add_message(request, messages.SUCCESS, 'Подуслуги добавлены в INS')
            url = reverse(incident_view, args=[incident.pk])
            url += '?tab=subservices'
            return redirect(url)

    context['filter_form'] = filter_form

    return render(request, 'bs3/ins/choose_subservices.html', context)


@login_required(login_url=LOGIN_URL)
def notification_view(request, incident_id, notification_id):
    context = {'app': 'ins'}

    incident = get_object_or_404(Incident, pk=incident_id)
    context['incident'] = incident

    notification = get_object_or_404(Notification, pk=notification_id)
    context['notification'] = notification

    if request.POST:
        action = request.POST.get('action')
        if action == 'resend_failed':
            failed_messages = notification.notificationmessage_set.filter(ok=False)
            errors = []
            for failed_message in failed_messages:
                try:
                    failed_message.email()
                except MailError as e:
                    errors.append('%s: %s' % (failed_message.client.netname, str(e)))
            if errors:
                messages.warning(request, ', '.join(errors))
            else:
                messages.success(request, 'Сообщения переотправлены')
            url = reverse(notification_view, args=[incident.pk, notification.pk])
            return redirect(url)

    return render(request, 'bs3/ins/notification.html', context)


def client_notification_view(request, incident_id, notification_id, netname):
    context = {'app': 'ins'}

    incident = get_object_or_404(Incident, pk=incident_id)
    context['incident'] = incident

    notification = get_object_or_404(incident.notifications, pk=notification_id)
    context['notification'] = notification

    client = get_object_or_404(Client, netname=netname)
    text = notification.prepare_message(client)
    context['text'] = text

    notification_message = get_object_or_404(NotificationMessage, notification=notification, client=client)
    context['notification_message'] = notification_message

    if request.POST:
        action = request.POST.get('action')
        if action == 'resend':
            try:
                notification_message.email()
            except Exception as e:
                messages.error(request, 'Не удалось отправить: ' + str(e))
            else:
                messages.success(request, 'Оповещение переотправлено')
            url = reverse(client_notification_view, args=[incident.pk, notification.pk, client.netname])
            return redirect(url)

    return render(request, 'bs3/ins/client_notification.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('ins.change_incident')
def choose_leases(request, incident_id):
    context = {'app': 'ins'}
    incident = get_object_or_404(Incident, pk=incident_id)
    context['incident'] = incident
    filter_form = InsLeaseFilterForm()

    leases = common_models.Lease.objects.filter(organization=incident.provider)

    if request.POST:

        action = request.POST.get('action')

        if action == 'filter':
            filter_form = InsLeaseFilterForm(request.POST)
            if filter_form.is_valid():
                if filter_form.cleaned_data['city']:
                    leases = leases.filter(cities__in=filter_form.cleaned_data['city'])

                if filter_form.cleaned_data['keywords']:
                    search_string = filter_form.cleaned_data['keywords']
                    leases = common_models.LeaseSearch(queryset=leases).search(search_string)

                if filter_form.cleaned_data['limit_by_services']:
                    leases = []
                    for service in incident.services.all():
                        if incident.provider:
                            for lease in service.lease.filter(organization=incident.provider):
                                leases.append(lease)
                        else:
                            for lease in service.lease.all():
                                leases.append(lease)

        elif action == 'choose_leases':
            lease_ids = request.POST.getlist('lease')
            leases = common_models.Lease.objects.filter(pk__in=lease_ids)
            for lease in leases:
                incident.leases.add(lease)

            messages.add_message(request, messages.SUCCESS, 'Услуги подрядчиков добавлены в INS')
            url = reverse(incident_view, args=[incident.pk])
            url += '?tab=leases'
            return redirect(url)

    context['leases'] = leases
    context['filter_form'] = filter_form

    return render(request, 'bs3/ins/choose_leases.html', context)


@login_required(login_url=LOGIN_URL)
def outages(request):
    context = {'app': 'ins', 'tab': 'outages'}

    now = datetime.now()

    report_year = now.year if now.month > 1 else now.year - 1
    report_month = now.month - 1 if now.month > 1 else 12

    open_incidents_count = Incident.objects.filter(
        time_start__year=report_year,
        time_start__month=report_month,
        report_outage=True,
        type='failure',
        closed=False,
    ).count()
    context['open_incidents_count'] = open_incidents_count

    incidents = Incident.objects.filter(
        time_start__year=report_year,
        time_start__month=report_month,
        report_outage=True,
        type='failure',
        closed=True,
    ).order_by('-time_start')
    context['incidents'] = incidents

    form = OutageForm(initial={'year': report_year, 'month': report_month})
    context['form'] = form

    provider_ids = [x.provider_id for x in incidents if x.provider_id]
    providers = Client.objects.filter(id__in=provider_ids)
    form.fields['provider'].queryset = providers

    if request.GET:
        form = OutageForm(request.GET)
        context['form'] = form

        form.fields['provider'].queryset = providers

        if form.is_valid():

            open_incidents_count = Incident.objects.filter(
                time_start__year=report_year,
                time_start__month=report_month,
                report_outage=True,
                type='failure',
                closed=False,
            ).count()
            context['open_incidents_count'] = open_incidents_count

            incidents = Incident.objects.filter(
                time_start__year=form.cleaned_data['year'],
                time_start__month=form.cleaned_data['month'],
                report_outage=True,
                type='failure',
                closed=True,
            ).order_by('-time_start')

            if form.cleaned_data['provider']:
                incidents = incidents.filter(provider=form.cleaned_data['provider'])

            if form.cleaned_data['client']:
                incidents = incidents.filter(services__client=form.cleaned_data['client']).distinct()

            if form.cleaned_data['keywords']:
                incidents = InsSearch(queryset=incidents).search(form.cleaned_data['keywords'])

            context['incidents'] = incidents

    context['report_month'] = report_month
    context['report_year'] = report_year

    return render(request, 'bs3/ins/outages.html', context)


def calc(request):
    context = {'app': 'ins', 'tab': 'calc'}

    form = CalcForm()
    if request.method == 'POST':
        form = CalcForm(request.POST)
        if form.is_valid():
            summary_time, text = form.calculated()
            context['summary_time'] = summary_time
            context['text'] = text

    context['form'] = form

    return render(request, 'bs3/ins/calc.html', context)
