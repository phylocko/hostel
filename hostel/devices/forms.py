from django import forms
from .models import Device
from hostel.service.variables import DEVICE_TYPES
import hostel.common.models as common_models
from hostel.nets.models import Net
from django.core.exceptions import ValidationError
from hostel.store.models import Entry


class CreateDeviceForm(forms.ModelForm):
    default_attrs = {'class': 'form-control'}

    netname = forms.CharField(widget=forms.TextInput(attrs=default_attrs))
    type = forms.ChoiceField(widget=forms.Select(attrs=default_attrs), choices=DEVICE_TYPES, required=True)
    status = forms.ChoiceField(widget=forms.Select(attrs=default_attrs), choices=Device.STATUSES)
    community = forms.CharField(required=False, widget=forms.TextInput(attrs=default_attrs))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=default_attrs))
    ipaddress = forms.GenericIPAddressField(required=False, widget=forms.TextInput(attrs=default_attrs))
    is_managed = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    datacenter = forms.ModelChoiceField(required=False, widget=forms.Select(attrs=default_attrs),
                                        queryset=common_models.Datacenter.objects.all()
                                        .order_by('city__name', 'address'))

    class Meta:
        model = Device
        fields = ['netname', 'status', 'type', 'datacenter', 'comment', 'is_managed', 'community', 'ipaddress']

    def clean_ipaddress(self):
        ipaddress = self.cleaned_data['ipaddress']
        try:
            Net.objects.get(address=ipaddress, netmask=32)
        except Net.DoesNotExist:
            return ipaddress
        else:
            raise ValidationError('Address %s already exists' % ipaddress, code='invalid')

    def clean_community(self):
        community = self.cleaned_data['community']
        is_managed = self.cleaned_data['is_managed']
        if is_managed and not community:
            raise ValidationError('Community must be set for managed devices')
        return community


class DeviceForm(forms.ModelForm):
    attrs = {'class': 'form-control'}
    netname = forms.CharField(widget=forms.TextInput(attrs=attrs))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=attrs))
    status = forms.ChoiceField(widget=forms.Select(attrs=attrs), choices=Device.STATUSES)
    store_entry = forms.ModelChoiceField(
        required=False,
        queryset=Entry.objects.none(),
        widget=forms.Select(attrs=attrs)
    )
    community = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    version = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    type = forms.ChoiceField(
        widget=forms.Select(attrs=attrs),
        choices=DEVICE_TYPES, required=True)
    is_managed = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    datacenter = forms.ModelChoiceField(
        required=False,
        widget=forms.Select(attrs=attrs),
        queryset=common_models.Datacenter.objects.all().prefetch_related('city'))  # .order_by('city__name', 'address'
    management_net = forms.ModelChoiceField(
        required=False,
        widget=forms.Select(attrs=attrs),
        queryset=Net.objects.none())

    rack = forms.ModelChoiceField(
        required=False,
        queryset=common_models.Rack.objects.all().order_by('location'),
        widget=forms.Select(attrs=attrs)
    )
    rack_placement = forms.ChoiceField(
        required=True,
        choices=Device.RACK_PLACEMENT_CHOICES,
        widget=forms.Select(attrs=attrs)
    )
    whole_rack_depth = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    start_unit = forms.IntegerField(required=False, widget=forms.NumberInput(attrs=attrs))

    class Meta:
        model = Device
        fields = ['netname',
                  'comment',
                  'type',
                  'store_entry',
                  'status',
                  'management_net',
                  'community',
                  'datacenter',
                  'version',
                  'is_managed',
                  'whole_rack_depth',
                  'rack',
                  'rack_placement',
                  'start_unit',
                  ]

    def clean(self):
        if self.cleaned_data.get('netname') and 'netname' in self._errors:
            del self._errors['netname']
        return self.cleaned_data

    def clean_start_unit(self):
        start_unit = self.cleaned_data['start_unit']

        if not start_unit:
            return start_unit

        rack = self.cleaned_data['rack']
        side = self.cleaned_data['rack_placement']

        store_entry = self.cleaned_data['store_entry']
        if not store_entry:
            raise forms.ValidationError('Требуется указание складского юнита')

        if not rack:
            raise forms.ValidationError('Если указан юнит, необходимо указать и стойку')

        if not store_entry.unit_height:
            raise forms.ValidationError('Не задана высота %s' % store_entry)

        end_unit = start_unit + store_entry.unit_height - 1

        need_whole_rack_depth = self.cleaned_data['whole_rack_depth']

        if not rack.can_accommodate(
                start_unit=start_unit,
                end_unit=end_unit,
                side=side,
                device=self.instance,
                need_whole_depth=need_whole_rack_depth,
        ):
            raise forms.ValidationError('Невозможно разместить девайс в этом юните')

        return start_unit
