import re

# name?
def get_referrer_path(request):
    """
        Get the path part of the referrer URI. If the URL is not related to
        SERVER_NAME, returns None.

        Example:
        http://www.skoljka.org:1234/abc/def/ghi/
            --> /abc/def/ghi/

        http://www.something.com/a/b/c/
            --> None
    """
    referrer = request.META.get('HTTP_REFERER')
    if not referrer:
        return None

    # Remove http:// or https:// part
    referrer = re.sub('^https?://', '', referrer)

    # Check if the referrer is this domain itself
    server_name = request.META.get('SERVER_NAME')
    if not re.match('^%s(:\d+)?/' % re.escape(server_name), referrer):
        return None     # not this server

    # Return path
    return referrer[referrer.find('/'):]
