from django import forms
from .models import Entry, Part


class EntryForm(forms.ModelForm):
    attrs = {'class': 'form-control'}
    type = forms.ChoiceField(required=True, choices=Entry.TYPE_CHOICES, widget=forms.Select(attrs=attrs))
    vendor = forms.CharField(required=True, widget=forms.TextInput(attrs=attrs))
    unit_height = forms.IntegerField(required=False, initial=0, widget=forms.NumberInput(attrs=attrs))
    model = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    serial = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=attrs))

    class Meta:
        model = Entry
        fields = ['type', 'model', 'vendor', 'comment', 'serial', 'unit_height']


class PartForm(forms.ModelForm):
    attrs = {'class': 'form-control'}
    type = forms.CharField(required=True, widget=forms.TextInput(attrs=attrs))
    entry = forms.ModelChoiceField(required=False, queryset=Entry.objects.all(), widget=forms.Select(attrs=attrs))
    vendor = forms.CharField(required=True, widget=forms.TextInput(attrs=attrs))
    model = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    serial = forms.CharField(required=False, widget=forms.TextInput(attrs=attrs))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=attrs))

    class Meta:
        model = Part
        fields = ['type', 'model', 'entry', 'vendor', 'comment', 'serial']
