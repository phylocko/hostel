from django import forms
from .models import Vlan


class VlanForm(forms.ModelForm):
    class Meta:
        model = Vlan
        fields = ['ticket',
                  'vlannum',
                  'vname',
                  'status',
                  'comment',
                  'is_management',
                  'is_local',
                  ]

        widgets = {
            'ticket': forms.TextInput(attrs={'class': 'form-control'}),
            'vlannum': forms.TextInput(attrs={'class': 'form-control input-lg', 'rows': '5'}),
            'vname': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control'}),
            'is_management': forms.CheckboxInput(),
            'is_local': forms.CheckboxInput(),
        }
