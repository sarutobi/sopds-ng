"""Декораторы для SOPDS."""

import base64
from functools import wraps

from constance import config
from django.contrib import auth
from django.http import HttpResponse

from sopds_web_backend.services import auth_services


def sopds_auth_validate(view_function):
    """Декоратор для проверки и аутентификации пользователей."""

    @wraps(view_function)
    def wrap(*args, **kwargs):
        def _unauthed():
            response = HttpResponse(
                """<html><title>Auth required</title><body>
                                    <h1>Authorization Required</h1></body></html>""",
                content_type="text/html",
            )
            response["WWW-Authenticate"] = 'Basic realm="OPDS"'
            response.status_code = 401
            return response

        if (
            args
            and hasattr(args[0], "__class__")
            and hasattr(args[0], view_function.__name__)
        ):
            request = args[1]
        else:
            request = args[0]

        header = "HTTP_AUTHORIZATION"
        if not config.SOPDS_AUTH or request.user.is_authenticated:
            return view_function(*args, **kwargs)

        try:
            authentication = request.META[header]
        except KeyError:
            return _unauthed()
        try:
            (auth_meth, auth_data) = authentication.split(" ", 1)
        except ValueError:
            return _unauthed()

        if "basic" != auth_meth.lower():
            return _unauthed()
        auth_data = base64.b64decode(auth_data.strip()).decode("utf-8")
        username, password = auth_data.split(":", 1)

        # Rate limiting
        ip = request.META.get("REMOTE_ADDR", "unknown")
        if auth_services.is_rate_limited(ip):
            return HttpResponse(
                "Too many login attempts. Please try again later.",
                status=429,
                content_type="text/plain",
            )

        user = auth.authenticate(username=username, password=password)
        if user and user.is_active:
            auth_services.reset_attempts(ip)
            request.user = user
            auth.login(request, user)
            return view_function(*args, **kwargs)
        else:
            auth_services.record_failed_attempt(ip)
            return _unauthed()

    return wrap
