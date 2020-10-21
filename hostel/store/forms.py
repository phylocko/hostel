from django import forms
from .models import Entry


class EntryForm(forms.ModelForm):
    attrs = {'class': 'form-control'}
    type = forms.ChoiceField(required=True, choices=Entry.TYPE_CHOICES, widget=forms.Select(attrs=attrs))
    vendor = forms.ChoiceField(required=True, choices=Entry.VENDOR_CHOICES, widget=forms.Select(attrs=attrs))
    unit_height = forms.IntegerField(required=False, initial=0, widget=forms.NumberInput(attrs=attrs))
    model = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    serial = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=attrs))

    class Meta:
        model = Entry
        fields = ['type', 'model', 'vendor', 'comment', 'serial', 'unit_height']
