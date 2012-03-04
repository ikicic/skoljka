from activity.models import Action
from activity.constants import *

def send(actor, type, **kwargs):
    class dummy(object):
        id = None
    
    target_id = kwargs.pop('target_id', None) or kwargs.pop('target', dummy).id
    action_object_id = kwargs.pop('action_object_id', None) or kwargs.pop('action_object', dummy).id
    if target_id: kwargs['target_id'] = target_id
    if action_object_id: kwargs['action_object_id'] = action_object_id
    
    action = Action(actor=actor, type=type, **kwargs)
    action.save()