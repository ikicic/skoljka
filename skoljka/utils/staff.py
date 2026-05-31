import inspect
from functools import wraps
from typing import Any, Callable

from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext as _

from skoljka.utils.auth import login_redirect


def _check_staff(request: HttpRequest) -> HttpResponse | None:
    if not request.user.is_authenticated:
        return login_redirect(request)
    if not request.user.is_staff:
        return HttpResponse(_("Forbidden"), status=403)
    return None


def staff_required(fn: Callable[..., Any]) -> Callable[..., HttpResponse]:
    """Decorator that restricts a view to staff users. Supports async views."""
    if inspect.iscoroutinefunction(fn):
        @wraps(fn)
        async def async_wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            err = await sync_to_async(_check_staff)(request)
            if err:
                return err
            return await fn(request, *args, **kwargs)
        return async_wrapper
    else:
        @wraps(fn)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            if err := _check_staff(request):
                return err
            return fn(request, *args, **kwargs)
        return wrapper
