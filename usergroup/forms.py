from django import forms
from django.contrib.auth.models import Group

from usergroup.fields import UserEntryField
from usergroup.models import UserGroup

class UserEntryForm(forms.Form):
    list = UserEntryField()

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']
