from django import forms
from django.contrib.auth.models import Group

from usergroup.fields import UserEntryField, GroupEntryField, UserAndGroupEntryField, SeperatedUserAndGroupEntryField
from usergroup.models import UserGroup

class UserEntryForm(forms.Form):
    list = UserEntryField(label='Popis korisnika')

class GroupEntryForm(forms.Form):
    list = GroupEntryField(label='Popis grupa')

class UserAndGroupEntryForm(forms.Form):
    list = UserAndGroupEntryField(label='Popis korisnika i grupa')

class SeperatedUserAndGroupEntryForm(forms.Form):
    list = SeperatedUserAndGroupEntryField(label='Popis')

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']

class UserGroupForm(forms.ModelForm):
    class Meta:
        model = UserGroup
        fields = ['hidden']
