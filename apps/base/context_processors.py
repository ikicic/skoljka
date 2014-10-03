from django.conf import settings

def add_constants(request):
    return {'EXTRA_HEADER_TOP': settings.EXTRA_HEADER_TOP}
