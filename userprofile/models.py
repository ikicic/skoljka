from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    
    quote = models.CharField(max_length=200, blank=True)
