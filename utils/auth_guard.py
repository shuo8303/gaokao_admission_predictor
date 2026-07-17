"""Route guards for pages that require login."""

from functools import wraps

from flask import redirect, request, session, url_for


def login_required(view_func):
    """Require a phone-login session before entering a view."""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get("user_phone"):
            return view_func(*args, **kwargs)

        return redirect(url_for("auth.login", next=request.full_path))

    return wrapped_view
