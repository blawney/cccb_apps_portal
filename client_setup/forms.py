from django import forms
from models import Service
from django.contrib.auth.models import User

class AddClientForm(forms.Form):
	first_name = forms.CharField(label='First name', max_length=50)
	last_name = forms.CharField(label='Last name', max_length=50)
	email_address = forms.EmailField(label='Email')

class ServiceForm(forms.ModelForm):
	service = forms.ChoiceField(label='Service')

	class Meta:
		model = Service
		fields = ('name',)
