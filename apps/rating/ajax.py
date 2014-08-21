from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.formats import number_format

from tags.models import Tag, TaggedItem
from task.models import Task
from permissions.constants import VIEW

from skoljka.libs.decorators import ajax

from rating.utils import do_vote

@ajax(post=['value', 'tag', 'task'])
def tag_vote(request):
    tag = get_object_or_404(Tag, name=request.POST['tag'])
    
    task_ct = ContentType.objects.get_for_model(Task)
    task = Task.objects.get(id=request.POST['task'])
    if not task.user_has_perm(request.user, VIEW):
        return HttpResponseForbidden('Not allowed to view or edit this task.')
        
    taggeditem = get_object_or_404(TaggedItem, tag=tag,
            object_id=request.POST['task'], content_type=task_ct)
        
    value = taggeditem.votes.update(request.user, request.POST['value'])
    return HttpResponse(value)

@ajax(method='POST')
def vote(request, object_id, content_type_id, name):
    if name not in request.POST:
        raise Http404

    value = request.POST[name]
    value = do_vote(request.user, object_id, content_type_id, name, value)

    if isinstance(value, (int, float)):
        return HttpResponse(number_format(value, 1))
    return value

