from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import ProtectedError, Count
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect, reverse

from hostel.clients.forms import ClientForm
from hostel.clients.views import client_view
from hostel.docs.models import Application, ApplicationSearch
from hostel.ins.models import Incident
from hostel.settings import LOGIN_URL, MRTG_URL
from hostel.spy.models import Spy
from hostel.templater.models import Templater
from hostel.tracker.models import Rt
from hostel.vlans.forms import VlanForm
from hostel.vlans.models import VlanSearch
from .forms import *
from .models import *


@login_required(login_url=LOGIN_URL)
def home(request):
    try:
        managers = Group.objects.get(name='Managers')
    except Group.DoesNotExist:
        return view_engineer_dashboard(request)

    if managers in request.user.groups.all():
        return view_manager_dashboard(request)
    return view_engineer_dashboard(request)


def logout_page(request):
    logout(request)
    return login_page(request)


def login_page(request):
    if request.method == 'POST':  # Данные приехали, занчит юзер ввел пароль и логин
        username = request.POST.get('login', '')
        password = request.POST.get('password', '')
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                go_next = request.GET.get('next', None)
                if go_next:
                    return redirect(go_next)
                else:
                    return redirect(home)
            else:
                messages.add_message(request, messages.ERROR, 'Аккаунт временно отключен')
        else:
            messages.add_message(request, messages.ERROR, 'Неверные логин/пароль')
    username = ''
    next = request.GET.get('next', '')
    context = {'login': username, 'next': next}
    return render(request, 'bs3/common/login.html', context)


@login_required(login_url=LOGIN_URL)
def view_engineer_dashboard(request):
    recent_clients = Client.objects.all().order_by('-updated')[0:10]

    # Services
    services = Service.objects.filter(status='test', client__enabled=True)

    # Tested services
    tested_services = [x for x in services if x.commercial_status == "on_test"]

    # Tested and expired services
    expired_services = [x for x in services if x.commercial_status == "off_test"]

    # Planned maintenance
    incidents = Incident.objects.filter(closed=False, type='work', time_end__gt=datetime.datetime.now())

    # Log entries
    spy_list = [x for x in Spy.objects.all().order_by('-time')[:20]]
    spy_list.reverse()

    # Birthdays
    today = datetime.datetime.today()
    upcoming_birthdays = User.objects.filter(
        birthday__month=today.month,
        birthday__day__gt=today.day,
        is_active=True)

    birthday_today = User.objects.filter(
        birthday__month=today.month,
        birthday__day=today.day,
        is_active=True)

    recent_calls = Call.objects.all().order_by('-time')[0:6]

    context = {
        'recent_clients': recent_clients,
        'expired_services': expired_services,
        'tested_services': tested_services,
        'incidents': incidents,
        'upcoming_birthdays': upcoming_birthdays,
        'birthday_today': birthday_today,
        'spy_list': spy_list,
        'recent_calls': recent_calls,
    }

    return render(request, 'bs3/dashboard/engineer_dashboard.html', context)


@login_required(login_url=LOGIN_URL)
def view_manager_dashboard(request):
    my_clients = Client.objects.filter(enabled=True, manager=request.user).order_by('netname')

    # Services
    services = Service.objects.filter(client__manager=request.user,
                                      client__enabled=True)

    # Tested services
    tested_services = [x for x in services if x.commercial_status == "on_test"]

    # Tested and expired services
    expired_services = [x for x in services if x.commercial_status == "off_test"]

    # Planned maintenance
    incidents = Incident.objects.filter(closed=False, type='work', deleted=False, time_end__gt=datetime.datetime.now())

    # Log entries
    spy_list = [x for x in Spy.objects.all().order_by('-time')[:20]]
    spy_list.reverse()

    # Birthdays
    today = datetime.datetime.today()
    upcoming_birthdays = Manager.objects.filter(birthday__month=today.month,
                                                birthday__day__gte=today.day,
                                                is_working=True)

    birthday_today = Manager.objects.filter(birthday__month=today.month,
                                            birthday__day=today.day,
                                            is_working=True)

    recent_calls = Call.objects.all().order_by('-time')[0:6]

    context = {
        'my_clients': my_clients,
        'expired_services': expired_services,
        'tested_services': tested_services,
        'incidents': incidents,
        'upcoming_birthdays': upcoming_birthdays,
        'birthday_today': birthday_today,
        'spy_list': spy_list,
        'recent_calls': recent_calls,
    }

    # forms
    client_form = ClientForm()
    context['client_form'] = client_form

    return render(request, 'bs3/dashboard/manager_dashboard.html', context)


@login_required(login_url=LOGIN_URL)
def view_services(request):
    context = {}

    services = Service.objects.all().order_by('client__netname')

    filter_form = ServicesFilterForm(request.GET or None)
    if filter_form.is_valid():

        if filter_form.cleaned_data['name']:
            services = services.filter(name__in=filter_form.cleaned_data['name'])

        if filter_form.cleaned_data['service_type']:
            services = services.filter(servicetype__icontains=filter_form.cleaned_data['service_type'])

        if filter_form.cleaned_data['status']:
            services = services.filter(status__in=filter_form.cleaned_data['status'])

        if filter_form.cleaned_data['manager']:
            services = services.filter(client__manager=filter_form.cleaned_data['manager'])

        has_document = filter_form.cleaned_data['has_document']
        if has_document:
            if has_document == 'yes':
                services = services.filter(application__isnull=False)
            elif has_document == 'no':
                services = services.filter(application__isnull=True)

        if filter_form.cleaned_data['text']:
            services = ServiceSearch(queryset=services).search(filter_form.cleaned_data['text'])

        services = services.distinct()

        if not filter_form.has_changed():
            paginator = Paginator(services, request.user.pagination_count)
            page = request.GET.get('page', 1)
            services = paginator.get_page(page)

    context['filter_form'] = filter_form
    context['listing'] = services

    return render(request, 'bs3/services/view_services.html', context)


