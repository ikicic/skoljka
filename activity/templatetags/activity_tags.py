from django import template
from django.utils.safestring import mark_safe

from activity.models import Action

register = template.Library()

@register.inclusion_tag('inc_recent_activity.html', takes_context=True)
def activity_list(context, exclude_user=None, target=None, action_object=None): 
    activity = Action.objects.all()
    if exclude_user and exclude_user.is_authenticated():
        activity = activity.exclude(actor=exclude_user)
    if target:
        activity = activity.filter(target=target)
    if action_object:
        activity = activity.filter(action_object=action_object)
        
    activity = activity.order_by('-id')[:40]
    
    return {'activity': activity}