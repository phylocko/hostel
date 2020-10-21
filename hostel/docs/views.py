from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect, reverse

import hostel.common.helper_functions as h
from hostel.clients.models import Client
from hostel.companies.models import Company
from hostel.settings import LOGIN_URL
from hostel.spy.models import Spy
from .forms import AgreementForm, ApplicationForm
from .models import Application, Agreement, ApplicationSearch, AgreementSearch


@login_required(login_url=LOGIN_URL)
@permission_required('docs.delete_agreement')
def delete_agreement(request):
    agreement = get_object_or_404(Agreement, pk=request.POST.get('id'))
    try:
        agreement.delete()
    except:
        messages.add_message(request, messages.ERROR, "Ошибка при удалении документа.")
        return redirect(view_agreement, agreement_id=agreement.pk)
    Spy().log(object=agreement, action=Spy.DELETE, user=request.user)

    messages.add_message(request, messages.SUCCESS, "Договор и все сопутствующие файлы удалены")

    return redirect(view_agreements)


@login_required(login_url=LOGIN_URL)
@permission_required('docs.change_agreement')
def delete_agreement_file(request):
    agreement = get_object_or_404(Agreement, pk=request.POST.get('id'))
    agreement.delete_file()
    messages.add_message(request, messages.SUCCESS, "Скан договора удален.")
    return redirect(view_agreement, agreement_id=agreement.pk)


