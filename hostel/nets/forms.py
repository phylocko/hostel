from django import forms
from .models import Net
from hostel.devices.models import Device
import hostel.common.models as common_models

ATTRS = {'class': 'form-control'}


class NetForm(forms.ModelForm):
    device = forms.ModelChoiceField(
        queryset=Device.objects.filter(status='+').order_by('netname'),
        widget=forms.Select(attrs=ATTRS),
        required=False
    )

    status = forms.ChoiceField(
        choices=Net.STATUSES,
        widget=forms.Select(attrs=ATTRS)
    )

    city = forms.ModelChoiceField(
        queryset=common_models.City.objects.all().order_by('name'),
        widget=forms.Select(attrs=ATTRS),
        required=False
    )

    class Meta:
        model = Net
        fields = [
            'device',
            'description',
            'address',
            'netmask',
            'city',
            'comment',
            'status',
            'mac',
            'ptr',
            'management_vlan',
            'vlan',
            'ticket'
        ]

        widgets = {
            'address': forms.TextInput(attrs={'class': 'form-control ipaddress', 'placeholder': '0.0.0.0'}),
            'netmask': forms.TextInput(attrs={'class': 'form-control netmask', 'placeholder': '32'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'rows': '5'}),
            'mac': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'FF:FF:FF:FF:FF:FF'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': '4'}),
            'ptr': forms.TextInput(attrs=ATTRS),
            'ticket': forms.TextInput(attrs=ATTRS),
            'management_vlan': forms.Select(attrs=ATTRS),
            'vlan': forms.Select(attrs=ATTRS),
        }
