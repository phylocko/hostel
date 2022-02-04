from django import forms
from django.contrib.auth.models import Group, Permission, User

from hostel.clients.models import Client
from hostel.devices.models import Device
from hostel.service.variables import lease_types
from datetime import datetime
from .models import (Service, SubService, Autonomoussystem, User,
                     Datacenter, Lease, City, BurstSet, LeaseGroup,
                     Ourservice, Phone, Rack, Photo)

ATTRS = {'class': 'form-control'}


class ClientFilterForm(forms.Form):
    select_row_height = 18

    # Services
    service_choices = [('', '')]
    height = len(service_choices) * select_row_height
    services = forms.MultipleChoiceField(choices=service_choices,
                                         widget=forms.SelectMultiple(attrs={'class': 'form-control',
                                                                            'style': 'height: %spx' % height}))

    # Cities
    cities_choices = [('', '')]
    height = len(cities_choices) * select_row_height
    cities = forms.MultipleChoiceField(choices=cities_choices,
                                       widget=forms.SelectMultiple(attrs={'class': 'form-control',
                                                                          'style': 'height: %spx' % height}))


class BundleVlanForm(forms.Form):
    device = forms.ModelChoiceField(required=True,
                                    queryset=Device.objects.all().order_by('netname'),
                                    widget=forms.Select(attrs={'class': 'form-control'}))
    bundle = forms.IntegerField(required=True,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))


class ProvisionPeeringForm(forms.Form):
    device = forms.ModelChoiceField(required=True,
                                    queryset=Device.objects.all().order_by('netname'),
                                    widget=forms.Select(attrs={'class': 'form-control'}))
    bundle = forms.CharField(required=True,
                             widget=forms.TextInput(attrs={'class': 'form-control'}))


class BurstSetForm(forms.ModelForm):
    attrs = {'class': 'form-control'}
    name = forms.CharField(required=True, widget=forms.TextInput(attrs=attrs))
    client = forms.ModelChoiceField(required=True,
                                    queryset=Client.objects.filter(enabled=True, is_consumer=True),
                                    widget=forms.Select(attrs=attrs))
    limit = forms.IntegerField(required=False, widget=forms.NumberInput(attrs=attrs))
    price = forms.FloatField(required=True, widget=forms.TextInput(attrs=attrs))
    subscription_fee = forms.IntegerField(required=True, widget=forms.TextInput(attrs=attrs))
    with_tax = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    direction = forms.ChoiceField(required=True, choices=BurstSet.DIRECTIONS, widget=forms.Select(attrs=attrs))

    class Meta:
        model = BurstSet
        fields = ['name', 'client', 'limit', 'price', 'with_tax', 'direction', 'subscription_fee']


class DateRangeForm(forms.Form):
    attrs = {'class': 'form-control'}
    format = '%Y-%m-%d'

    start_date = forms.DateField(required=True, input_formats=[format], widget=forms.DateInput(attrs=attrs))
    end_date = forms.DateField(required=True, input_formats=[format], widget=forms.DateInput(attrs=attrs))

    def __init__(self, *args, **kwargs):
        super(DateRangeForm, self).__init__(*args, **kwargs)

        today = datetime.now()

        start_month = today.month - 1
        start_year = today.year
        if start_month < 1:
            start_month = 12
            start_year -= 1

        start_time = today.replace(day=1, month=start_month, year=start_year)
        end_time = today.replace(day=1)

        start_date = start_time.date()
        end_date = end_time.date()

        self.initial['start_date'] = start_date
        self.initial['end_date'] = end_date


class BurstCalculationForm(DateRangeForm):
    pass