@login_required(login_url=LOGIN_URL)
def lease_view(request, lease_id):
    context = {'app': 'lease', 'mode': 'view'}

    tab = request.GET.get('tab', 'services')
    context['tab'] = tab

    lease = get_object_or_404(Lease, pk=lease_id)
    context['lease'] = lease
    logs = Spy.objects.filter(object_name='lease', object_id=lease.pk).order_by('-time')
    context['logs'] = logs

    if tab == 'ins':
        incidents = lease.incident_set.all().order_by('-time_start')[0:100]
        context['incidents'] = incidents

    if tab == 'services':
        services = lease.services.all().order_by('pk')
        context['services'] = services

    if tab == 'subservices':
        subservices = lease.subservices.all().order_by('pk')
        context['subservices'] = subservices

    action = request.POST.get('action')
    if action == 'disturb_provider':
        subject = request.POST.get('subject')
        support_email = request.POST.get('support_email')
        parent_id = request.POST.get('parent_rt')
        message = request.POST.get('message', '')
        message = message.strip()

        if not subject or not support_email or not messages:
            messages.add_message(request, messages.ERROR, 'Не указаны данные')
            return redirect(lease_view, lease_id=lease.pk)

        try:
            tracker = Rt()
        except Rt.LoginError as e:
            messages.add_message(request, messages.ERROR, e)
            return redirect(lease_view, lease_id=lease.pk)

        ticket_id = tracker.create_ticket(Subject=subject, Requestors=support_email)
        if request.user.profile.email:
            tracker.edit_ticket(ticket_id, AdminCc=request.user.profile.email)

        if message:
            tracker.reply(ticket_id, text=message)

        if parent_id:
            tracker.edit_link(ticket_id, 'MemberOf', parent_id)

        report_client = request.POST.get('report_client_check')
        if report_client:
            report_text = request.POST.get('report_text')
            if report_text:
                tracker.reply(parent_id, text=report_text)

        messages.add_message(request, messages.SUCCESS, 'Тикет RT#%s успешно создан.' % ticket_id)
        return redirect(lease_view, lease_id=lease.pk)

    if action == 'release_application':
        lease.application = None
        lease.save()
        messages.add_message(request, messages.SUCCESS, 'Документ отвязан от лизы')
        return redirect(reverse('lease', args=[lease.pk]))

    return render(request, 'bs3/lease/lease_view.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_lease')
def lease_update(request, lease_id):
    context = {'app': 'lease', 'mode': 'edit'}
    lease = get_object_or_404(Lease, pk=lease_id)
    if request.method == "POST":
        form = LeaseForm(request.POST, instance=lease)
        if form.is_valid():
            old_object = Lease.objects.get(pk=lease.pk)
            Spy().changed(lease, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные Lease обновлены')
            return redirect(lease_view, lease_id=form.instance.pk)
    else:
        form = LeaseForm(instance=lease)
    context['form'] = form
    context['lease'] = lease
    return render(request, 'bs3/lease/lease_update.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.add_lease')
def lease_create(request):
    context = {'app': 'lease', 'tab': 'add'}

    service_id = request.POST.get('service_id', None)
    if service_id:
        service = get_object_or_404(Service, pk=service_id)

    form = LeaseForm(request.POST or None)
    if form.is_valid():
        lease = form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, "Lease успешно создан")

        if service_id:
            service.lease.add(lease)
            service.save()
            url = reverse('service', args=[service.pk])
            return redirect(url + '?tab=leases')
        else:
            return redirect(lease_view, lease_id=form.instance.pk)
    context['form'] = form
    return render(request, 'bs3/lease/lease_create.html', context)


@login_required(login_url=LOGIN_URL)
def lease_list(request):
    context = {'app': 'lease', 'tab': 'filter'}

    leases = Lease.objects.all().order_by('-updated')[0:20]

    filter_form = LeaseFilterForm(request.GET or None)
    context['filter_form'] = filter_form

    if filter_form.is_valid():

        leases = Lease.objects.all()

        # keywords
        search_string = filter_form.cleaned_data.get('search_string')
        if search_string:
            leases = LeaseSearch(queryset=leases).search(search_string)

        types = filter_form.cleaned_data.get('types')
        if types:
            leases = leases.filter(type__in=types)

        # is_ours
        is_ours = filter_form.cleaned_data.get('is_ours')
        if is_ours == 'yes':
            leases = leases.filter(is_ours=True)
        elif is_ours == 'no':
            leases = leases.filter(is_ours=False)

        # is_bought
        is_bought = filter_form.cleaned_data.get('is_bought')
        if is_bought == 'yes':
            leases = leases.filter(is_bought=True)
        elif is_bought == 'no':
            leases = leases.filter(is_bought=False)

        # cities
        cities = filter_form.cleaned_data.get('cities')
        if cities:
            leases = leases.filter(cities__in=cities)

        # provider
        providers = filter_form.cleaned_data.get('provider')
        if providers:
            leases = leases.filter(organization__in=providers)

        leases = leases.distinct()

    context['leases'] = leases
    return render(request, 'bs3/lease/leases_filter.html', context)


@login_required(login_url=LOGIN_URL)
def lease_search(request):
    context = {'tab': 'search'}
    search_string = request.GET.get('search', None)
    leases = LeaseSearch().search(search_string)
    context['leases'] = leases
    context['search_string'] = search_string
    return render(request, 'bs3/lease/view_leases.html', context)


@login_required(login_url=LOGIN_URL)
def lease_groups(request):
    context = {}
    lease_groups = LeaseGroup.objects.all().order_by('pk')

    context['lease_groups'] = lease_groups
    return render(request, 'bs3/lease/group_list.html', context)


@login_required(login_url=LOGIN_URL)
def lease_group_view(request, group_id):
    context = {'mode': 'view'}
    lease_group = get_object_or_404(LeaseGroup, pk=group_id)
    context['lease_group'] = lease_group

    initial = {'rt': lease_group.rt, 'group': lease_group}
    lease_form = LeaseForm(initial=initial)
    context['lease_form'] = lease_form

    logs = Spy.objects.filter(object_name='leasegroup', object_id=lease_group.pk).order_by('-time')
    context['logs'] = logs

    if request.POST:
        action = request.POST.get('action')
        if action == 'delete_lease_group':
            try:
                lease_group.delete()
            except ProtectedError:
                messages.error(request, 'Нельзя удалить группу, пока в ней есть лизы')
                return redirect(lease_group_view, group_id=lease_group.pk)
            else:
                Spy().log(object=lease_group, action=Spy.DELETE, user=request.user)
                messages.success(request, 'Группа удалена')
                return redirect(lease_groups)
        if action == 'release_lease':
            lease_id = request.POST.get('lease_id')
            lease = get_object_or_404(Lease, pk=lease_id)
            lease_group.leases.remove(lease)
            Spy().changed(instance=lease_group, request=request)
            messages.success(request, 'Лиз %s отвязан от группы' % lease)
            return redirect(lease_group_view, group_id=lease_group.pk)

    return render(request, 'bs3/lease/group_view.html', context)


@login_required(login_url=LOGIN_URL)
def lease_group_update(request, group_id):
    context = {'mode': 'edit'}

    lease_group = get_object_or_404(LeaseGroup, pk=group_id)
    context['lease_group'] = lease_group

    form = LeaseGroupForm(instance=lease_group)

    if request.POST:
        form = LeaseGroupForm(request.POST, instance=lease_group)
        if form.is_valid():
            old_object = LeaseGroup.objects.get(pk=lease_group.pk)
            Spy().changed(instance=form.instance, old_instance=old_object, form=form, request=request)
            form.save()
            messages.success(request, 'Данные группы обновлены')
            return redirect(lease_group_view, group_id=lease_group.pk)

    context['form'] = form
    return render(request, 'bs3/lease/group_view.html', context)


