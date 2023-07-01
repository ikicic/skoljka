from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render_to_response

from skoljka.mathcontent.models import MAX_LENGTH, MathContent
from skoljka.mathcontent.templatetags.mathcontent_tags import mathcontent_render
from skoljka.mathcontent.utils import convert_to_html_safe
from skoljka.utils.decorators import ajax, require


@ajax(get='text')
def preview(request):
    text = request.GET['text']

    if len(text) > MAX_LENGTH:
        return HttpResponseBadRequest("Message too long.")

    return convert_to_html_safe(text)
