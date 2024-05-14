"""when functions are called we set up a context"""

import contextlib
import contextvars

HANDLER = contextvars.ContextVar('_gust_HANDLER')


@contextlib.contextmanager
def gust(handler):
    """With this we setup contextvars and reset for our app"""
    token = HANDLER.set(handler)
    try:
        yield
    finally:
        HANDLER.reset(token)


def get_handler():
    """get the current handler"""
    return HANDLER.get(None)


def get_app():
    """get the context app"""
    return get_handler().application


def get_current_user():
    """get the context app"""
    return get_handler().current_user
