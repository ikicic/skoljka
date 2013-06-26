from django import forms

from pm.models import MessageContent
from usergroup.fields import GroupEntryField


class NewMessageForm(forms.ModelForm):
    list = GroupEntryField()

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user') # user must be given!
        super(NewMessageForm, self).__init__(*args, **kwargs)
        self.fields['list'].user = user

    class Meta:
        model = MessageContent
        fields = ['subject']
