from django.conf import settings
from django.utils.html import mark_safe

def add_constants(request):
    return {'EXTRA_HEADER_TOP': mark_safe(settings.EXTRA_HEADER_TOP)}
