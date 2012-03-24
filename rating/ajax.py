from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from rating.fields import RatingField

from tags.models import Tag, TaggedItem
from task.models import Task
from permissions.constants import VIEW


@login_required
def tag_vote(request):
    if not request.is_ajax() or request.method != 'POST':
        return HttpResponseBadRequest()
    if any((x not in request.POST for x in ['value', 'tag', 'task'])):
        return HttpResponseBadRequest()
        
    tag = get_object_or_404(Tag, name=request.POST['tag'])
    
    task_ct = ContentType.objects.get_for_model(Task)
    task = Task.objects.get(id=request.POST['task'])
    if not task.has_perm(request.user, VIEW):
        return HttpResponseForbidden('Not allowed to view or edit this task.')
        
    taggeditem = get_object_or_404(TaggedItem, tag=tag, object_id=request.POST['task'], content_type=task_ct)
        
    value = taggeditem.votes.update(request.user, request.POST['value'])
    return HttpResponse(value)

@login_required
def vote(request, object_id, content_type_id, name):
    if not request.is_ajax() or request.method != 'POST' or name not in request.POST:
        raise Http404
        
    value = request.POST[name]      # value == 0 for delete
    try:
        content_type = ContentType.objects.get_for_id(content_type_id)
        instance = content_type.get_object_for_this_type(id=object_id)
    except:
        raise Http404("Something's wrong")
        
        
    specific = ["solution", "task"]
    if content_type.app_label in specific and content_type.model in specific:
        if name == "quality_rating" and instance.author == request.user:
            raise Http404("Not allowed")
    
    manager = getattr(instance, name)
    value = manager.update(request.user, value)
    
    return HttpResponse(value)