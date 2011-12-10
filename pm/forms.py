from django import forms

from pm.models import MessageContent
from usergroup.fields import UserAndGroupEntryField



class NewMessageForm(forms.ModelForm):
    list = UserAndGroupEntryField()
    class Meta:
        model = MessageContent
        fields = ['subject']
