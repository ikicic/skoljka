from django import forms
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist

class UserEntryField(forms.CharField):
    widget = forms.Textarea()
    
#TODO: optimizirati
    def clean(self, value):
        list = [x.strip() for x in value.split(',')]
        not_found = []
        found = []
        for x in list:
            try:
                found.append(User.objects.get(username__iexact=x))
            except ObjectDoesNotExist:
                not_found.append(x)
    
        if not_found:
            raise forms.ValidationError(u'Nepostojeći korisnici: %s' % ' '.join(not_found))
            
        return found


class UserAndGroupEntryField(forms.CharField):
    widget = forms.Textarea()
    
#TODO: optimizirati
    def clean(self, value):
        list = [x.strip() for x in value.split(',')]
        not_found = []
        users = []
        groups = []
        for x in list:
            try:
                users.append(User.objects.get(username__iexact=x))
            except ObjectDoesNotExist:
                try:
                    groups.append(Group.objects.get(name__iexact=x))
                except ObjectDoesNotExist:
                    not_found.append(x)
                    
        if not_found:
            raise forms.ValidationError(u'Nepostojeći korisnici ili grupe: %s' % ' '.join(not_found))
        
        return (users, groups)
