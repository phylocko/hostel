from django import forms
from hostel.clients.models import Client
from hostel.common.models import service_l2, City
from hostel.vlans.models import Vlan


class ServiceForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.filter(enabled=True), required=True,
                                    widget=forms.Select(attrs={'class': 'form-control'}))
    vlan = forms.ModelChoiceField(queryset=Vlan.objects.filter(is_management=False, service__isnull=True),
                                  required=False,
                                  widget=forms.Select(attrs={'class': 'form-control'}))
    service_type = forms.ChoiceField(choices=service_l2.TYPES, required=True,
                                     widget=forms.Select(attrs={'class': 'form-control'}))
    rt = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    vlan_id = forms.IntegerField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    vlan_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    comment = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    cities = forms.ModelMultipleChoiceField(queryset=City.objects.all().order_by('name'),
                                    widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
                                    required=True)