class ServiceForm(forms.ModelForm):
    attrs = {'class': 'form-control'}
    servicetype = forms.ChoiceField(required=True, widget=forms.Select(attrs=attrs))
    status = forms.ChoiceField(required=True, choices=Service.STATUSES, widget=forms.Select(attrs=attrs))
    cities = forms.ModelMultipleChoiceField(
        required=True,
        queryset=City.objects.all().order_by('name'),
        widget=forms.SelectMultiple(attrs=attrs)
    )
    asn = forms.ModelChoiceField(
        required=False,
        queryset=Autonomoussystem.objects.none(),
        widget=forms.Select(attrs=attrs)
    )
    start_time = forms.DateTimeField(required=True, widget=forms.DateTimeInput(attrs=attrs))
    end_time = forms.DateTimeField(required=True, widget=forms.DateTimeInput(attrs=attrs))
    rt = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=attrs))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs=attrs))
    commited_bandwidth = forms.IntegerField(required=False, widget=forms.NumberInput(attrs=attrs))
    maximum_bandwidth = forms.IntegerField(required=False, widget=forms.NumberInput(attrs=attrs))

    class Meta:
        model = Service
        fields = ['comment', 'description', 'servicetype', 'rt',
                  'status', 'start_time', 'end_time', 'cities', 'asn',
                  'commited_bandwidth', 'maximum_bandwidth']

    def __init__(self, *args, **kwargs):
        try:
            service_name = kwargs.pop('service_name')
            client = kwargs.pop('client')
            asn = kwargs.pop('asn')
        except KeyError:
            service_name = None
            client = None
            asn = None
        super(ServiceForm, self).__init__(*args, **kwargs)

        if not self.instance.pk:
            if not service_name or not client:
                raise ValueError('service_name and client are required')
            self.instance.name = service_name
            self.instance.client = client

        params = self.instance.params()
        if 'service_types' in params:
            self.fields['servicetype'].choices = params['service_types']

        if 'status' in params:
            self.fields['status'].initial = params['status']

        if 'require_as' in params:
            if params['require_as']:
                self.fields['asn'].required = True
                if self.instance.pk:
                    self.fields['asn'].queryset = Autonomoussystem.objects.filter(
                        client=self.instance.client).order_by('asn')
                else:
                    self.fields['asn'].queryset = Autonomoussystem.objects.filter(
                        client=client).order_by('asn')

    def validate_asn(self):
        asn = self.cleaned_data['asn']
        params = self.instance.params()
        if not params['require_as'] and asn:
            raise forms.ValidationError('Данный сервис не требует автономной системы')
        if params['require_as'] and not asn:
            raise forms.ValidationError('Данный сервис требует автономную систему')


class SubServiceForm(forms.ModelForm):
    attrs = {'class': 'form-control', 'autocomplete': 'off'}
    area_attrs = {'class': 'form-control', 'rows': 4}

    sub_id = forms.CharField(required=True, widget=forms.TextInput(attrs=attrs))
    rt = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    status = forms.ChoiceField(
        required=True,
        choices=SubService.STATUSES,
        widget=forms.Select(attrs=attrs))
    cities = forms.ModelMultipleChoiceField(
        queryset=City.objects.all().order_by('name'),
        required=True,
        widget=forms.SelectMultiple(attrs=attrs)
    )
    description = forms.CharField(required=False, widget=forms.Textarea(attrs=area_attrs))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=area_attrs))

    class Meta:
        model = SubService
        fields = ['sub_id', 'comment', 'description', 'ticket', 'status', 'cities']

    def __init__(self, *args, **kwargs):
        service = None
        if 'service' in kwargs:
            service = kwargs.pop('service')

        super().__init__(*args, **kwargs)
        self.service = service
        if self.service:
            self.initial['ticket'] = self.service.ticket
            self.initial['description'] = self.service.description
            self.initial['cities'] = self.service.cities.all()

    def clean_sub_id(self):
        sub_id = self.cleaned_data['sub_id']
        if not self.instance.pk:
            # check if we have such subservice
            if SubService.objects.filter(service=self.service, sub_id=sub_id).count() > 0:
                raise forms.ValidationError('ID назначен другой подуслуге %s' % self.service)

        return sub_id

    def save(self, *args, **kwargs):
        if not self.instance.pk:
            self.instance.service = self.service
        return super().save(*args, **kwargs)


