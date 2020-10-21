from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from hostel.settings import LOGIN_URL
from .forms import SpyFilterForm
from .models import Spy


@login_required(login_url=LOGIN_URL)
def spy_list(request):
    context = {}

    spy_objects = Spy.objects.all().order_by('-time')

    filter_form = SpyFilterForm(request.GET or None)
    context['filter_form'] = filter_form

    if filter_form.is_valid():
        context['filter_form'] = filter_form

        client = filter_form.cleaned_data['client']
        if client:
            spy_objects = spy_objects.filter(client=client)

        action = filter_form.cleaned_data['action']
        if action:
            spy_objects = spy_objects.filter(action=action)

        user = filter_form.cleaned_data['user']
        if user:
            spy_objects = spy_objects.filter(user=user)

        time_from = filter_form.cleaned_data['time_from']
        if time_from:
            spy_objects = spy_objects.filter(time__gte=time_from)

        time_to = filter_form.cleaned_data['time_to']
        if time_to:
            spy_objects = spy_objects.filter(time__lte=time_to)

        object_name = filter_form.cleaned_data['object_name']
        if object_name:
            spy_objects = spy_objects.filter(object_name__icontains=object_name)

        context['listing'] = spy_objects

    else:
        p = request.GET.get('page', 1)
        paginator = Paginator(spy_objects, request.user.pagination_count)
        page = paginator.page(p)
        context['p'] = page
        context['listing'] = page

    return render(request, 'bs3/spy/spy_items.html', context)
