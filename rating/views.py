from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse
from rating.fields import RatingField


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
        if name != "quality_rating" and instance.author == request.user:
            raise Http404("Not allowed")
    
    manager = getattr(instance, name)
    manager.update(request.user, value)
    
    return HttpResponse(getattr(instance, '%s_avg' % name))