class ServicesFilterForm(forms.Form):
    attrs = {'class': 'form-control'}

    NAME_CHOICES = (
        ('', '')
    )
    name = forms.MultipleChoiceField(required=False, choices=NAME_CHOICES, widget=forms.SelectMultiple(attrs=attrs))
    service_type = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    text = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    status = forms.MultipleChoiceField(required=False, choices=Service.STATUSES,
                                       widget=forms.SelectMultiple(attrs=attrs))
    manager = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs=attrs)
    )
    DOC_CHOICES = (
        (None, 'Не важно'),
        ('yes', 'Да'),
        ('no', 'Нет'),
    )
    has_document = forms.ChoiceField(required=False, choices=DOC_CHOICES, widget=forms.Select(attrs=attrs))


class ServiceTestEndForm(forms.Form):
    attrs = {'class': 'form-control'}
    new_expiration_time = forms.DateTimeField(required=True, input_formats=['%Y-%m-%d %H:%M'],
                                              widget=forms.DateTimeInput(attrs=attrs, ))


class ASForm(forms.ModelForm):
    class Meta:
        model = Autonomoussystem

        fields = ['asn', 'asset', 'aslist', 'engname', 'asset6', 'ticket', 'comment']

        widgets = {
            'asn': forms.TextInput(attrs={'class': 'form-control'}),
            'asset': forms.TextInput(attrs={'class': 'form-control'}),
            'aslist': forms.TextInput(attrs={'class': 'form-control'}),
            'engname': forms.TextInput(attrs={'class': 'form-control'}),
            'asset6': forms.TextInput(attrs={'class': 'form-control'}),
            'ticket': forms.TextInput(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control'}),
        }


class LeaseForm(forms.ModelForm):
    default_attrs = {'class': 'form-control'}

    ticket = forms.IntegerField(
        required=False,
        widget=forms.TextInput(attrs=default_attrs))

    type = forms.ChoiceField(
        required=False,
        choices=lease_types,
        widget=forms.Select(attrs=default_attrs))

    organization = forms.ModelChoiceField(
        required=True,
        queryset=Client.objects.all().order_by('netname'),
        widget=forms.Select(attrs=default_attrs))

    group = forms.ModelChoiceField(
        required=False,
        queryset=LeaseGroup.objects.all().order_by('description'),
        widget=forms.Select(attrs=default_attrs))

    cities = forms.ModelMultipleChoiceField(
        required=True,
        queryset=City.objects.all().order_by('name'),
        widget=forms.SelectMultiple(attrs=default_attrs))

    identity = forms.CharField(required=True, widget=forms.TextInput(attrs=default_attrs))
    addresses = forms.CharField(required=False, widget=forms.Textarea(attrs=default_attrs))
    agreement = forms.CharField(required=False, widget=forms.TextInput(attrs=default_attrs))
    support_email = forms.CharField(required=False, widget=forms.TextInput(attrs=default_attrs))
    description = forms.CharField(required=False, widget=forms.TextInput(attrs=default_attrs))

    contacts = forms.CharField(required=False, widget=forms.Textarea(attrs=default_attrs))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=default_attrs))
    google_map_url = forms.CharField(required=False, widget=forms.TextInput(attrs=default_attrs))

    is_ours = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    is_bought = forms.BooleanField(required=False, widget=forms.CheckboxInput())

    class Meta:
        model = Lease
        fields = ['ticket',
                  'organization',
                  'cities',
                  'identity',
                  'agreement',
                  'support_email',
                  'description',
                  'type',
                  'contacts',
                  'comment',
                  'is_ours',
                  'is_bought',
                  'group',
                  'google_map_url',
                  'addresses',
                  ]

    def clean_addresses(self):
        lease_type = self.cleaned_data.get('type')
        addresses = self.cleaned_data.get('addresses')
        if lease_type in ['l2', 'qinq']:
            if not addresses:
                raise forms.ValidationError('Адреса включения обязательны для l2-каналов')
        return addresses


