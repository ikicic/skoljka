
# TODO: refactor UserOptions!

def get_useroption(request, field_name):
    if request.user.is_authenticated():
        return getattr(request.user.get_profile(), field_name)
    else:
        return request.COOKIES.get(field_name, self.default_value)
