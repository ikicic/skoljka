from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count

from skoljka.tags.models import Tag
from skoljka.task.models import Task
from skoljka.utils.decorators import response


@login_required
@response('tags_list.html')
def list(request):
    can_edit = request.user.is_staff

    alert_class = message = ''
    updated = []
    invalid = []

    if can_edit and request.method == 'POST':
        # input name is given in format `w{{ id }}`
        for k, v in request.POST.iteritems():
            if not v or not v.strip():
                continue

            # not a tag weight, skip
            if k[0] != 'w':
                continue

            # we expect that if a key starts with a `w`, that it is a tag weight
            try:
                id = int(k[1:])
            except ValueError:
                return (response.BAD_REQUEST, 'Invalid input id %s' % k)

            try:
                weight = float(v)
            except ValueError:
                invalid.append(id)
                continue

            Tag.objects.filter(id=id).update(weight=weight)
            updated.append(id)

        if invalid:
            alert_class = 'alert-error'
            message = 'Neke vrijednosti su nevaljanje (%d).' % len(invalid)
        else:
            alert_class = 'alert-success'
            message = 'Promjene spremljene.'

    task_content_type = ContentType.objects.get_for_model(Task)
    tags = Tag.objects.filter(
        tags_taggeditem_items__content_type=task_content_type
    ).annotate(taggeditem_count=Count('tags_taggeditem_items'))

    return {
        'tags': tags,
        'can_edit': can_edit,
        'alert_class': alert_class,
        'invalid': invalid,
        'message': message,
        'updated': updated,
    }
