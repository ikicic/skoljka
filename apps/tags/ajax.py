from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponse, HttpResponseForbidden, \
        HttpResponseBadRequest
from django.db.models import Model
from django.shortcuts import get_object_or_404

from permissions.constants import EDIT

from tags.utils import add_tags, remove_tags

from skoljka.libs.decorators import ajax

# dokumentirati:
#   perm: delete_tag
#   (TODO: uzeti neko drugo ime, ovo je rezervirano vec)

_ALLOWED_CONTENT_TYPES = [('task', 'task')]

def _get_object(request):
    content_type_id = request.POST['content_type_id']
    content_type = get_object_or_404(ContentType, id=content_type_id)
    if (content_type.app_label, content_type.model) \
            not in _ALLOWED_CONTENT_TYPES:
        return HttpResponseBadRequest()
    object_id = request.POST['object_id']
    try:
        instance = content_type.get_object_for_this_type(id=object_id)
    except ObjectDoesNotExist:
        raise Http404
    if not instance.user_has_perm(request.user, EDIT):
        return HttpResponseForbidden('0')
    return instance

@ajax(post=['name', 'content_type_id', 'object_id'])
def delete(request):
    instance = _get_object(request)
    if not isinstance(instance, Model):
        return instance  # HttpResponse
    name = request.POST['name']
    remove_tags(instance, [name])  # Only one tag!
    return '1'


@ajax(post=['name', 'content_type_id', 'object_id'])
def add(request):
    instance = _get_object(request)
    if not isinstance(instance, Model):
        return instance  # HttpResponse
    name = request.POST['name']
    if len(name) == 0:
        return HttpResponseBadRequest(
                "Tag name has to be at least one character long.")
    if name.lower() in ['news', 'oldnews'] and not request.user.is_superuser:
        return '00'  # HttpResponseForbidden("Nedozvoljena oznaka.")
    change = add_tags(instance, [name])  # Only one tag!
    return '1' if change != 0 else '-1'
