####
# TODO: refactor, rewrite the whole thing!
####

from django.contrib.contenttypes.models import ContentType

from activity.models import Action
from activity.constants import *
from skoljka.libs import xss

def _filter(**kwargs):
    action_object = kwargs.pop('action_object', None)
    if action_object:
        content_type = ContentType.objects.get_for_model(action_object)
        kwargs['action_object_content_type'] = content_type
        kwargs['action_object_id'] = action_object.pk

    target = kwargs.pop('target', None)
    if target:
        content_type = ContentType.objects.get_for_model(target)
        kwargs['target_content_type'] = content_type
        kwargs['target_id'] = target.pk

    return Action.objects.filter(**kwargs)

def remove(actor, type, **kwargs):
    """
    Removes SINGLE action. Throws except in the case multiple activities match
    given data.
    """
    try:
        filter = _filter(actor=actor, type=type, **kwargs)
        action = filter.get()
        action.delete()
    except Action.DoesNotExist:
        return

# SPEED: rucno napraviti upite
# shortcut
def add(actor, type_desc, fake_action_object=False, **kwargs):
    """
    Set fake_action_object to True if the action_object is used in a hacky way
    with a fake action_object_content_type_id and action_object_id.
    """
    type, subtype = type_desc
    action = Action(actor=actor, type=type, subtype=subtype, **kwargs)

    # can this be DRY-ed somehow?
    # ----- global -----
    if not fake_action_object and action.action_object:
        if hasattr(action.action_object, "name"):
            action.action_object_cache = action.action_object.name
        elif hasattr(action.action_object, "username"):
            action.action_object_cache = action.action_object.username
        elif hasattr(action.action_object, "value"):    # rating
            action.action_object_cache = str(action.action_object.value)

    if action.target:
        if hasattr(action.target, "name"):
            action.target_cache = action.target.name
        elif hasattr(action.target, "username"):
            action.target_cache = action.target.username
        elif action.target._meta.app_label == 'solution' and action.target._meta.module_name == 'solution':
            data = [
                action.target.author_id,
                action.target.author.username,
                action.target.task_id,
                action.target.task.name,
                action.target.task.author_id,
            ]
            # 250 chars should be enough for this
            action.target_cache = POST_SEND_CACHE_SEPARATOR.join([xss.escape(unicode(x)) for x in data])

    # ----- type specific -----
    if type == POST_SEND:
        T = action.action_object.content.text
        action.action_object_cache = T[:78] + '...' if len(T) > 80 else T

    action.save()

def replace_or_add(actor, type_desc, **kwargs):
    """
    Replace old activity with same actor, type and other parameters.
    Note that the new activity may have different subtype than the existing one.

    If there is no matching activity, new one will be created.

    In the case there are multiple activities matching the given conditions,
    exception will be thrown.

    Implementation:
        Basically just calls 'remove' and 'add'.

    Example:
        To Do activity is replaced with As Solved.
    """

    remove(actor, type_desc[0], **kwargs)
    add(actor, type_desc, **kwargs)
