from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect, reverse

from hostel.settings import LOGIN_URL
from hostel.spy.models import Spy
from .models import Company, CompanySearch
from .forms import CompanyForm


@login_required(login_url=LOGIN_URL)
def company_list(request):
    context = {'app': 'companies'}

    tab = request.GET.get('tab', 'all')
    context['tab'] = tab

    companies = Company.objects.all().order_by('name')

    if request.GET:
        search_string = request.GET.get('search')
        context['search_string'] = search_string
        if search_string:
            companies = CompanySearch().search(search_string)
            context['listing'] = companies
            return render(request, 'bs3/companies/company_list.html', context)

    paginator = Paginator(companies, request.user.pagination_count)
    page = request.GET.get('page', 1)
    companies = paginator.get_page(page)

    context['listing'] = companies
    return render(request, 'bs3/companies/company_list.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('companies.add_company')
def company_create(request):
    context = {'app': 'cities', 'tab': 'add'}

    form = CompanyForm(request.POST or None)
    if form.is_valid():
        form.save()
        Spy().created(form.instance, form, request)
        messages.add_message(request, messages.SUCCESS, "Компания успешно создана")
        return redirect(company_view, company_id=form.instance.pk)

    context['form'] = form
    return render(request, 'bs3/companies/company_create.html', context)


@login_required(login_url=LOGIN_URL)
def company_view(request, company_id):
    context = {'app': 'companies', 'mode': 'view'}

    company = get_object_or_404(Company, pk=company_id)
    context['company'] = company

    logs = Spy.objects.filter(object_name='company', object_id=company.pk).order_by('-time')[0:100]
    context['logs'] = logs

    if request.POST:
        action = request.POST.get('action')
        if action == 'delete_company':
            company.delete()
            messages.add_message(request, messages.SUCCESS, 'Компания удалена')
            return redirect(company_list)

    return render(request, 'bs3/companies/company_view.html', context)


@login_required(login_url=LOGIN_URL)
@permission_required('companies.change_company')
def company_update(request, company_id):
    context = {'app': 'companies'}
    company = get_object_or_404(Company, pk=company_id)
    context['company'] = company

    form = CompanyForm(instance=company)
    context['form'] = form

    if request.method == "POST":
        form = CompanyForm(request.POST, instance=company)
        context['form'] = form
        if form.is_valid():
            old_object = Company.objects.get(pk=company.pk)
            Spy().changed(company, old_object, form, request)
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Данные компании обновлены')
            url = reverse(company_view, args=[company.pk])
            return redirect(url)

    return render(request, 'bs3/companies/company_update.html', context)
