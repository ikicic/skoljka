from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404

from tags.models import Tag, TaggedItem
from task.models import Task
from permissions.constants import VIEW

from skoljka.utils.decorators import ajax

# dokumentirati:
#   perm: delete_tag
#   (TODO: uzeti neko drugo ime, ovo je rezervirano vec)


@login_required
@ajax(post=['name', 'task'])
def delete(request):
    # TODO: DRY
    if not request.user.has_perm('delete_tag'):
        return '0'
        
    tag = get_object_or_404(Tag, name=request.POST['name'])
    task = get_object_or_404(Task, id=request.POST['task'])
    if not task.has_perm(request.user, VIEW):
        return HttpResponseForbidden('Not allowed to view or edit this task.')
    task_ct = ContentType.objects.get_for_model(Task)
        
    TaggedItem.objects.filter(tag=tag, object_id=task.id, content_type=task_ct).delete()
    
    return '1'

@login_required
@ajax(post=['name', 'task'])
def add(request):
    # TODO: DRY
    name = request.POST['name'].strip()
    if len(name) == 0:
        return HttpResponseBadRequest('Tag name has to be at least one character long.')
        
    task = get_object_or_404(Task, id=request.POST['task'])
    if not task.has_perm(request.user, VIEW):
        return HttpResponseForbidden('Not allowed to view or edit this task.')

    task_ct = ContentType.objects.get_for_model(Task)

    # https://code.djangoproject.com/ticket/13492
    # (mozda vezana rasprava: https://code.djangoproject.com/ticket/7789) 
    try:
        tag = Tag.objects.get(name__iexact=request.POST['name'])
    except Tag.DoesNotExist:
        tag = Tag.objects.create(name=request.POST['name'])
    taggeditem, created = TaggedItem.objects.get_or_create(object_id=task.id, content_type=task_ct, tag=tag)
    
    return '1' if created else '0'
