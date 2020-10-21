from datetime import datetime
from threading import Thread
from time import sleep

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect, reverse

import hostel.common.models as common_models
from hostel.common.forms import BurstSetForm, DateRangeForm, BurstCalculationForm
from hostel.settings import LOGIN_URL
from hostel.spy.models import Spy
from . import forms
from .models import Burst
from .models import BurstSideException


@login_required(login_url=LOGIN_URL)
def burst_home(request):
    return redirect(burst_sets_view)


@login_required(login_url=LOGIN_URL)
@permission_required('common.add_burstset')
def burst_set_add(request):
    context = {}
    form = BurstSetForm(request.POST or None)
    if form.is_valid():
        burst_set = form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, "Burst-набор успешно создан")
        return redirect(reverse('burst_set', args=[burst_set.pk]))

    context['form'] = form
    return render(request, 'bs3/burst/add_burst_set.html', context)


@login_required(login_url=LOGIN_URL)
def burst_set_interfaces_view(request, burst_set_id):
    context = {'tab': 'interfaces'}

    burst_set = get_object_or_404(common_models.BurstSet, pk=burst_set_id)
    context['burst_set'] = burst_set

    if request.method == 'POST':

        action = request.POST.get('action')

        if action in ['add_positive', 'add_negative']:

            bundle_id = request.POST.get('bundle_id', None)
            if not bundle_id.isdecimal():
                messages.error(request, 'Неправильный ID бандла (должно быть число)')
                return redirect(reverse('burst_set', args=[burst_set_id]))

            try:
                bundle = common_models.Bundle.objects.get(pk=bundle_id)
            except common_models.Bundle.DoesNotExist:
                messages.error(request, 'Не существует бандла с ID %s' % bundle_id)
                return redirect(reverse('burst_set', args=[burst_set_id]))

            if action == 'add_positive':

                if bundle in burst_set.extract_bundles.all():
                    messages.add_message(
                        request, messages.WARNING,
                        'Нельзя добавить интерфейс в список подсчета и в список вычета одновременно!')
                else:
                    burst_set.bundles.add(common_models.Bundle.objects.get(pk=bundle_id))
                    messages.add_message(request, messages.SUCCESS, 'Интерфейс добавлен в список для подсчета')

            if action == 'add_negative':
                bundle = get_object_or_404(common_models.Bundle, pk=bundle_id)
                if bundle in burst_set.bundles.all():
                    messages.add_message(request, messages.WARNING,
                                         'Нельзя добавить интерфейс в список подсчета и в список вычета одновременно!')
                else:
                    burst_set.extract_bundles.add(common_models.Bundle.objects.get(pk=bundle_id))
                    messages.add_message(request, messages.SUCCESS, 'Интерфейс добавлен в список для вычета')
            return redirect(reverse('burst_set', args=[burst_set_id]))

        if action == 'remove_bundle':
            bundle_id = request.POST.get('bundle_id', None)
            bundle = get_object_or_404(common_models.Bundle, pk=bundle_id)
            burst_set.bundles.remove(bundle)
            burst_set.extract_bundles.remove(bundle)
            messages.add_message(request, messages.SUCCESS, 'Интерфейс %s удален из списка' % bundle)
            return redirect(reverse('burst_set', args=[burst_set_id]))

        if action == 'delete_burst_set':
            burst_set.delete()
            messages.add_message(request, messages.SUCCESS, 'Burst-set "%s" удален' % burst_set.name)
            return redirect(reverse('burst_sets'))

    return render(request, 'bs3/burst/burst_set.html', context)


@login_required(login_url=LOGIN_URL)
def burst_set_update_view(request, burst_set_id):
    context = {}

    end = datetime.now()
    end = end.replace(day=1)
    context['end_date'] = end.strftime('%Y-%m-%d')

    if end.month == 1:
        end = end.replace(month=12)
    else:
        end = end.replace(month=end.month - 1)
    context['start_date'] = end.strftime('%Y-%m-%d')

    burst_set = get_object_or_404(common_models.BurstSet, pk=burst_set_id)
    context['burst_set'] = burst_set
    form = BurstSetForm(instance=burst_set)
    context['form'] = form

    if request.method == 'POST':
        form = BurstSetForm(request.POST, instance=burst_set)
        context['form'] = form
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные обновлены')
            return redirect(burst_set_interfaces_view, burst_set_id=burst_set_id)
        else:
            messages.add_message(request, messages.ERROR, 'Форма содержит ошибки')

    return render(request, 'bs3/burst/burst_set_update.html', context)


def burst_set_calculate_view(request, burst_set_id):
    context = {'tab': 'calculate'}

    burst_set = get_object_or_404(common_models.BurstSet, pk=burst_set_id)
    context['burst_set'] = burst_set

    form = BurstCalculationForm()
    context['form'] = form

    if request.GET:
        form = BurstCalculationForm(request.GET)
        context['form'] = form

        if form.is_valid():

            date_format = '%Y-%m-%d'
            start_date = form.cleaned_data.get('start_date').strftime(date_format)
            end_date = form.cleaned_data.get('end_date').strftime(date_format)

            burst = Burst(burst_set)

            try:
                result = burst.get_burst(start_date, end_date)
            except BurstSideException as e:
                messages.add_message(request, messages.ERROR, 'Burst side error: %s' % e)
            else:
                context['calculation'] = result

            try:
                separated_calculation = burst.get_separated_burst(start_date, end_date)
            except BurstSideException as e:
                messages.add_message(request, messages.ERROR, 'Burst side error: %s' % e)
            else:
                context['separated_calculation'] = separated_calculation

    return render(request, 'bs3/burst/burst_set.html', context)


@login_required(login_url=LOGIN_URL)
def burst_sets_view(request):
    context = {'app': 'burst'}
    burst_sets = common_models.BurstSet.objects.all().order_by('name')
    filter_form = forms.BurstSetFilterForm()

    date_range_form = DateRangeForm()
    context['date_range_form'] = date_range_form

    if request.GET:
        filter_form = forms.BurstSetFilterForm(request.GET)
        if filter_form.is_valid():

            manager = filter_form.cleaned_data['manager']
            if manager:
                burst_sets = burst_sets.filter(client__manager__in=manager)

            search_string = filter_form.cleaned_data['keywords']
            if search_string:
                burst_sets = common_models.BurstSetSearch().search(search_string)

    context['filter_form'] = filter_form
    context['burst_sets'] = burst_sets

    return render(request, 'bs3/burst/burst_sets.html', context)


def calculate(request):
    context = {}

    burst_ids = request.GET.getlist('burst_sets')
    burst_sets = common_models.BurstSet.objects.filter(pk__in=burst_ids)
    bursts = [Burst(x) for x in burst_sets]
    report_storage = {x: None for x in bursts}

    start = request.GET.get('start_date', '')
    end = request.GET.get('end_date', '')

    context['start_date'] = start
    context['end_date'] = end

    def calculate_function(report_storage=None, burst=None, start=None, end=None):
        result = {'burst_set': burst.burst_set, 'calculation': None, 'error': None}
        try:
            calculation = burst.get_burst(start, end)
        except BurstSideException as e:
            result['error'] = e
        else:
            result['calculation'] = calculation
        report_storage[burst] = result

    threads = []
    i = 0
    portion_size = 100
    while i < len(burst_sets):
        for burst in bursts[i:i + portion_size]:
            thread = Thread(target=calculate_function, args=(report_storage, burst, start, end))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
        i += portion_size
        sleep(1)

    context['report'] = report_storage

    return render(request, 'bs3/burst/calculate.html', context)
