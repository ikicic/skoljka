from django.http import HttpResponseBadRequest

from skoljka.mathcontent.models import MAX_LENGTH
from skoljka.mathcontent.utils import convert_to_html_safe
from skoljka.utils.decorators import ajax


@ajax(get='text')
def preview(request):
    text = request.GET['text']

    if len(text) > MAX_LENGTH:
        return HttpResponseBadRequest("Message too long.")

    return convert_to_html_safe(text)
