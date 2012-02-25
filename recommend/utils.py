from django.db.models import F, Sum
from django.contrib.contenttypes.models import ContentType

from taggit.models import TaggedItem

from rating.constants import DIFFICULTY_RATING_ATTRS
from recommend.models import UserTagScore, UserRecommendation
from recommend.constants import *
from solution.models import Solution, STATUS
from task.models import Task

from collections import defaultdict
from datetime import datetime
import math

def get_solution_weight(solution_time):
    return math.exp(INTEREST_TIME_FACTOR * (datetime.now() - solution_time).total_seconds())

def task_event(user, task, action):
    print task, action
    if action == 'view':
        recommend_task(user, task)
        content_type = ContentType.objects.get_for_model(task)


def user_task_score(user, task):
    content_type = ContentType.objects.get_for_model(task)

    tag_ids = TaggedItem.objects.filter(content_type=content_type, object_id=task.id).values_list('tag_id', flat=True)
    if len(tag_ids) == 0:
        return 0

    diff = task.difficulty_rating_avg
    
    tag_score = UserTagScore.objects.filter(user=user, tag__in=tag_ids)
    num = den = 0
    
    for x in tag_score:
        weight = 1 * x.get_interest()
        num += weight * x.get_score(diff)
        den += weight
    
    return 0 if den < 1e-5 else num / den

def refresh_user_information(user):
    content_type = ContentType.objects.get_for_model(Task)

    solution = Solution.objects.filter(author=user, status__gt=STATUS['blank'], task__difficulty_rating_avg__gt=0).select_related('task')
    tags = TaggedItem.objects.filter(content_type=content_type, object_id__in=solution.values_list('task__id', flat=True))
    
    solution_by_task = dict(((x.task.id, x) for x in solution))
        
    class TagInfo(object):
        def __init__(self):
            self.sum = 0
            self.square_sum = 0
            self.total_weight = 0
            
        def __str__(self):
            return '%f %f %f' % (self.sum, self.square_sum, self.total_weight)
        
    tags_info = defaultdict(TagInfo)
    
    for x in tags:
        t = tags_info[x.tag_id]
        s = solution_by_task[x.object_id]
        w = 1 * get_solution_weight(s.date_created)
        diff = s.task.difficulty_rating_avg
        
        t.sum += w * diff
        t.square_sum += w * diff * diff
        t.total_weight += w

    UserTagScore.objects.filter(user=user).delete()
    for k, v in tags_info.iteritems():
        tag = UserTagScore(user=user, tag_id=k)
        tag.interest = v.total_weight
        tag.mean = v.sum / v.total_weight
        tag.variance = (v.square_sum - 2 * tag.mean * v.sum + tag.mean * tag.mean * v.total_weight) / v.total_weight
        if tag.variance < 1e-3:
            tag.variance = 0.8
        tag.save()

def recommend_task(user, task):
    score = user_task_score(user, task)
    if score > 0:
        object, created = UserRecommendation.objects.get_or_create(user=user, task=task, defaults={'score': score})
        if not created:
            object.score = score
            object.save()
