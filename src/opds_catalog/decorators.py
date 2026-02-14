from functools import wraps

import base64
from django.http import HttpResponse
from django.contrib import auth
from constance import config


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

        user = auth.authenticate(username=username, password=password)
        if user and user.is_active:
            request.user = user
            auth.login(request, user)
            return view_function(*args, **kwargs)

        return _unauthed()

    return wrap