@login_required(login_url=LOGIN_URL)
def lease_group_create(request):
    context = {}
    form = LeaseGroupForm(request.POST or None)
    if form.is_valid():
        form.save()
        Spy().created(instance=form.instance, form=form, request=request)
        messages.success(request, 'Группа успешно создана')
        return redirect(lease_group_view, group_id=form.instance.pk)

    context['form'] = form
    return render(request, 'bs3/lease/group_create.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.delete_lease')
def lease_delete(request):
    lease = get_object_or_404(Lease, pk=request.POST.get('id'))
    Spy().log(object=lease, form=None, user=request.user, action=Spy.DELETE)
    lease.delete()
    messages.add_message(request, messages.SUCCESS, 'Lease удален')
    return redirect(lease_list)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_lease')
def lease_release_from_service(request):
    if request.method == "POST":
        service = get_object_or_404(Service, pk=request.POST.get("service_id"))
        lease = get_object_or_404(Lease, pk=request.POST.get("lease_id"))
        service.lease.remove(lease)

        messages.add_message(request, messages.SUCCESS, 'Услуга подрядика отвазана от услуги %s' % service)
        return redirect(service_view, service_id=service.pk)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_lease')
def lease_choose_for_service(request):
    if request.method == "POST":
        service = get_object_or_404(Service, pk=request.POST.get("service_id"))
        lease = get_object_or_404(Lease, pk=request.POST.get("lease_id"))
        service.lease.add(lease)
        messages.success(request, 'Лиза привязана')
        url = reverse('service', args=[service.pk])
        return redirect(url + '?tab=leases')
    context = {}
    search_string = request.GET.get('search', '')
    search_string = search_string.strip()

    service = get_object_or_404(Service, pk=request.GET.get("service"))
    leases = Lease.objects.filter(cities__in=service.cities.all()).exclude(pk__in=service.lease.all()).distinct()

    if search_string:
        leases = LeaseSearch(queryset=leases).search(search_string)

    context['search_string'] = search_string
    context['service'] = service
    context['leases'] = leases
    return render(request, 'bs3/lease/choose_lease_for_service.html', context)


# == ==
@login_required(login_url=LOGIN_URL)
@permission_required('common.change_manager')
def user_list_view(request):
    context = {'tab': 'all', 'app': 'managers'}
    managers = User.objects.all().order_by('username')
    search_string = request.GET.get('search', None)
    if search_string:
        context['tab'] = 'search'
        context['search_string'] = search_string
        managers = UserSearch().search(search_string)
    context['managers'] = managers
    return render(request, 'bs3/users/user_list.html', context)


@login_required(login_url=LOGIN_URL)
def employes_view(request):
    context = {'app': 'staff'}
    managers = User.objects.filter(is_active=True).order_by("last_name")
    context['managers'] = managers
    return render(request, 'bs3/staff/view_managers.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.add_manager')
def create_user(request):
    context = {}

    form = UserForm(request.POST or None, request.FILES or None)
    context['form'] = form

    if form.is_valid():
        form.save()
        user = form.instance

        messages.add_message(request, messages.SUCCESS, 'Пользователь успешно создан')
        Spy().created(form.instance, form, request)
        return redirect(reverse('user', args=[user.pk]))

    return render(request, 'bs3/users/add_user.html', context)


@login_required(login_url=LOGIN_URL)
def view_map(request):
    context = {}
    switches = request.GET.get('switches')
    context['switches'] = bool(switches)
    return render(request, 'bs3/map/map.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_manager')
def set_user_password(request):
    manager = get_object_or_404(User, pk=request.POST.get('id', None))
    password = request.POST.get('password')
    manager.set_password(password)
    messages.add_message(request, messages.SUCCESS, "Пароль для пользователя %s изменен" % manager)
    return redirect(reverse('user', args=[manager.pk]))


@login_required(login_url=LOGIN_URL)
def change_profile_password(request):
    user = request.user
    password = request.POST.get('password')
    if password:
        user.set_password(password)
        messages.add_message(request, messages.SUCCESS, "Ваш пароль успешно изменен")
    else:
        messages.add_message(request, messages.ERROR, "Ошибка при изменении пароля")
    return redirect(reverse('profile'))


@login_required(login_url=LOGIN_URL)
def group_list(request):
    context = {'app': 'groups'}
    groups = Group.objects.all().order_by('name')
    context['groups'] = groups
    return render(request, 'bs3/groups/group_list.html', context)


def group_view(request, group_id):
    context = {'app': 'groups', 'mode': 'view'}
    group = get_object_or_404(Group, pk=group_id)
    context['group'] = group

    if request.method == 'POST':
        action = request.POST.get('action', None)
        if action == 'change_user_membership':
            user = get_object_or_404(User, pk=request.POST.get('user_id', None))
            if user in group.user_set.all():
                group.user_set.remove(user)
            else:
                group.user_set.add(user)
            return redirect(group_view, group_id=group.pk)

        if action == 'change_permission_membership':
            permission = get_object_or_404(Permission, pk=request.POST.get('permission_id', None))
            if permission in group.permissions.all():
                group.permissions.remove(permission)
            else:
                group.permissions.add(permission)
            return redirect(group_view, group_id=group.pk)

        if action == 'delete_group':
            group.delete()
            messages.add_message(request, messages.SUCCESS, 'Группа удалена')
            return redirect(group_list)

    permissions = Permission.objects.all().order_by('name')
    context['permissions'] = permissions

    users = User.objects.all().order_by('username')
    context['users'] = users

    return render(request, 'bs3/groups/group.html', context)


@permission_required('auth.add_group')
def group_create(request):
    context = {'app': 'groups'}
    form = GroupForm(request.POST or None)
    if form.is_valid():
        form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, 'Группа создана')
        return redirect(group_view, group_id=form.instance.pk)
    context['form'] = form
    return render(request, 'bs3/groups/group_create.html', context)


