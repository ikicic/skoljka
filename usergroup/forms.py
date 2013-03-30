from django import forms
from django.contrib.auth.models import Group

from usergroup.fields import UserEntryField, GroupEntryField, UserAndGroupEntryField, SeperatedUserAndGroupEntryField
from usergroup.models import UserGroup

class UserEntryForm(forms.Form):
    list = UserEntryField()

class GroupEntryForm(forms.Form):
    list = GroupEntryField()

class UserAndGroupEntryForm(forms.Form):
    list = UserAndGroupEntryField()

class SeperatedUserAndGroupEntryForm(forms.Form):
    list = SeperatedUserAndGroupEntryField()

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']

class UserGroupForm(forms.ModelForm):
    class Meta:
        model = UserGroup
        fields = ['hidden']