class LeaseFilterForm(forms.Form):
    default_attrs = {'class': 'form-control'}

    types = forms.MultipleChoiceField(required=False, choices=lease_types,
                                      widget=forms.SelectMultiple(attrs=default_attrs))

    cities = forms.ModelMultipleChoiceField(required=False,
                                            queryset=City.objects.all().order_by('name'),
                                            widget=forms.SelectMultiple(attrs=default_attrs))

    provider = forms.ModelMultipleChoiceField(required=False, widget=forms.SelectMultiple(attrs=default_attrs),
                                              queryset=Client.objects.filter(
                                                  lease__isnull=False,
                                                  enabled=True).order_by('netname').distinct())

    is_ours = forms.ChoiceField(required=False, choices=(('', 'Не важно'),
                                                         ('yes', 'Да'),
                                                         ('no', 'Нет')),
                                widget=forms.Select(attrs=default_attrs))
    is_bought = forms.ChoiceField(required=False, choices=(('', 'Не важно'),
                                                           ('yes', 'Да'),
                                                           ('no', 'Нет')),
                                  widget=forms.Select(attrs=default_attrs))
    search_string = forms.CharField(required=False, widget=forms.TextInput(attrs=default_attrs))


class LeaseGroupForm(forms.ModelForm):
    default_attrs = {'class': 'form-control'}

    rt = forms.IntegerField(required=False, widget=forms.TextInput(attrs=default_attrs))
    description = forms.CharField(required=True, widget=forms.TextInput(attrs=default_attrs))
    comment = forms.CharField(required=False, widget=forms.TextInput(attrs=default_attrs))

    class Meta:
        model = LeaseGroup
        fields = ['rt', 'description', 'comment']


class UserForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs=ATTRS)
    )
    permissions = forms.ModelChoiceField(
        queryset=Permission.objects.all().order_by('codename'),
        required=False,
        widget=forms.SelectMultiple(attrs=ATTRS)
    )
    photo = forms.ImageField(required=False, widget=forms.FileInput(attrs=ATTRS))

    groups = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Group.objects.all(),
        widget=forms.SelectMultiple(attrs=ATTRS)
    )

    class Meta:
        model = User

        fields = [
            'username',
            'last_name',
            'first_name',
            'mid_name',
            'email',
            'phone',
            'ext_phone',
            'birthday',
            'position',
            'is_active',
            'gender',
            'photo',

            'kind',
            'theme',
            'pagination_count',
        ]

        attrs = {'class': 'form-control'}

        widgets = {
            'username': forms.TextInput(attrs=attrs),
            'last_name': forms.TextInput(attrs=attrs),
            'first_name': forms.TextInput(attrs=attrs),
            'mid_name': forms.TextInput(attrs=attrs),
            'email': forms.EmailInput(attrs=attrs),
            'phone': forms.TextInput(attrs=attrs),
            'ext_phone': forms.TextInput(attrs=attrs),
            'birthday': forms.DateInput(attrs=attrs),
            'position': forms.TextInput(attrs=attrs),
            'kind': forms.Select(attrs=attrs),
            'theme': forms.Select(attrs=attrs),
            'pagination_count': forms.NumberInput(attrs=attrs),
            'gender': forms.Select(attrs=attrs),
            'is_active': forms.CheckboxInput(),
        }


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название'})
        }


