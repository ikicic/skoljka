import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from django.middleware.csrf import get_token
from pythonjsx.runtime import JSXResult


def px_view(fn: Callable[..., JSXResult | HttpResponse]) -> Callable[..., HttpResponse]:
    """Decorator that wraps a PythonJSX view function.

    The view function should return a JSXResult. This decorator converts it
    to an HttpResponse with the rendered HTML and prepends <!DOCTYPE html>.
    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> HttpResponse:
        result = fn(*args, **kwargs)
        if isinstance(result, HttpResponseBase):
            return result
        return HttpResponse(result.to_html_document(), content_type="text/html")

    return wrapper


def csrf_header_json(request: HttpRequest) -> str:
    """Return a JSON string for hx-headers with the CSRF token."""
    return json.dumps({"X-CSRFToken": get_token(request)})
