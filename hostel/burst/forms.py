from django import forms
from hostel.common.models import User


class BurstSetFilterForm(forms.Form):
    attrs = {'class': 'form-control'}
    manager = forms.ModelMultipleChoiceField(
        queryset=User.objects.all().order_by('username'),
        widget=forms.SelectMultiple(attrs=attrs),
        required=False
    )

    keywords = forms.CharField(
        widget=forms.TextInput(attrs=attrs),
        required=False
    )