class DatacenterForm(forms.ModelForm):
    class Meta:
        model = Datacenter

        fields = [
            'name',
            'city',
            'address',
            'contacts',
            'organization',
            'comment',
        ]

        widgets = {
            'name': forms.TextInput(attrs={"class": "form-control"}),
            'city': forms.Select(attrs={"class": "form-control"}),
            'address': forms.TextInput(attrs={"class": "form-control"}),
            'contacts': forms.Textarea(attrs={"class": "form-control"}),
            'organization': forms.Select(attrs={"class": "form-control"}),
            'comment': forms.Textarea(attrs={"class": "form-control"}),
        }

    def disable(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True


class CityForm(forms.ModelForm):
    class Meta:
        model = City

        fields = [
            'name',
            'map_url',
        ]

        widgets = {
            'name': forms.TextInput(attrs=ATTRS),
            'map_url': forms.URLInput(attrs=ATTRS),
        }


class PhoneForm(forms.ModelForm):
    attrs = {'class': 'form-control'}
    number = forms.CharField(required=True, widget=forms.TextInput(attrs=attrs))
    client = forms.ModelChoiceField(
        required=False,
        queryset=Client.objects.all().order_by('netname'),
        widget=forms.Select(attrs=attrs)
    )
    description = forms.CharField(required=True, widget=forms.TextInput(attrs=attrs))
    blacklisted = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    spam = forms.BooleanField(required=False, widget=forms.CheckboxInput())

    class Meta:
        model = Phone
        fields = ['number', 'client', 'description', 'blacklisted', 'spam']


class RackForm(forms.ModelForm):
    attrs = {'class': 'form-control'}
    location = forms.CharField(required=True, widget=forms.TextInput(attrs=attrs))
    height = forms.IntegerField(required=True, widget=forms.NumberInput(attrs=attrs))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=attrs))
    datacenter = forms.ModelChoiceField(
        required=False,
        queryset=Datacenter.objects.all().prefetch_related('city'),
        widget=forms.Select(attrs=attrs)
    )

    class Meta:
        model = Rack
        fields = ['location', 'height', 'datacenter', 'comment']

    def clean_height(self):
        height = self.cleaned_data['height']
        max_allowed_height = 0

        rack_devices = self.instance.device_set.filter(
            start_unit__isnull=False,
            store_entry__isnull=False,
            store_entry__unit_height__isnull=False
        )

        for device in rack_devices:
            max_device_unit = device.start_unit + device.store_entry.unit_height - 1
            max_allowed_height = max(max_allowed_height, max_device_unit)

        if max_allowed_height > height:
            raise forms.ValidationError('В стойке есть девайсы до юнита %s включительно' % max_allowed_height)

        return height


class UserProfileForm(forms.ModelForm):
    photo = forms.ImageField(required=False, widget=forms.FileInput(attrs=ATTRS))

    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'mid_name',
            'last_name',
            'email',
            'phone',
            'ext_phone',
            'birthday',
            'position',
            'kind',
            'gender',
            'theme',
            'pagination_count',
            'photo',
        ]
        widgets = {
            'username': forms.TextInput(attrs=ATTRS),
            'first_name': forms.TextInput(attrs=ATTRS),
            'mid_name': forms.TextInput(attrs=ATTRS),
            'last_name': forms.TextInput(attrs=ATTRS),
            'email': forms.TextInput(attrs=ATTRS),
            'phone': forms.TextInput(attrs=ATTRS),
            'ext_phone': forms.TextInput(attrs=ATTRS),
            'birthday': forms.DateInput(attrs=ATTRS),
            'position': forms.TextInput(attrs=ATTRS),
            'kind': forms.Select(attrs=ATTRS),
            'gender': forms.Select(attrs=ATTRS),
            'theme': forms.Select(attrs=ATTRS),
            'pagination_count': forms.NumberInput(attrs=ATTRS),
        }


class PhotoForm(forms.ModelForm):
    src = forms.ImageField(required=True, widget=forms.FileInput(attrs=ATTRS))
    comment = forms.CharField(required=False, widget=forms.TextInput(attrs=ATTRS))

    class Meta:
        model = Photo
        fields = ['src', 'comment']
