from django.db import models
from django.contrib.auth.models import User, Group
from django.template.loader import add_to_builtins

from tags.models import Tag

from folder.models import Folder
from rating.constants import DIFFICULTY_RATING_ATTRS
from task.models import Task
from solution.models import SOLUTION_CORRECT_SCORE


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    
    # data
    GENDER_CHOICES = (
        ('', 'Neizjašnjeno'),
        ('M', 'Momak'),
        ('F', 'Djevojka'),
    )
    gender = models.CharField(blank=True, max_length=1, choices=GENDER_CHOICES, default='', verbose_name='Spol')
    birthday = models.DateField(blank=True, null=True, verbose_name='Dan rođenja', help_text='U formatu YYYY-MM-DD')
    city = models.CharField(max_length=50, blank=True, verbose_name='Grad')
    country = models.CharField(max_length=50, blank=True, verbose_name='Država')
    quote = models.CharField(max_length=200, blank=True, verbose_name='Citat')
    website = models.CharField(max_length=100, blank=True, verbose_name='Web')
    
    # options
    show_hidden_tags = models.BooleanField(default=False, verbose_name='Prikazuj skrivene tagove')
    
    # utility
    unread_pms = models.IntegerField(default=0)    
    selected_folder = models.ForeignKey(Folder, blank=True, null=True)
    private_group = models.OneToOneField(Group)

    # deprecated or to fix
    solved_count = models.IntegerField(default=0)
    score = models.FloatField(default=0)
    diff_distribution = models.CharField(max_length=100)
    
    # da vraca [] umjesto None?
    def get_normalized_diff_distribution(self):
        distribution = self.diff_distribution.split(',')
        if len(distribution) == 1:
            return None
        
        distribution = [int(x) for x in distribution]
        total = sum(distribution)

        return None if total == 0 else [float(x) / total for x in distribution]
        
        
    def update_diff_distribution(self, commit=True):
        tasks = Task.objects.filter(hidden=False, solution__author=self, solution__correctness_avg__gte=SOLUTION_CORRECT_SCORE).values('id', 'difficulty_rating_avg').distinct().order_by()

        distribution = [0] * DIFFICULTY_RATING_ATTRS['range']
        for x in tasks:
            distribution[int(x['difficulty_rating_avg'] - 0.5)] += 1

        self.diff_distribution = ','.join(map(str, distribution))
        if commit:
            self.save()



# ovo navodno nije preporuceno, ali vjerujem da ce se 
# dovoljno cesto koristiti da DRY nadjaca
add_to_builtins('userprofile.templatetags.userprofile_tags')
