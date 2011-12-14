from django.db import models
from django.contrib.auth.models import User
from django.template.loader import add_to_builtins

class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    
    quote = models.CharField(max_length=200, blank=True)



# ovo navodno nije preporuceno, ali vjerujem da ce se 
# dovoljno cesto koristiti da DRY nadjaca
add_to_builtins('userprofile.templatetags.userprofile_tags')
