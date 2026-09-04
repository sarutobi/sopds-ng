"""Декораторы для SOPDS."""

import base64
from functools import wraps

from constance import config
from django.contrib import auth
from django.http import HttpRequest, HttpResponse


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

        # Определяем request: первый аргумент, если это HttpRequest, иначе второй (для методов класса)
        request = (
            args[0]
            if args and isinstance(args[0], HttpRequest)
            else args[1]
            if len(args) > 1
            else None
        )
        if request is None:
            return _unauthed()

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

        try:
            auth_data = base64.b64decode(auth_data.strip()).decode("utf-8")
            username, password = auth_data.split(":", 1)
        except (base64.binascii.Error, UnicodeDecodeError, ValueError):
            return _unauthed()

        user = auth.authenticate(username=username, password=password)
        if user and user.is_active:
            request.user = user
            auth.login(request, user)
            return view_function(*args, **kwargs)

        return _unauthed()

    return wrap
