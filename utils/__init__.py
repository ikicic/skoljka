import re

# DEPRECATED: not used anymore. Kept because it is relatively complicated.
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

def interpolate_colors(r1, g1, b1, r2, g2, b2, percent):
    return (r1 + (r2 - r1) * percent,
            g1 + (g2 - g1) * percent,
            b1 + (b2 - b1) * percent)

def interpolate_three_colors(r1, g1, b1, r2, g2, b2, percent2, r3, g3, b3, percent3):
    """
        Triangle color interpolation.
        percent2 and percent3 represent barycentric coordinates, i.e.
            0 <= percent2, percent3 <= 1
            0 <= percent2 + percent3 <= 1
    """
    return (r1 + (r2 - r1) * percent2 + (r3 - r1) * percent3,
            g1 + (g2 - g1) * percent2 + (g3 - g1) * percent3,
            b1 + (b2 - b1) * percent2 + (b3 - b1) * percent3)
