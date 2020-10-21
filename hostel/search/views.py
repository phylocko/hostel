from hostel.common.views import service_view
from django.shortcuts import render, redirect
from .models import SearchAll
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from hostel.settings import LOGIN_URL
from hostel.clients.views import client_view


@login_required(login_url=LOGIN_URL)
def view_search_results(request):
    search_string = request.GET.get("search", None)
    search_results = SearchAll().search(search_string)

    if search_string == 'вменяемый менеджер':
        messages.error(request, 'Oxymoron search error')

    if search_results['count'] == 1:

        if len(search_results['search_results']['services']) == 1:
            return redirect(service_view, service_id=search_results['search_results']['services'][0].pk)

        if len(search_results['search_results']['clients']) == 1:
            return redirect(client_view, client_id=search_results['search_results']['clients'][0].pk)

    return render(request, 'bs3/search_results.html', {'mixed_results': search_results['search_results'],
                                                       'search_string': search_string,
                                                       'count': search_results['count']})
