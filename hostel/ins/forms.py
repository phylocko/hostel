from django import forms
from .models import Incident, Notification
import hostel.common.models as common_models
from hostel.devices.models import Device
from datetime import datetime, timedelta
from hostel.clients.models import Client


class ClientFilterForm(forms.Form):
    city = forms.ModelMultipleChoiceField(queryset=common_models.City.objects.all().order_by('name'),
                                          widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
                                          required=False)

    service_name = forms.ModelMultipleChoiceField(queryset=common_models.Ourservice.objects.all().order_by('name'),
                                                  widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
                                                  required=False)

    device = forms.ModelMultipleChoiceField(
        queryset=Device.objects.filter(type__in=['router', 'switch']).order_by('netname'),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False)

    device_negative = forms.ModelMultipleChoiceField(
        queryset=Device.objects.filter(type__in=['router', 'switch']).order_by('netname'),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False)

    keywords = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)

    client = forms.ModelMultipleChoiceField(
        queryset=Client.objects.filter(enabled=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False)

    from_leases = forms.BooleanField(widget=forms.CheckboxInput(), required=False)


class InsLeaseFilterForm(forms.Form):
    city = forms.ModelMultipleChoiceField(queryset=common_models.City.objects.all().order_by('name'),
                                          widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
                                          required=False)

    keywords = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)

    limit_by_services = forms.BooleanField(widget=forms.CheckboxInput(), required=False)


class NotificationForm(forms.ModelForm):
    attrs = {'class': 'form-control'}
    text = forms.CharField(required=True, widget=forms.Textarea(attrs=attrs))

    class Meta:
        model = Notification
        fields = ['text']

    def __init__(self, *args, **kwargs):
        incident = kwargs.pop('incident')
        super().__init__(*args, **kwargs)
        self.instance.incident = incident


class InsForm(forms.ModelForm):
    provider = forms.ModelChoiceField(queryset=Client.objects.filter(is_provider=True, enabled=True),
                                      widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Incident
        fields = [
            'time_start',
            'time_end',
            'outage_period',
            'name',
            'type',
            'ticket',
            'fiber',
            'provider',
            'provider_tt',
            'closed',
            'comment',
            'report_outage'
        ]

        widgets = {
            'time_start': forms.TextInput(attrs={'class': 'form-control'}),
            'time_end': forms.TextInput(attrs={'class': 'form-control'}),
            'outage_period': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'ticket': forms.TextInput(attrs={'class': 'form-control'}),
            'fiber': forms.Textarea(attrs={'class': 'form-control', 'id': 'fiber'}),
            'provider_tt': forms.TextInput(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control'}),
            'report_outage': forms.CheckboxInput(),
            'fmp_filter': forms.TextInput(attrs={'class': 'form-control'}),
            'closed': forms.CheckboxInput(),
        }


class InsFromRTForm(forms.Form):
    attrs = {'class': 'form-control'}
    name = forms.CharField(required=True,
                           widget=forms.TextInput(attrs=attrs))
    incident_type = forms.ChoiceField(required=True,
                                      choices=Incident.TYPES,
                                      widget=forms.Select(attrs=attrs))
    rt = forms.IntegerField(required=True,
                            widget=forms.NumberInput(attrs=attrs))


class OutageForm(forms.Form):
    attrs = {'class': 'form-control'}

    year = forms.ChoiceField(
        required=True,
        widget=forms.Select(
            attrs=attrs
        )
    )

    month = forms.CharField(required=True,
                            widget=forms.Select(
                                attrs=attrs,
                                choices=(
                                    (1, "Январь"),
                                    (2, "Февраль"),
                                    (3, "Март"),
                                    (4, "Апрель"),
                                    (5, "Май"),
                                    (6, "Июнь"),
                                    (7, "Июль"),
                                    (8, "Август"),
                                    (9, "Сентябрь"),
                                    (10, "Октябрь"),
                                    (11, "Ноябрь"),
                                    (12, "Декабрь"),

                                )
                            ))

    provider = forms.ModelChoiceField(
        required=False,
        queryset=Client.objects.filter(lease__isnull=False).distinct().order_by('netname'),
        widget=forms.Select(
            attrs=attrs
        )
    )

    keywords = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control',
                   'autocomplete': 'off'}
        )
    )

    client = forms.ModelChoiceField(required=False,
                                    queryset=Client.objects.filter(is_consumer=True).order_by('netname'),
                                    widget=forms.Select(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super(OutageForm, self).__init__(*args, **kwargs)

        year_choices = ((x, x) for x in range(2013, datetime.now().year + 2))
        self.fields['year'].choices = year_choices


class CalcForm(forms.Form):
    text = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 8})
    )

    def calculated(self):
        text = self.cleaned_data['text']
        summary_time, parsed_text = Incident.parse_intervals(text)
        return summary_time, parsed_text
