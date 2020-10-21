from django import forms
from .models import Client
import hostel.common.models as common_models
from hostel.common.models import User
from django.core.exceptions import ValidationError


class ClientFilterForm(forms.Form):
    default_attrs = {'class': 'form-control'}

    netname = forms.CharField(required=False,
                              widget=forms.TextInput(attrs=default_attrs))

    cities = forms.ModelMultipleChoiceField(queryset=common_models.City.objects.all().order_by('name'),
                                            widget=forms.SelectMultiple(attrs=default_attrs),
                                            required=False)

    manager = forms.ModelMultipleChoiceField(queryset=User.objects.all().order_by('username'),
                                             widget=forms.SelectMultiple(attrs=default_attrs),
                                             required=False)

    search_string = forms.CharField(required=False, widget=forms.TextInput(attrs=default_attrs))

    statuses = (('', 'Любой'), ('+', '+'), ('-', '-'))
    status = forms.ChoiceField(required=False, choices=statuses, widget=forms.Select(attrs=default_attrs))


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['netname',
                  'clientname',
                  'engname',
                  'city',
                  'address',
                  'contacts',
                  'support_contacts',
                  'comment',
                  'email',
                  'support_email',
                  'url',
                  'manager',
                  'ticket',
                  'is_consumer',
                  'is_provider',
                  'enabled']

        widgets = {
            'netname': forms.TextInput(attrs={'class': 'form-control'}),
            'clientname': forms.TextInput(attrs={'class': 'form-control'}),
            'engname': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'contacts': forms.Textarea(attrs={'class': 'form-control', 'rows': '5'}),
            'support_contacts': forms.Textarea(attrs={'class': 'form-control', 'rows': '5'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': '4'}),
            'email': forms.TextInput(attrs={'class': 'form-control'}),
            'support_email': forms.TextInput(attrs={'class': 'form-control'}),
            'url': forms.TextInput(attrs={'class': 'form-control'}),
            'manager': forms.Select(attrs={'class': 'form-control'}),
            'ticket': forms.TextInput(attrs={'class': 'form-control'}),
            'is_consumer': forms.CheckboxInput(),
            'is_provider': forms.CheckboxInput(),
            'enabled': forms.CheckboxInput(),
        }


class RequestServiceForm(forms.Form):
    default_attrs = {'class': 'form-control'}
    parent_rt = forms.IntegerField(required=False, widget=forms.TextInput(attrs=default_attrs))
    ports = forms.CharField(required=True, widget=forms.TextInput(attrs=default_attrs))
    contacts = forms.CharField(required=True, widget=forms.Textarea(attrs=default_attrs))
    comment = forms.CharField(required=False, widget=forms.TextInput(attrs=default_attrs))

    def clean_ports(self):
        ports = str(self.cleaned_data['ports'])
        if '-r' not in ports and not '-sw' in ports:
            raise ValidationError('Порт должен содержать имя свитча или роутера. '
                                  'Например: rostov-sw1', code='wrong_ports')
        return ports

    def clean_contacts(self):
        if '@' not in self.cleaned_data['contacts']:
            raise ValidationError('В контактах должен быть email.', code='wrong_contacts')
        return self.cleaned_data['contacts']


class RequestServiceL2Form(RequestServiceForm):
    default_attrs = {'class': 'form-control'}
    addresses = forms.CharField(required=True, widget=forms.Textarea(attrs=default_attrs))
    service_type = forms.ChoiceField(widget=forms.Select(attrs=default_attrs),
                                     choices=common_models.service_l2.TYPES)


class RequestServiceBGPForm(RequestServiceForm):
    default_attrs = {'class': 'form-control'}
    inet2_requested = forms.BooleanField(required=False)
    wix_requested = forms.BooleanField(required=False)
    bgpinet_requested = forms.BooleanField(required=False)

    inet2_type = forms.ChoiceField(widget=forms.Select(attrs=default_attrs),
                                   choices=common_models.service_inet2.TYPES)

    wix_type = forms.ChoiceField(widget=forms.Select(attrs=default_attrs),
                                 choices=common_models.service_wix.TYPES)

    bgpinet_type = forms.ChoiceField(widget=forms.Select(attrs=default_attrs),
                                     choices=common_models.service_bgpinet.TYPES)

    mode_choices = (
        ('', ''),
        ('test', 'Тест'),
        ('commerce', 'Коммерция'),
    )
    mode = forms.ChoiceField(required=True, choices=mode_choices, widget=forms.Select(attrs=default_attrs))

    test_period = forms.IntegerField(required=False, min_value=1, max_value=30, initial=14,
                                     widget=forms.NumberInput(attrs=default_attrs))

    def clean(self):
        bgpinet_requested = self.cleaned_data['bgpinet_requested']
        wix_requested = self.cleaned_data['wix_requested']
        inet2_requested = self.cleaned_data['inet2_requested']
        if not bgpinet_requested and not inet2_requested and not wix_requested:
            raise ValidationError('Не выбрана услуга', code='no_service')
