from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class ContractorRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True, label='Имя', widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=True, label='Фамилия', widget=forms.TextInput(attrs={'class': 'form-control'}))
    organization_name = forms.CharField(max_length=255, required=True, label='Наименование организации', widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'organization_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
