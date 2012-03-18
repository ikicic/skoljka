from activity.models import Action
from activity.constants import *

# SPEED: rucno napraviti upite
# shortcut
def send(actor, type, **kwargs):
    action = Action(actor=actor, type=type, **kwargs)

    # can this be DRY-ed somehow?    
    # ----- global -----
    if action.action_object:
        if hasattr(action.action_object, "name"):
            action.action_object_cache = action.action_object.name
        elif hasattr(action.action_object, "username"):
            action.action_object_cache = action.action_object.username
        
    if action.target:
        if hasattr(action.target, "name"):
            action.target_cache = action.target.name
        elif hasattr(action.target, "username"):
            action.target_cache = action.target.username

    # ----- type specific -----
    if type == POST_SEND:
        T = action.action_object.content.text
        action.action_object_cache = T[:98] + '...' if len(T) > 100 else T
    
    action.save()