@permission_required('auth.change_group')
def group_update(request, group_id):
    context = {'app': 'groups', 'mode': 'edit'}
    group = get_object_or_404(Group, pk=group_id)
    context['group'] = group
    form = GroupForm(instance=group, initial={'users': group.user_set.all()})

    if request.method == 'POST':
        form = GroupForm(instance=group, data=request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные группы обновлены')
            return redirect(group_view, group_id=group.pk)

    context['form'] = form
    return render(request, 'bs3/groups/group.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.view_user')
def view_user(request, user_id):
    context = {}

    shown_user = get_object_or_404(User, pk=user_id)
    context['shown_user'] = shown_user

    form = UserForm(instance=shown_user, initial={'groups': shown_user.groups.all()})
    context['form'] = form

    if request.method == "POST":
        action = request.POST.get('action')

        if action == 'delete_user' and request.user.has_perm('common.delete_user'):
            Spy().deleted(instance=shown_user, request=request)
            shown_user.delete()
            messages.success(request, 'Пользователь удален')
            return redirect(reverse('users'))

    logs = Spy.objects.filter(object_name='user', object_id=shown_user.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/users/user.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_user')
def update_user(request, user_id):
    context = {}

    shown_user = get_object_or_404(User, pk=user_id)
    context['shown_user'] = shown_user

    form = UserForm(instance=shown_user, initial={'groups': shown_user.groups.all()})
    context['form'] = form

    if request.method == "POST":
        form = UserForm(request.POST, request.FILES, instance=shown_user)

        if form.is_valid():
            form.save()

            if form.cleaned_data['groups'] is not None:
                shown_user.groups.clear()
                for group in form.cleaned_data['groups']:
                    shown_user.groups.add(group)

            messages.add_message(request, messages.SUCCESS, 'Данные обновлены')
            Spy().log(object=form.instance, action=Spy.CHANGE, user=request.user)

            return redirect(reverse('user', args=[shown_user.pk]), user_id=shown_user.pk)

    logs = Spy.objects.filter(object_name='user', object_id=shown_user.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/users/user_update.html', context)


@login_required(login_url=LOGIN_URL)
def employee_view(request, employee_id):
    manager = get_object_or_404(User, pk=employee_id)
    return render(request, 'bs3/staff/view_manager.html', {'manager': manager})


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_city')
def update_city(request, city_id):
    city = get_object_or_404(City, pk=city_id)
    if request.method == "POST":
        form = CityForm(request.POST, instance=city)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, "Данные города обновлены")
            return redirect(city_view, city_id=city.pk)
    else:
        form = CityForm(instance=city)
        context = {'form': form, 'mode': 'edit', 'city': city}
    return render(request, 'bs3/cities/view_city.html', context)


@login_required(login_url=LOGIN_URL)
def profile_view(request):
    context = {}

    profile = request.user

    form = UserProfileForm(instance=profile)
    context['form'] = form

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        context['form'] = form
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки сохранены')
            return redirect(reverse('profile'))

    return render(request, 'bs3/common/view_user_profile.html', context)


@login_required(login_url=LOGIN_URL)
def bundle_list(request):
    context = {'app': 'bundles'}
    tab = request.GET.get("tab", "latest")
    if tab not in ['latest', 'all', 'backbone', 'client']:
        tab = 'latest'

    if tab == 'latest':
        bundles = Bundle.objects.all().order_by("-created").prefetch_related('device')[0:100]

    context['bundles'] = bundles
    context['tab'] = tab

    return render(request, 'bs3/bundles/bundle_list.html', context)


@login_required(login_url=LOGIN_URL)
def bundle_search(request):
    context = {'app': 'bundles', 'tab': 'search'}
    search_string = request.GET.get('search', None)
    context['search_string'] = search_string
    bundles = BundleSearch().search(search_string)
    context['bundles'] = bundles
    return render(request, 'bs3/bundles/bundle_list.html', context)


@login_required(login_url=LOGIN_URL)
def bundle_view(request, bundle_id):
    context = {'app': 'bundles', 'mode': 'view'}
    tab = request.GET.get('tab', 'recent')
    context['MRTG_URL'] = MRTG_URL
    bundle = get_object_or_404(Bundle, pk=bundle_id)
    context['bundle'] = bundle
    context['tab'] = tab
    tagged_bundle_vlans = BundleVlan.objects.filter(bundle=bundle, mode='tagged').order_by('vlan__vlannum')
    context['tagged_bundle_vlans'] = tagged_bundle_vlans
    untagged_bundle_vlans = BundleVlan.objects.filter(bundle=bundle, mode='untagged').order_by('vlan__vlannum')
    context['untagged_bundle_vlans'] = untagged_bundle_vlans
    bundle_services = Service.objects.filter(bundle_vlans__bundle__in=[bundle]).distinct()
    context['bundle_subservices'] = bundle_services
    bundle_subservices = SubService.objects.filter(bundle_vlans__bundle__in=[bundle]).distinct()
    context['bundle_subservices'] = bundle_subservices

    return render(request, 'bs3/bundles/bundle.html', context)


# == Autonomous System ==
@login_required(login_url=LOGIN_URL)
def autonomoussystem_view(request, autonomoussystem_id):
    context = {'app': 'asn'}
    asn = get_object_or_404(Autonomoussystem, pk=autonomoussystem_id)

    if request.POST:
        action = request.POST.get('action')

        if action == 'move_as':
            client_id = request.POST.get('client')
            if not client_id:
                messages.error(request, 'Не указан клиент')
                return redirect(autonomoussystem_view, autonomoussystem_id=asn.pk)

            new_client = get_object_or_404(Client, pk=client_id)
            asn.client = new_client
            asn.save()
            messages.success(request, 'Автономная система привязана к клиенту %s' % new_client.netname)
            return redirect(reverse('autonomous_system', args=[asn.pk]))

        if action == 'delete_asn':
            client = asn.client
            Spy().log(object=asn, form=None, user=request.user, action=Spy.DELETE)
            asn.delete()
            messages.add_message(request, messages.SUCCESS, '%s удалена' % asn)
            return redirect(reverse('client', args=[client.pk]))

    our_services_as = Ourservice.objects.filter(tech_type='as')
    context['our_services_as'] = our_services_as
    context['asn'] = asn

    logs = Spy.objects.filter(object_name='autonomoussystem', object_id=asn.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/common/autonomoussystems/autonomoussystem_view.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_autonomoussystem')
def autonomoussystem_update(request, autonomoussystem_id):
    context = {'mode': 'edit'}
    asn = get_object_or_404(Autonomoussystem, pk=autonomoussystem_id)
    if request.method == "POST":
        form = ASForm(request.POST, instance=asn)
        if form.is_valid():
            old_object = Autonomoussystem.objects.get(pk=asn.pk)
            Spy().changed(asn, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные AS обновлены')
            return redirect(autonomoussystem_view, autonomoussystem_id=asn.pk)
    else:
        form = ASForm(instance=asn)
    context['form'] = form
    context['asn'] = asn
    return render(request, 'bs3/common/autonomoussystems/autonomoussystem_update.html', context)


@login_required(login_url=LOGIN_URL)
def autonomoussystem_list(request):
    autonomoussystems = Autonomoussystem.objects.all()[0:20]
    return render(request, 'bs3/clients/client_list.html', {'autonomoussystems': autonomoussystems})


@login_required(login_url=LOGIN_URL)
@permission_required('common.add_autonomoussystem')
def autonomoussystem_create(request):
    context = {'app': 'autonomoussystems'}
    client = get_object_or_404(Client, pk=request.GET.get('client'))
    form = ASForm(request.POST or None, initial={'engname': client.netname, 'rt': client.rt})
    if form.is_valid():
        form.instance.client = client
        form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, "AS успешно создана")
        return redirect(autonomoussystem_view, autonomoussystem_id=form.instance.pk)
    context['form'] = form
    context['client'] = client
    return render(request, 'bs3/common/autonomoussystems/add_as.html', context)


@login_required(login_url=LOGIN_URL)
def archiverd_service_view(request, service_id):
    context = {}
    service = get_object_or_404(ArchivedService, pk=service_id)
    context['service'] = service
    params = json.loads(service.params)
    context['params'] = params
    return render(request, 'bs3/services/archived_service.html', context)


@login_required(login_url=LOGIN_URL)
def service_view(request, service_id):
    context = {'app': 'services', 'mode': 'view'}

    service = get_object_or_404(Service, pk=service_id)
    context['service'] = service

    try:
        client_settings = Templater().client_settings(service)
    except Templater.TemplaterError:
        client_settings = ''
    else:
        context['settings'] = client_settings

    logs = Spy.objects.filter(object_name='service', object_id=service.pk).order_by('-time')
    context['logs'] = logs

    tab = request.GET.get('tab', 'params')
    context['tab'] = tab

    search_string = request.GET.get('search')
    if search_string:
        context['search_string'] = search_string

    if tab == 'leases':
        leases = service.lease.all()
        if search_string:
            leases = LeaseSearch(queryset=leases).search(search_string)
        context['leases'] = leases

    if tab == 'ins':
        context['incidents'] = Incident.objects.filter(services=service).order_by('-time_start')

    if tab == 'bundles':
        bundle_vlans = service.bundle_vlans.all()
        context['bundle_vlans'] = bundle_vlans

        bundles = []
        for bundle_vlan in bundle_vlans:
            bundles.append(bundle_vlan.bundle)
        context['bundles'] = bundles

    if tab == 'subservices':
        subservices = service.subservices.all().order_by('sub_id')
        if search_string:
            subservices = SubServiceSearch(queryset=subservices).search(search_string)
        context['subservices'] = subservices

    today_date = datetime.datetime.now().replace(hour=11, minute=0, second=0)
    service_test_end_form = ServiceTestEndForm(initial={'new_expiration_time': today_date})
    context['service_test_end_form'] = service_test_end_form

    if request.POST:
        action = request.POST.get('action')

        if action == 'delete_service':

            delete_nets = False
            delete_vlans = False
            if request.POST.get('delete_nets'):
                delete_nets = True
                messages.success(request, 'Привязанные сети удалены')
            if request.POST.get('delete_vlans'):
                delete_vlans = True
                messages.success(request, 'Привязанные вланы удалены')

            messages.success(request, 'Услуга %s удалена' % service)
            Spy().log(object=service, form=None, user=request.user, action=Spy.DELETE)

            service.delete(delete_nets=delete_nets, delete_vlans=delete_vlans)
            return redirect(client_view, client_id=service.client.pk)

        if action == 'release_vlan':
            vlan = get_object_or_404(Vlan, pk=request.POST.get('vlan_id'))
            vlan.service = None
            vlan.save()
            messages.add_message(request, messages.SUCCESS, 'Влан %s отвязан от услуги' % vlan)
            return redirect(service_view, service_id=service.pk)

        if action == 'release_lease':
            lease = get_object_or_404(Lease, pk=request.POST.get('lease_id'))
            service.lease.remove(lease)
            messages.add_message(request, messages.SUCCESS, 'Лиза отвязана')
            url = reverse('service', args=[service.pk])
            return redirect(url + '?tab=leases')

        if action == 'release_net':
            net = get_object_or_404(Net, pk=request.POST.get('net_id'))
            net.service = None
            net.save()
            messages.add_message(request, messages.SUCCESS, 'Сеть %s отвязана от услуги' % net)
            return redirect(service_view, service_id=service.pk)

        if action == 'release_application':
            service.application = None
            service.save()
            messages.add_message(request, messages.SUCCESS, 'Документ отвязан от услуги')
            return redirect(service_view, service_id=service.pk)

        if action == 'copy_service':
            cities = service.cities.all()
            service.pk = None
            service.save()
            for city in cities:
                service.cities.add(city)
            messages.add_message(request, messages.SUCCESS, 'Услуга скопирована')
            return redirect(service_view, service_id=service.pk)

        if action == 'send_settings':
            if not service.ticket:
                messages.error(request, 'Не указан номер тикета RT')
                return redirect(service_view, service_id=service.pk)

            if not client_settings:
                messages.error(request, 'Настройки не определены')
                return redirect(service_view, service_id=service.pk)

            try:
                tracker = Rt()
            except Rt.LoginError as e:
                messages.error(request, e)
                return redirect(service_view, service_id=service.pk)

            tracker.reply(service.ticket, text=client_settings)
            messages.success(request, 'Настройки отправлены в рамках тикета #%s' % service.ticket)
            return redirect(service_view, service_id=service.pk)

        if action == 'change_test_end_date':
            if not service.ticket:
                messages.error(request, 'Не заполнен номер тикета в описании услуги')
                return redirect(service_view, service_id=service.pk)

            service_test_end_form = ServiceTestEndForm(request.POST)
            context['service_test_end_form'] = service_test_end_form
            if service_test_end_form.is_valid():
                new_expiration_time = service_test_end_form.cleaned_data.get('new_expiration_time')
                service.end_time = new_expiration_time
                if service.status == 'off':
                    service.status = 'test'
                service.save()
                messages.success(request, 'Установлена новая дата окончания теста')

                # Add comment to a ticket
                try:
                    tracker = Rt()
                except Rt.LoginError as e:
                    messages.error(request, e)
                    return redirect(service_view, service_id=service.pk)

                report_text = 'Дата окончания теста услуги %s изменена пользователем %s. ' % (service,
                                                                                              request.user.username)
                report_text += 'Новая дата: %s' % new_expiration_time

                tracker.comment(service.ticket, text=report_text)
                return redirect(service_view, service_id=service.pk)
            else:
                messages.error(request, 'Форма содержит ошибки')
                return redirect(service_view, service_id=service.pk)

        if action == 'set_commerce':
            if not service.ticket:
                messages.error(request, 'Не заполнен номер тикета RT в описании услуги')
                return redirect(service_view, service_id=service.pk)

            service.status = 'on'
            service.save()
            messages.success(request, 'Услуга переведена в коммерцию')

            # Add comment to a ticket
            try:
                tracker = Rt()
            except Rt.LoginError as e:
                messages.error(request, e)
                return redirect(service_view, service_id=service.pk)

            report_text = 'Услуга %s переведена в коммерцию пользователем %s.\r\n' % (service, request.user.username)
            report_text += 'Закрываю.'

            tracker.comment(service.rt, text=report_text)
            try:
                tracker.edit_ticket(service.rt, Status='Resolved')
            except tracker.APISyntaxError:  # thrown when changing 'resolved' to 'resolved'
                pass
            return redirect(service_view, service_id=service.pk)

    lease_initial = dict(cities=service.cities.all(),
                         comment=service.comment,
                         rt=service.ticket)
    lease_form = LeaseForm(initial=lease_initial)
    context['lease_form'] = lease_form

    return render(request, 'bs3/services/service_view.html', context)


@login_required(login_url=LOGIN_URL)
def subservice_view(request, service_id, subservice_id):
    context = {}

    default_tab = 'params'
    tab = request.GET.get('tab', default_tab)
    if tab not in ['leases', 'params', 'bundles']:
        tab = default_tab
    context['tab'] = tab

    service = get_object_or_404(Service, pk=service_id)
    context['service'] = service

    subservice = get_object_or_404(service.subservices, pk=subservice_id)
    context['subservice'] = subservice

    if tab == 'bundles':
        bundle_vlans = subservice.bundle_vlans.all()
        context['bundle_vlans'] = bundle_vlans

        bundles = []
        for bundle_vlan in bundle_vlans:
            bundles.append(bundle_vlan.bundle)
        context['bundles'] = bundles

    if request.POST:
        action = request.POST.get('action')

        if action == 'release_vlan':
            vlan_id = request.POST.get('vlan_id')
            vlan = get_object_or_404(subservice.vlans, pk=vlan_id)
            subservice.vlans.remove(vlan)
            messages.success(request, 'Влан отвязан')
            url = reverse('subservice', args=[service.pk, subservice.pk])
            return redirect(url + '?tab=params')

        if action == 'release_lease':
            lease_id = request.POST.get('lease_id')
            lease = get_object_or_404(subservice.leases, pk=lease_id)
            subservice.leases.remove(lease)
            messages.success(request, 'Лиза отвязана')
            url = reverse('subservice', args=[service.pk, subservice.pk])
            return redirect(url + '?tab=leases')

        if action == 'delete_subservice':
            delete_nets = False
            delete_vlans = False

            if request.POST.get('delete_nets'):
                delete_nets = True
                messages.success(request, 'Привязанные сети удалены')
            if request.POST.get('delete_vlans'):
                delete_vlans = True
                messages.success(request, 'Привязанные вланы удалены')

            messages.success(request, 'Подуслуга %s удалена' % subservice)
            Spy().log(object=subservice, form=None, user=request.user, action=Spy.DELETE)

            subservice.delete(delete_nets=delete_nets, delete_vlans=delete_vlans)
            url = reverse('service', args=[service.pk])
            return redirect(url + '?tab=subservices')

    return render(request, 'bs3/services/subservice_view.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_service')
def subservice_update(request, service_id, subservice_id):
    context = {}
    service = get_object_or_404(Service, pk=service_id)
    context['service'] = service
    subservice = get_object_or_404(service.subservices, pk=subservice_id)
    context['subservice'] = subservice

    form = SubServiceForm(instance=subservice)
    context['form'] = form

    if request.POST:
        form = SubServiceForm(request.POST, instance=subservice)
        if form.is_valid():
            form.save()
            messages.success(request, 'Подуслуга обновлена')
            return redirect(reverse('subservice', args=[service_id, subservice_id]))

    return render(request, 'bs3/services/subservice_update.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_service')
def subservice_create(request, service_id):
    context = {}
    service = get_object_or_404(Service, pk=service_id)
    context['service'] = service

    form = SubServiceForm(request.POST or None, service=service)
    if form.is_valid():
        subservice = form.save()
        messages.success(request, 'Подуслуга создана')
        return redirect(reverse('subservice', args=[service.pk, subservice.pk]))
    context['form'] = form
    return render(request, 'bs3/services/subservice_create.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_service')
def subservice_create_vlan_view(request, service_id, subservice_id):
    context = {}
    service = get_object_or_404(Service, pk=service_id)
    context['service'] = service

    subservice = get_object_or_404(service.subservices, pk=subservice_id)
    context['subservice'] = subservice

    form = VlanForm(request.POST or None)
    if form.is_valid():
        vlan = form.save()
        subservice.vlans.add(vlan)
        messages.success(request, 'Влан создан')
        return redirect(reverse('subservice', args=[service.pk, subservice.pk]))

    context['form'] = form

    free_vlans = Vlanaggregator().freevlans()
    context['free_vlans'] = free_vlans

    return render(request, 'bs3/services/subservice_create_vlan.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_service')
def subservice_create_lease_view(request, service_id, subservice_id):
    context = {}
    service = get_object_or_404(Service, pk=service_id)
    context['service'] = service

    subservice = get_object_or_404(service.subservices, pk=subservice_id)
    context['subservice'] = subservice

    initial = {'rt': subservice.rt, 'cities': subservice.cities.all()}
    form = LeaseForm(request.POST or None, initial=initial)
    if form.is_valid():
        lease = form.save()
        subservice.leases.add(lease)
        messages.success(request, 'Лиза создана')
        url = reverse('subservice', args=[service.pk, subservice.pk])
        return redirect(url + '?tab=leases')

    context['form'] = form

    return render(request, 'bs3/services/subservice_create_lease.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_service')
def subservice_choose_vlan_view(request, service_id, subservice_id):
    context = {}
    service = get_object_or_404(Service, pk=service_id)
    context['service'] = service

    subservice = get_object_or_404(service.subservices, pk=subservice_id)
    context['subservice'] = subservice

    if request.POST:
        vlan_id = request.POST.get('vlan_id')
        vlan = get_object_or_404(Vlan, pk=vlan_id)
        subservice.vlans.add(vlan)
        messages.success(request, 'Влан привязан')
        url = reverse('subservice', args=[service.pk, subservice.pk])
        return redirect(url + '?tab=params')

    vlans = Vlan.objects.filter(is_management=False, service=service)
    vlans = vlans.order_by('vlannum')

    search_string = request.GET.get('search')
    if search_string:
        context['search_string'] = search_string
        vlans = VlanSearch(queryset=vlans).search(search_string)

    context['vlans'] = vlans

    return render(request, 'bs3/services/subservice_choose_vlan.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_service')
def subservice_choose_lease_view(request, service_id, subservice_id):
    context = {}
    service = get_object_or_404(Service, pk=service_id)
    context['service'] = service

    subservice = get_object_or_404(service.subservices, pk=subservice_id)
    context['subservice'] = subservice

    if request.POST:
        lease_id = request.POST.get('lease_id')
        lease = get_object_or_404(Lease, pk=lease_id)
        subservice.leases.add(lease)
        messages.success(request, 'Лиза привязана')
        url = reverse('subservice', args=[service.pk, subservice.pk])
        return redirect(url + '?tab=leases')

    leases = Lease.objects.filter(cities__in=service.cities.all())
    leases = leases.exclude(pk__in=subservice.leases.all())
    leases = leases.order_by('pk')

    search_string = request.GET.get('search')
    if search_string:
        context['search_string'] = search_string
        leases = LeaseSearch().search(search_string)

    context['leases'] = leases

    return render(request, 'bs3/services/subservice_choose_lease.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_service')
def service_update(request, service_id):
    context = {'app': 'service', 'mode': 'edit'}

    return_to = request.GET.get('return_to')
    context['return_to'] = return_to

    service = get_object_or_404(Service, pk=service_id)

    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            old_object = Service.objects.get(pk=service.pk)
            Spy().changed(service, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные услуги обновлены')
            if return_to == 'client':
                return redirect(client_view, client_id=service.client.pk)
            else:
                return redirect(service_view, service_id=form.instance.pk)

    form = ServiceForm(instance=service)
    context['form'] = form
    context['service'] = service

    return render(request, 'bs3/services/service_update.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_service')
def choose_doc_for_service(request, service_id):
    context = {}
    service = get_object_or_404(Service, pk=service_id)
    context['service'] = service

    search_string = request.GET.get('search')
    context['search_string'] = search_string

    applications = Application.objects.filter(agreement__company__in=service.client.companies.all())
    if search_string:
        applications = ApplicationSearch(queryset=applications).search(search_string)
    context['applications'] = applications

    if request.POST:
        application_id = request.POST.get('application_id')
        if application_id:
            application = get_object_or_404(Application, pk=application_id)
            service.application = application
            service.save()
            messages.success(request, 'Документ привязан к услуге')
            return redirect(reverse('service', args=[service_id]))

    return render(request, 'bs3/services/choose_doc.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_lease')
def choose_doc_for_lease(request, lease_id):
    context = {}
    lease = get_object_or_404(Lease, pk=lease_id)
    context['lease'] = lease

    search_string = request.GET.get('search')
    context['search_string'] = search_string

    applications = Application.objects.filter(agreement__company__in=lease.organization.companies.all())
    if search_string:
        applications = ApplicationSearch(queryset=applications).search(search_string)
    context['applications'] = applications

    if request.POST:
        application_id = request.POST.get('application_id')
        if application_id:
            application = get_object_or_404(Application, pk=application_id)
            lease.application = application
            lease.save()
            messages.success(request, 'Документ привязан к лизе')
            return redirect(reverse('lease', args=[lease_id]))

    return render(request, 'bs3/lease/choose_doc.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.add_service')
def service_create(request):
    context = {}
    initial = {}

    client_id = request.GET.get('client_id')
    service_name = request.GET.get('service_name')
    asn_id = request.GET.get('asn_id')
    asn = None
    if asn_id:
        asn = get_object_or_404(Autonomoussystem, pk=asn_id)
        initial['asn'] = asn

    client = get_object_or_404(Client, pk=client_id)
    context['client'] = client

    start_time = datetime.datetime.now()
    start_time = start_time.strftime('%Y-%m-%d %H:%M')
    initial['start_time'] = start_time

    end_time = datetime.datetime.now() + datetime.timedelta(days=14)
    end_time = end_time.replace(hour=11, minute=0, second=0)
    end_time = end_time.strftime('%Y-%m-%d %H:%M')
    initial['end_time'] = end_time

    if service_name not in service_params:
        raise Http404('Нет услуги %s' % service_name)

    form = ServiceForm(service_name=service_name, client=client, asn=asn, initial=initial)
    context['form'] = form

    if request.POST:
        form = ServiceForm(request.POST, service_name=service_name, asn=asn, client=client)
        context['form'] = form
        form.instance.name = service_name
        if form.is_valid():
            service = form.save()

            Spy().created(form.instance, form, request)
            messages.add_message(request, messages.SUCCESS, "Услуга создана")

            return redirect(reverse('service', args=[service.pk]))
    return render(request, 'bs3/services/service_create.html', context)


@login_required(login_url=LOGIN_URL)
def city_view(request, city_id):
    context = {'app': 'city', 'mode': 'view'}
    city = get_object_or_404(City, pk=city_id)
    context['city'] = city

    logs = Spy.objects.filter(object_name='city', object_id=city.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/cities/view_city.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_city')
def city_update(request, city_id):
    context = {'app': 'cities', 'mode': 'edit'}

    city = get_object_or_404(City, pk=city_id)

    if request.method == "POST":
        form = CityForm(request.POST, instance=city)
        if form.is_valid():
            old_object = City.objects.get(pk=city.pk)
            Spy().changed(city, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные клиента обновлены')
            return redirect(city_view, city_id=form.instance.pk)

    else:
        form = CityForm(instance=city)

    context['form'] = form
    context['city'] = city

    return render(request, 'bs3/cities/view_city.html', context)


@login_required(login_url=LOGIN_URL)
def city_create(request):
    context = {'app': 'cities', 'tab': 'add'}

    form = CityForm(request.POST or None)
    if form.is_valid():
        form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, "Клиент успешно создан")
        return redirect(city_view, city_id=form.instance.pk)

    context['form'] = form
    # decorate_city_form(form)

    return render(request, 'bs3/cities/city_create.html', context)


@login_required(login_url=LOGIN_URL)
def city_list(request):
    context = {'tab': 'all', 'app': 'cities'}
    cities = City.objects.all().order_by('name')

    search_string = request.GET.get('search', '')
    context['search_string'] = search_string

    if search_string:
        cities = CitySearch().search(search_string)

    cities = cities.annotate(Count('datacenter__device', distinct=True),
                             Count('services', distinct=True),
                             Count('datacenter', distinct=True))
    context['cities'] = cities
    return render(request, 'bs3/cities/city_list.html', context)


@login_required(login_url=LOGIN_URL)
def city_delete(request):
    city = get_object_or_404(City, pk=request.POST.get('id'))
    Spy().log(object=city, form=None, user=request.user, action=Spy.DELETE)
    city.delete()
    messages.add_message(request, messages.SUCCESS, 'Город «%s» удален' % city.name)
    return redirect(city_list)


@login_required(login_url=LOGIN_URL)
def datacenter_view(request, datacenter_id):
    context = {'app': 'datacenters', 'mode': 'view'}

    datacenter = get_object_or_404(Datacenter, pk=datacenter_id)
    context['datacenter'] = datacenter

    tab = request.GET.get('tab', 'devices')
    if tab not in ('devices', 'racks'):
        tab = 'devices'
    context['tab'] = tab

    if tab == 'devices':
        devices = datacenter.device.all()
        context['devices'] = devices.prefetch_related('store_entry')
    elif tab == 'racks':
        racks = datacenter.rack_set.all()
        context['racks'] = racks

    if request.POST:
        action = request.POST.get('action')
        if action == 'disturb_datacenter':
            subject = request.POST.get('subject')
            message = request.POST.get('message')
            email = request.POST.get('email')
            parent_id = request.POST.get('parent_id')

            if not email:
                messages.error(request, 'Email не указан')
                return redirect(datacenter_view, datacenter_id=datacenter.pk)

            try:
                tracker = Rt()
            except Rt.LoginError as e:
                messages.add_message(request, messages.ERROR, e)
                return redirect(datacenter_view, datacenter_id=datacenter.pk)

            ticket_id = tracker.create_ticket(Subject=subject, Requestors=email)
            if request.user.profile.email:
                tracker.edit_ticket(ticket_id, AdminCc=request.user.profile.email)

            if message:
                tracker.reply(ticket_id, text=message)

            if parent_id:
                tracker.edit_link(ticket_id, 'MemberOf', parent_id)

            messages.success(request, 'Тикет #%s успешно создан' % ticket_id)
        return redirect(datacenter_view, datacenter_id=datacenter.pk)

    try:
        disturb_message = Templater().datacenter_disturb_message(datacenter)
    except Templater.TemplaterError:
        pass
    else:
        context['disturb_message'] = disturb_message

    logs = Spy.objects.filter(object_name='datacenter', object_id=datacenter.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/datacenters/datacenter_view.html', context)


@login_required(login_url=LOGIN_URL)
def rack_list(request):
    context = {'app': 'racks'}
    racks = Rack.objects.order_by('datacenter')
    racks = racks.prefetch_related('datacenter', 'datacenter__city')
    racks = racks.annotate(device_count=Count('device'))
    context['racks'] = racks
    return render(request, 'bs3/racks/rack_list.html', context)


@login_required(login_url=LOGIN_URL)
def rack_view(request, rack_id):
    context = {'app': 'racks'}
    rack = get_object_or_404(Rack, pk=rack_id)
    context['rack'] = rack

    if request.POST:
        action = request.POST.get('action')
        if action == 'delete_rack':
            Spy().log(object=rack, action=Spy.DELETE, user=request.user)
            rack.delete()
            messages.success(request, 'Стойка удалена')
            return redirect(reverse('racks'))

    front_schema, back_schema = rack.facades()
    context['front_schema'] = front_schema
    context['back_schema'] = back_schema

    return render(request, 'bs3/racks/rack.html', context)


@login_required(login_url=LOGIN_URL)
def rack_update(request, rack_id):
    context = {'app': 'racks'}
    rack = get_object_or_404(Rack, pk=rack_id)
    context['rack'] = rack

    form = RackForm(instance=rack)
    context['form'] = form

    if request.POST:
        form = RackForm(request.POST, instance=rack)
        context['form'] = form
        if form.is_valid():
            form.save()
            Spy().log(object=rack, action=Spy.CHANGE, user=request.user, form=form)
            messages.success(request, 'Данные стойки обновлены')
            return redirect(reverse('rack', args=[rack.pk]))

    return render(request, 'bs3/racks/rack_update.html', context)


@login_required(login_url=LOGIN_URL)
def rack_create(request):
    context = {'app': 'racks'}
    form = RackForm(request.POST or None)
    context['form'] = form
    if form.is_valid():
        rack = form.save()
        Spy().log(object=rack, action=Spy.CREATE, user=request.user)
        messages.success(request, 'Стойка успешно создана')
        return redirect(reverse('rack', args=[rack.pk]))
    return render(request, 'bs3/racks/rack_create.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.change_datacenter')
def datacenter_update(request, datacenter_id):
    context = {'app': 'datacenter', 'mode': 'edit'}
    datacenter = get_object_or_404(Datacenter, pk=datacenter_id)
    if request.method == "POST":
        form = DatacenterForm(request.POST, instance=datacenter)
        if form.is_valid():
            old_object = Datacenter.objects.get(pk=datacenter.pk)
            Spy().changed(datacenter, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные Datacenter обновлены')
            return redirect(datacenter_view, datacenter_id=form.instance.pk)
    else:
        form = DatacenterForm(instance=datacenter)
    context['form'] = form
    context['datacenter'] = datacenter
    return render(request, 'bs3/datacenters/datacenter_view.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.add_datacenter')
def datacenter_create(request):
    context = {'app': 'datacenters', 'tab': 'add'}
    form = DatacenterForm(request.POST or None)
    if form.is_valid():
        form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, "Datacenter успешно создан")
        return redirect(datacenter_view, datacenter_id=form.instance.pk)
    context['form'] = form
    return render(request, 'bs3/datacenters/datacenter_create.html', context)


@login_required(login_url=LOGIN_URL)
def datacenter_list(request):
    context = {'app': 'datacenter', 'tab': 'all'}
    datacenters = Datacenter.objects.all() \
        .prefetch_related('device', 'organization', 'city') \
        .order_by('city__name', 'address')
    context['datacenters'] = datacenters

    search_string = request.GET.get('search', '')
    context['search_string'] = search_string
    if search_string:
        datacenters = DatacenterSearch(queryset=datacenters).search(search_string)
        context['datacenters'] = datacenters

    return render(request, 'bs3/datacenters/view_datacenters.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('common.delete_datacenter')
def datacenter_delete(request):
    datacenter = get_object_or_404(Datacenter, pk=request.POST.get('id'))
    Spy().log(object=datacenter, form=None, user=request.user, action=Spy.DELETE)
    datacenter.delete()
    messages.add_message(request, messages.SUCCESS, 'Datacenter удален')
    return redirect(datacenter_list)


@login_required(login_url=LOGIN_URL)
def number_list_view(request):
    context = {'tab': 'numbers'}
    numbers = Phone.objects.all().order_by('-count')[0:100]

    search_string = request.GET.get('search')
    context['search_string'] = search_string
    if search_string:
        numbers = PhoneSearch().search(search_string)

    paginator = Paginator(numbers, request.user.pagination_count)
    page = request.GET.get('page', 1)
    listing = paginator.get_page(page)

    context['listing'] = listing

    return render(request, 'bs3/cc/number_list.html', context)


@login_required(login_url=LOGIN_URL)
def number_view(request, number_id):
    context = {}
    phone = get_object_or_404(Phone, pk=number_id)
    context['phone'] = phone

    calls = Call.objects.filter(phone=phone).order_by('-time')[0:200]
    context['calls'] = calls

    return render(request, 'bs3/cc/number.html', context)


@login_required(login_url=LOGIN_URL)
def update_number_view(request, number_id):
    context = {}
    phone = get_object_or_404(Phone, pk=number_id)
    context['phone'] = phone

    form = PhoneForm(instance=phone)
    context['form'] = form

    if request.POST:
        form = PhoneForm(request.POST, instance=phone)
        context['form'] = form
        if form.is_valid():
            form.save()
            messages.success(request, 'Телефон обновлён')
            return redirect(reverse('number', args=[phone.pk]))

    return render(request, 'bs3/cc/update_number.html', context)


@login_required(login_url=LOGIN_URL)
def call_list_view(request):
    context = {'tab': 'calls'}

    calls = Call.objects.all().order_by('-time')

    search_string = request.GET.get('search')
    context['search_string'] = search_string
    if search_string:
        calls = CallSearch().search(search_string)

    paginator = Paginator(calls, request.user.pagination_count)
    page = request.GET.get('page', 1)
    listing = paginator.get_page(page)

    context['listing'] = listing
    return render(request, 'bs3/cc/call_list.html', context)
