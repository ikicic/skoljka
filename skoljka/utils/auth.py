from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from functools import wraps
from typing import Callable


def login_redirect(request: HttpRequest, next_url: str | None = None) -> HttpResponse:
    """Redirect to login with a URL-encoded local next target."""
    return redirect_to_login(next_url or request.get_full_path(), login_url=reverse("login"))


def login_required_response(request: HttpRequest) -> HttpResponse | None:
    if request.user.is_authenticated:
        return None
    return login_redirect(request)


def login_required_htmx_response(request: HttpRequest) -> HttpResponse | None:
    if request.user.is_authenticated:
        return None
    return HttpResponse(status=401)


def login_required_view(view_func: Callable) -> Callable:
    @wraps(view_func)
    def wrapped(request: HttpRequest, *args, **kwargs):
        if err := login_required_response(request):
            return err
        return view_func(request, *args, **kwargs)

    return wrapped


def login_required_htmx_view(view_func: Callable) -> Callable:
    @wraps(view_func)
    def wrapped(request: HttpRequest, *args, **kwargs):
        if err := login_required_htmx_response(request):
            return err
        return view_func(request, *args, **kwargs)

    return wrapped


def safe_next_redirect(request: HttpRequest, fallback: str = "/") -> HttpResponse:
    next_url = request.GET.get("next") or fallback
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = fallback
    return redirect(next_url)
