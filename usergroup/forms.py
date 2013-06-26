from django import forms
from django.contrib.auth.models import Group

from usergroup.fields import UserEntryField, GroupEntryField
from usergroup.models import UserGroup

class UserEntryForm(forms.Form):
    list = UserEntryField(label='Popis korisnika')

class GroupEntryForm(forms.Form):
    list = GroupEntryField(label='Popis korisnika i grupa')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user') # user must be given!
        super(GroupEntryForm, self).__init__(*args, **kwargs)
        self.fields['list'].user = user

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']

class UserGroupForm(forms.ModelForm):
    class Meta:
        model = UserGroup
        fields = ['hidden']
