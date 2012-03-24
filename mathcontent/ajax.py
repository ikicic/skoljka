from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from mathcontent.models import MAX_LENGTH
from mathcontent.utils import convert_to_html

@login_required
def preview(request):
    # TODO: POST method!
    if not request.is_ajax():
        return HttpResponseBadRequest('Not ajax!')

    if 'text' not in request.GET:
        return HttpResponseBadRequest('Missing "text" field.')
        
    text = request.GET['text']
    
    if len(text) > MAX_LENGTH:
        return HttpResponseBadRequest('Too long message.')
        
    return HttpResponse(convert_to_html(text))
