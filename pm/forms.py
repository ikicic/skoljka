from django import forms

from pm.models import MessageContent
#from usergroup.fields import UserAndGroupEntryField
from usergroup.fields import GroupEntryField



class NewMessageForm(forms.ModelForm):
    #list = UserAndGroupEntryField()
    list = GroupEntryField()
    class Meta:
        model = MessageContent
        fields = ['subject']
