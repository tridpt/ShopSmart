"""
Request-scoped context for agent tools.

Tools like `track_price` need to know which user is acting, but we don't want
to expose `user_id` as a model-visible function argument. The agent sets the
current user id here before running the ReAct loop; tools read it.
"""
import contextvars

_current_user_id: contextvars.ContextVar = contextvars.ContextVar(
    "current_user_id", default=None
)


def set_current_user_id(user_id):
    """Set the active user id for the current context. Returns a reset token."""
    return _current_user_id.set(user_id)


def get_current_user_id():
    """Return the active user id, or None."""
    return _current_user_id.get()


def reset_current_user_id(token):
    """Restore the previous context value using the token from set_*()."""
    try:
        _current_user_id.reset(token)
    except (ValueError, LookupError):
        pass
