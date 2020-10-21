from django import forms
from .models import Company
from hostel.clients.models import Client
from hostel.common.models import City


class CompanyForm(forms.ModelForm):
    default_attrs = {'class': 'form-control'}
    name = forms.CharField(widget=forms.TextInput(attrs=default_attrs))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=default_attrs))
    rt = forms.CharField(required=False, widget=forms.TextInput(attrs=default_attrs))
    contacts = forms.CharField(required=False, widget=forms.Textarea(attrs=default_attrs))
    client = forms.ModelChoiceField(required=False, widget=forms.Select(attrs=default_attrs),
                                    queryset=Client.objects.all().order_by('netname'))
    city = forms.ModelChoiceField(required=False, widget=forms.Select(attrs=default_attrs),
                                    queryset=City.objects.all().order_by('name'))
    edm = forms.BooleanField(required=False, widget=forms.CheckboxInput)

    class Meta:
        model = Company
        fields = ['name', 'client', 'city', 'rt', 'edm', 'comment', 'contacts']
