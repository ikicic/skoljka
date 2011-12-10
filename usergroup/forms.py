from django import forms
from django.contrib.auth.models import Group

from usergroup.fields import UserEntryField, UserAndGroupEntryField
from usergroup.models import UserGroup

class UserEntryForm(forms.Form):
    list = UserEntryField()

class UserAndGroupEntryForm(forms.Form):
    list = UserAndGroupEntryField()

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']