@login_required(login_url=LOGIN_URL)
@permission_required('docs.add_agreement')
def add_agreement(request):
    if request.method == 'POST':  # Если данные приехали из POST, то пытаемся добавить клиента
        form = AgreementForm(request.POST)

        if form.is_valid():
            try:
                form.instance.creator = request.user
                form.save()
                Spy().log(object=form.instance, form=form, action=Spy.CREATE, user=request.user)
            except:
                messages.add_message(request, messages.ERROR, 'Ошибка целостности БД.')
                context = {'form': form, 'app': 'docs', 'tab': 'add'}
                return render(request, 'bs3/docs/add_agreement.html', context)

            agreement = form.instance

            # Trying to handle file if exists
            if request.FILES.get('file'):
                result = agreement.handle_file(request.FILES['file'])
                if result:
                    messages.add_message(request, messages.SUCCESS, 'Файл "%s" успешно загружен' % result)
                else:
                    messages.add_message(request, messages.ERROR, "Ошибка сохранения файла")
            else:
                messages.add_message(request, messages.ERROR, "Загрузите скан документа")

            Spy().log(object=agreement, action=Spy.CREATE, user=request.user)
            return redirect(view_agreement, agreement_id=agreement.pk)

        else:
            choices = [('', '')]
            clients = Client.objects.filter(clientname__isnull=False).order_by("clientname")
            for client in clients:
                choice = (client.pk, "%s — %s" % (client.clientname, client.netname))
                choices.append(choice)

            form = h.inject_choices(form=form, field_name='client',
                                    choices=choices, required=False)

            messages.add_message(request, messages.ERROR, 'Форма содержит ошибки')
            context = {'form': form, 'app': 'docs', 'tab': 'add'}
            return render(request, 'bs3/docs/add_agreement.html', context)

    else:
        initial = {}
        company_id = request.GET.get('company')
        if company_id:
            initial['company'] = get_object_or_404(Company, pk=company_id)
        form = AgreementForm(initial=initial)

        context = {'form': form, 'app': 'docs', 'tab': 'add'}
        return render(request, 'bs3/docs/add_agreement.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('docs.add_application')
def add_application(request, agreement_id):
    context = {'app': 'docs'}
    agreement = get_object_or_404(Agreement, pk=agreement_id)
    context['agreement'] = agreement
    form = ApplicationForm()
    context['form'] = form

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        context['form'] = form

        if form.is_valid():

            agreement = Agreement.objects.get(pk=agreement_id)

            try:
                form.instance.agreement = agreement
                form.instance.creator = request.user
                Spy().log(object=form.instance, form=form, action=Spy.CREATE, user=request.user)
                form.save()
            except Exception as e:
                messages.add_message(request, messages.ERROR, 'Ошибка целостности БД: %s' % e)
                context = {'form': form, 'app': 'docs'}
                return render(request, 'bs3/docs/add_application.html', context)

            application = form.instance
            application.agreement = agreement
            application.save()

            # Trying to handle file if exists
            if request.FILES.get('file'):
                result = application.handle_file(request.FILES['file'])
                if result:
                    messages.add_message(request, messages.SUCCESS, 'Файл "%s" успешно загружен' % result)
                else:
                    messages.add_message(request, messages.ERROR, "Ошибка сохранения файла")
            else:
                messages.add_message(request, messages.ERROR, "Загрузите скан документа")

            return redirect(view_agreement, agreement_id=agreement.pk)

    return render(request, 'bs3/docs/add_application.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('docs.change_agreement')
def update_agreement(request, agreement_id):
    context = {'app': 'docs'}
    agreement = get_object_or_404(Agreement, pk=agreement_id)
    context['agreement'] = agreement

    form = AgreementForm(instance=agreement)
    context['form'] = form

    if request.method == 'POST':
        form = AgreementForm(data=request.POST, instance=agreement)
        if form.is_valid():
            form.save()

            Spy().log(object=agreement, form=form, action=Spy.CHANGE, user=request.user)
            messages.add_message(request, messages.SUCCESS, 'Информация обновлена')

            # Trying to handle file if exists
            if request.FILES.get('file'):
                result = agreement.handle_file(request.FILES['file'])
                if result:
                    messages.add_message(request, messages.SUCCESS, 'Файл "%s" успешно загружен' % result)
                else:
                    messages.add_message(request, messages.ERROR, "Ошибка сохранения файла")

            return redirect(view_agreement, agreement_id=agreement.pk)

    return render(request, 'bs3/docs/update_agreement.html', context)


@login_required(login_url=LOGIN_URL)
def view_agreement(request, agreement_id):
    return view_agreement_applications(request, agreement_id)


@login_required(login_url=LOGIN_URL)
def view_agreement_applications(request, agreement_id):
    context = {'app': 'docs', 'tab': 'applications'}
    agreement = get_object_or_404(Agreement, pk=agreement_id)
    context['agreement'] = agreement

    search_string = request.GET.get('search_string')
    context['search_string'] = search_string

    logs = Spy.objects.filter(object_name='agreement', object_id=agreement.pk).order_by('-time')
    context['logs'] = logs

    applications = agreement.applications.all()

    if search_string:
        applications = ApplicationSearch(queryset=applications).search(search_string)
    context['applications'] = applications

    return render(request, 'bs3/docs/view_agreement.html', context)


@login_required(login_url=LOGIN_URL)
def view_agreement_orders(request, agreement_id):
    context = {'app': 'docs', 'tab': 'orders'}
    agreement = get_object_or_404(Agreement, pk=agreement_id)
    context['agreement'] = agreement

    logs = Spy.objects.filter(object_name='agreement', object_id=agreement.pk).order_by('-time')
    context['logs'] = logs

    search_string = request.GET.get('search_string')
    context['search_string'] = search_string

    orders = agreement.applications.filter(application_type__in=[Application.APP_TYPE_ORDER,
                                                                 Application.APP_TYPE_APPLICATION])
    orders = orders.order_by('order_number')

    # generating dict with orders
    order_pairs = {}
    for order in orders:
        if order.order_number in order_pairs:
            order_pairs[order.order_number]['orders'].append(order)
        else:
            order_pairs[order.order_number] = {'orders': [order], 'akts': []}

    for akt in agreement.applications.filter(application_type=Application.APP_TYPE_AKT):
        if akt.order_number in order_pairs:
            order_pairs[akt.order_number]['akts'].append(akt)
        else:
            pair = {'orders': [], 'akts': [akt]}
            order_pairs[akt.order_number] = pair

    groups = [{'order_number': key, 'data': value}
              for key, value in order_pairs.items()]

    context['groups'] = groups
    return render(request, 'bs3/docs/view_agreement.html', context)


@login_required(login_url=LOGIN_URL)
def view_agreement_preview(request, agreement_id):
    context = {'app': 'docs', 'tab': 'preview'}
    agreement = get_object_or_404(Agreement, pk=agreement_id)
    context['agreement'] = agreement

    logs = Spy.objects.filter(object_name='agreement', object_id=agreement.pk).order_by('-time')
    context['logs'] = logs

    if request.POST:

        if not request.user.has_perm('docs.change_agreement'):
            messages.error(request, 'Недостаточно прав для изменения договоров')
            return redirect(reverse('agreement_preview', args=[agreement_id]))

        action = request.POST.get('action')
        if action == 'delete_file':
            agreement.filename = ''
            agreement.save()
            messages.success(request, 'Скан договора удален')

    return render(request, 'bs3/docs/view_agreement.html', context)


@login_required(login_url=LOGIN_URL)
def view_application(request, application_id):
    context = {'app': 'docs'}

    application = get_object_or_404(Application, pk=application_id)
    context['application'] = application

    tab = request.GET.get('tab', 'document')
    context['tab'] = tab

    if request.POST:
        action = request.POST.get('action')
        if action == 'delete_file':
            application.delete_file()
            messages.success(request, 'Файл приложения удален')
            return redirect(view_application, application_id=application.pk)

        if action == 'delete_application':
            application.delete()
            agreement_id = application.agreement.pk
            messages.success(request, 'Приложение удалено')

            return redirect(view_agreement, agreement_id=agreement_id)

    logs = Spy.objects.filter(object_name='application', object_id=application.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/docs/view_application.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('docs.change_application')
def update_application(request, application_id):
    context = {'app': 'docs', 'mode': 'edit'}

    application = get_object_or_404(Application, pk=application_id)
    context['application'] = application

    form = ApplicationForm(instance=application)
    context['form'] = form

    if request.method == 'POST':

        form = ApplicationForm(data=request.POST, instance=application)
        context['form'] = form
        if form.is_valid():

            form.save()
            Spy().log(object=form.instance, form=form, action=Spy.CHANGE, user=request.user)
            messages.add_message(request, messages.SUCCESS, 'Информация обновлена')

            # Trying to handle file if exists
            if request.FILES.get('file'):
                result = application.handle_file(request.FILES['file'])
                if result:
                    messages.add_message(request, messages.SUCCESS, 'Файл "%s" успешно загружен' % result)
                else:
                    messages.add_message(request, messages.ERROR, "Ошибка сохранения файла")

            return redirect(view_application, application_id=application.pk)
    return render(request, 'bs3/docs/update_application.html', context)


@login_required(login_url=LOGIN_URL)
def view_agreements(request):
    context = {'app': 'docs'}
    agreements = Agreement.objects.all().prefetch_related('client', 'applications', 'client__manager')

    search_string = request.GET.get('search')
    context['search_string'] = search_string
    if search_string:
        agreements = AgreementSearch(queryset=agreements).search(search_string)
        context['listing'] = agreements
    else:
        agreements = agreements.order_by('-pk')
        p = request.GET.get('page', 1)
        paginator = Paginator(agreements, request.user.pagination_count)
        page = paginator.page(p)
        context['p'] = page
        context['listing'] = page

    return render(request, 'bs3/docs/view_agreements.html', context)


@login_required(login_url=LOGIN_URL)
def delete_application(request):
    application = get_object_or_404(Application, pk=request.POST.get('id'))
    agreement = application.agreement
    try:
        application.delete()
    except:
        messages.add_message(request, messages.ERROR, "Ошибка при удалении документа.")

        return redirect(view_application, application_id=application.pk)
    Spy().log(object=application, action=Spy.DELETE, user=request.user)
    messages.add_message(request, messages.SUCCESS, "Документ удален")
    return redirect(view_agreement, agreement_id=agreement.pk)


@login_required(login_url=LOGIN_URL)
def search_agreement(request):
    search_string = request.GET.get('search', None)
    agreements = AgreementSearch().search(search_string)

    context = {
        "agreements": agreements,
        "search_string": search_string,
        "tab": "search",
    }

    return render(request, 'bs3/docs/view_agreements.html', context)
