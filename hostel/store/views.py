from django.shortcuts import render, get_object_or_404, redirect
from .models import Entry, EntrySearch, Part, PartSearch
from .forms import EntryForm, PartForm
from django.contrib import messages
from hostel.spy.models import Spy
from django.contrib.auth.decorators import login_required, permission_required
from hostel.settings import LOGIN_URL
from django.shortcuts import reverse


@login_required(login_url=LOGIN_URL)
def entry_view(request, entry_id):
    context = {'app': 'store'}
    entry = get_object_or_404(Entry, pk=entry_id)
    context['entry'] = entry

    logs = Spy.objects.filter(object_name='entry', object_id=entry.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/store/entry_view.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('store.change_entry')
def entry_update(request, entry_id):
    context = {'app': 'store', 'mode': 'edit'}
    entry = get_object_or_404(Entry, pk=entry_id)
    if request.method == "POST":
        form = EntryForm(request.POST, instance=entry)
        if form.is_valid():
            old_object = Entry.objects.get(pk=entry.pk)
            Spy().changed(entry, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные оборудования обновлены')
            return redirect(entry_view, entry_id=form.instance.pk)
    else:
        form = EntryForm(instance=entry)
    context['form'] = form
    context['entry'] = entry
    return render(request, 'bs3/store/entry_update.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('store.add_entry')
def entry_create(request):
    context = {'app': 'store', 'tab': 'add_entry'}
    form = EntryForm(request.POST or None)
    if form.is_valid():
        form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, "Оборудование добавлено на склад")
        return redirect(entry_view, entry_id=form.instance.pk)
    context['form'] = form
    return render(request, 'bs3/store/entry_create.html', context)


@login_required(login_url=LOGIN_URL)
def entry_list(request):
    context = {'app': 'store', 'tab': 'entries'}
    entries = Entry.objects.all().order_by("type").order_by("vendor")
    entries = entries.prefetch_related('device')

    search_string = request.GET.get('search', None)
    if search_string:
        context['search_string'] = search_string
        entries = EntrySearch(queryset=entries).search(search_string)

    context['entries'] = entries
    return render(request, 'bs3/store/entry_list.html', context)


@login_required(login_url=LOGIN_URL)
def part_list(request):
    context = {'app': 'store', 'tab': 'parts'}
    parts = Part.objects.all().order_by("type").order_by("vendor")
    parts = parts.prefetch_related('entry', 'entry__device')

    search_string = request.GET.get('search', None)
    if search_string:
        context['search_string'] = search_string
        parts = PartSearch(queryset=parts).search(search_string)

    context['parts'] = parts
    return render(request, 'bs3/store/part_list.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('store.add_part')
def part_create(request):
    context = {'app': 'store', 'tab': 'add_part'}
    form = PartForm(request.POST or None)
    if form.is_valid():
        part = form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, "Запчасть добавлена на склад")
        return redirect(reverse('part', args=[part.pk]))
    context['form'] = form
    return render(request, 'bs3/store/part_create.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('store.change_part')
def part_update(request, part_id):
    context = {'app': 'store', 'mode': 'edit'}
    part = get_object_or_404(Part, pk=part_id)
    context['part'] = part

    form = PartForm(instance=part)
    context['form'] = form

    if request.method == "POST":
        form = PartForm(request.POST, instance=part)
        context['form'] = form
        if form.is_valid():
            old_object = Part.objects.get(pk=part.pk)
            Spy().changed(part, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные запчасти обновлены')
            return redirect(reverse('part', args=[part.pk]))

    return render(request, 'bs3/store/part_update.html', context)


@login_required(login_url=LOGIN_URL)
def part_view(request, part_id):
    context = {'app': 'store'}
    part = get_object_or_404(Part, pk=part_id)
    context['part'] = part

    logs = Spy.objects.filter(object_name='part', object_id=part.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/store/part_view.html', context)
