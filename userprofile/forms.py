from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from userprofile.models import UserProfile


class UserCreationExtendedForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'first_name', 'last_name']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['quote']
    