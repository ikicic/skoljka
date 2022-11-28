from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404

from skoljka.utils.decorators import ajax, require

from skoljka.mathcontent.models import MathContent, MAX_LENGTH
from skoljka.mathcontent.utils import convert_to_html_safe
from skoljka.mathcontent.templatetags.mathcontent_tags import mathcontent_render

@ajax(get='text')
def preview(request):
    text = request.GET['text']

    if len(text) > MAX_LENGTH:
        return HttpResponseBadRequest("Message too long.")

    return convert_to_html_safe(text)
