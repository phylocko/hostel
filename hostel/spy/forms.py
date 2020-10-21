from django import forms
from .models import Spy
from hostel.clients.models import Client
from hostel.common.models import User
from datetime import datetime, timedelta


class SpyFilterForm(forms.Form):
    attrs = {'class': 'form-control'}

    user = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.all().order_by('username'),
        widget=forms.Select(attrs=attrs)
    )
    ACTION_CHOICES = [('', '')] + list(Spy.ACTION_CHOICES)
    action = forms.ChoiceField(
        required=False,
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs=attrs)
    )
    object_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs=attrs)
    )
    client = forms.ModelChoiceField(
        required=False,
        queryset=Client.objects.all().order_by('netname'),
        widget=forms.Select(attrs=attrs)
    )
    time_from = forms.DateTimeField(
        required=False,
        initial=datetime.now() - timedelta(hours=6),
        widget=forms.DateTimeInput(attrs=attrs)
    )
    time_to = forms.DateTimeField(
        required=False,
        initial=datetime.now(),
        widget=forms.DateTimeInput(attrs=attrs)
    )
