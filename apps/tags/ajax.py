from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404

from tags.models import Tag, TaggedItem
from task.models import Task
from permissions.constants import VIEW, EDIT

from tags.signals import send_task_tags_changed_signal

from skoljka.libs.decorators import ajax

# dokumentirati:
#   perm: delete_tag
#   (TODO: uzeti neko drugo ime, ovo je rezervirano vec)


@ajax(post=['name', 'task'])
def delete(request):
    task = get_object_or_404(Task, id=request.POST['task'])
    if not task.user_has_perm(request.user, EDIT):
        return '0' # HttpResponseForbidden("Not allowed to edit this task.")
    task_ct = ContentType.objects.get_for_model(Task)

    tag_name = request.POST['name']
    tag = get_object_or_404(Tag, name=tag_name)

    old_tags = list(task.tags.values_list('name', flat=True))
    TaggedItem.objects.filter(
            tag=tag, object_id=task.id, content_type=task_ct).delete()
    new_tags = [x for x in old_tags if x != tag_name]

    send_task_tags_changed_signal(task, old_tags, new_tags)

    return '1'

@ajax(post=['name', 'task'])
def add(request):
    # TODO: DRY
    name = request.POST['name'].strip()
    if len(name) == 0:
        return HttpResponseBadRequest(
                "Tag name has to be at least one character long.")

    # 'news' is used to mark task as news
    if name.lower() in ['news', 'oldnews']:
        return '00' # HttpResponseForbidden("Nedozvoljena oznaka.")

    task = get_object_or_404(Task, id=request.POST['task'])
    if not task.user_has_perm(request.user, EDIT):
        return '0' # HttpResponseForbidden("Not allowed to edit this task.")

    task_ct = ContentType.objects.get_for_model(Task)

    # https://code.djangoproject.com/ticket/13492
    # (mozda vezana rasprava: https://code.djangoproject.com/ticket/7789)
    try:
        tag = Tag.objects.get(name__iexact=request.POST['name'])
    except Tag.DoesNotExist:
        tag = Tag.objects.create(name=request.POST['name'])

    old_tags = list(task.tags.values_list('name', flat=True))
    taggeditem, created = TaggedItem.objects.get_or_create(
            object_id=task.id, content_type=task_ct, tag=tag)
    if created:
        new_tags = task.tags.values_list('name', flat=True)
        send_task_tags_changed_signal(task, old_tags, new_tags)

    return '1' if created else '-1'
