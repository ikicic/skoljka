from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden, HttpResponseServerError

def do_vote(user, object_id, content_type_id, name, value):
    # value == 0 for delete

    try:
        content_type = ContentType.objects.get_for_id(content_type_id)
        instance = content_type.get_object_for_this_type(id=object_id)
    except:
        return HttpResponseServerError("Something's wrong")

    specific = ["solution"] # task also?
    if content_type.app_label in specific and content_type.model in specific:
        if name == "quality_rating" and instance.author == user:
            return HttpResponseForbidden("Not allowed")

    manager = getattr(instance, name)
    print 'old value', value
    value = manager.update(user, value)
    print 'new value', value
    return value

def rating_check_request(request):
    """
    Check if POST contains the voting data, applies the vote if so.
    """
    if request.method != 'POST':
        return
    args = ['rating-instance-id', 'rating-content-type-id', 'rating-field-name',
            'rating-vote']
    try:
        args = [request.POST[x] for x in args]
    except:
        return

    return do_vote(request.user, *args)
