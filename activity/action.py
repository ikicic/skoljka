from activity.models import Action
from activity.constants import *

# shortcut
def send(actor, type, **kwargs):
    action = Action(actor=actor, type=type, **kwargs)
    action.save()