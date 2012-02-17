from django.db import models
from django.contrib.auth.models import User

from mathcontent.models import MathContent
from post.generic import PostGenericRelation
from rating.fields import RatingField
from rating.constants import *
from task.models import Task

SOLUTION_RATING_ATTRS = {
    'range': 5,
    'titles': [u'Netočno', u'Točno uz manje nedostatke.', u'Točno.', u'Točno i domišljato.', u'Genijalno! Neviđeno!'],
}

# TODO: nekako drugacije ovo nazvati
SOLUTION_CORRECT_SCORE = 2

class Solution(models.Model):
    task = models.ForeignKey(Task)
    author = models.ForeignKey(User)
    content = models.OneToOneField(MathContent)
    date_created = models.DateTimeField(auto_now_add=True)
    posts = PostGenericRelation()
    
    correctness = RatingField(**SOLUTION_RATING_ATTRS)