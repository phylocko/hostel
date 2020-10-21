from django.shortcuts import render, get_object_or_404, redirect
from .models import Entry, EntrySearch
from .forms import EntryForm
from django.contrib import messages
from hostel.spy.models import Spy
from django.contrib.auth.decorators import login_required, permission_required
from hostel.settings import LOGIN_URL


# == Entry ==
@login_required(login_url=LOGIN_URL)
def entry_view(request, entry_id):
    context = {'app': 'entry'}
    entry = get_object_or_404(Entry, pk=entry_id)
    context['entry'] = entry

    logs = Spy.objects.filter(object_name='entry', object_id=entry.pk).order_by('-time')
    context['logs'] = logs

    return render(request, 'bs3/store/entry_view.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('store.change_entry')
def entry_update(request, entry_id):
    context = {'app': 'entry', 'mode': 'edit'}
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
    context = {'app': 'entry', 'tab': 'add'}
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
    context = {'tab': 'all'}
    entries = Entry.objects.all().order_by("type").order_by("vendor")
    entries = entries.prefetch_related('device')

    search_string = request.GET.get('search', None)
    if search_string:
        context['search_string'] = search_string
        entries = EntrySearch(queryset=entries).search(search_string)

    context['entries'] = entries
    return render(request, 'bs3/store/entry_list.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('store.delete_entry')
def entry_delete(request):
    entry = get_object_or_404(Entry, pk=request.POST.get('id'))
    Spy().log(object=entry, form=None, user=request.user, action=Spy.DELETE)
    entry.delete()
    messages.add_message(request, messages.SUCCESS, 'Оборудование удалено со склада')
    return redirect(entry_list)