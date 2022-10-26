from django.conf import settings

# TODO: refactor UserOptions!

def get_useroption(request, field_name, default_value=None):
    if request.user.is_authenticated():
        return getattr(request.user.get_profile(), field_name)
    elif not settings.DISABLE_PREF_COOKIES:
        return request.COOKIES.get(field_name, default_value)
    else:
        return default_value
