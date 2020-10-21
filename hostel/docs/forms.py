from django import forms
from .models import Agreement, Application


class AgreementForm(forms.ModelForm):
    agreement_date = forms.DateField(input_formats=['%d.%m.%Y'],
                                     widget=forms.DateInput(attrs={'class': 'form-control'}, format='%d.%m.%Y'))

    class Meta:
        model = Agreement
        fields = ['client',
                  'company',
                  'comment',
                  'agreement_number',
                  'agreement_date',
                  'partner_type',
                  'name',
                  'is_terminated',
                  ]

        widgets = {
            'agreement_number': forms.TextInput(attrs={'class': 'form-control'}),
            'client': forms.Select(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'partner_type': forms.Select(attrs={'class': 'form-control input-lg'}),
            'is_terminated': forms.CheckboxInput(),
        }


class ApplicationForm(forms.ModelForm):
    date = forms.DateField(required=False,
                           input_formats=['%d.%m.%Y'],
                           widget=forms.DateInput(attrs={'class': 'form-control'}, format='%d.%m.%Y'))

    def clean_order_number(self):
        application_type = self.cleaned_data.get('application_type', '')
        order_number = self.cleaned_data.get('order_number', '')
        if application_type in ([Application.APP_TYPE_AKT,
                                 Application.APP_TYPE_ORDER,
                                 Application.APP_TYPE_APPLICATION]):
            if not order_number:
                raise forms.ValidationError('Номер заказа обязателен для заказов и актов')

        return order_number

    def clean_name(self):
        application_type = self.cleaned_data.get('application_type', '')
        name = self.cleaned_data.get('name', '')
        if application_type not in [Application.APP_TYPE_AKT,
                                    Application.APP_TYPE_ORDER,
                                    Application.APP_TYPE_APPLICATION]:
            if not name:
                raise forms.ValidationError('Название обязательно для данного типа документа')

        return name

    def clean_date(self):
        application_type = self.cleaned_data.get('application_type', '')
        date = self.cleaned_data.get('date')
        if application_type == Application.APP_TYPE_AKT:
            if not date:
                raise forms.ValidationError('Дата обязательна для Актов')
        return date

    class Meta:
        model = Application
        fields = ['application_type',
                  'name',
                  'comment',
                  'order_number',
                  'date',
                  ]

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control'}),
            'application_type': forms.Select(attrs={'class': 'form-control input-lg'}),
            'order_number': forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'date': forms.DateTimeInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        }
