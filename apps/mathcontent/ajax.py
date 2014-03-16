from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404

from mathcontent.models import MathContent, MAX_LENGTH
from mathcontent.utils import convert_to_html

from skoljka.libs.decorators import ajax, require

@ajax(get='text')
def preview(request):
    # TODO: POST method!
    text = request.GET['text']

    if len(text) > MAX_LENGTH:
        return HttpResponseBadRequest('Message too long.')

    return convert_to_html(text)

@ajax()
def render(request, id):
    mathcontent = get_object_or_404(MathContent, id=id)
    return mathcontent.render(quote=False)

@ajax()
def render_quote(request, id):
    mathcontent = get_object_or_404(MathContent, id=id)
    return mathcontent.render(quote=True)
