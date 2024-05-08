"""when functions are called we set up a context"""

import contextlib
import contextvars

GUST = contextvars.ContextVar('_gust_GUST')
USER = contextvars.ContextVar('_gust_USER')
HANDLER = contextvars.ContextVar('_gust_HANDLER')


@contextlib.contextmanager
def gust(app, user, handler=None):
    """With this we setup contextvars and reset for our app"""
    token = GUST.set(app)
    utoken = USER.set(user)
    htoken = HANDLER.set(handler)
    try:
        yield
    finally:
        GUST.reset(token)
        USER.reset(utoken)
        HANDLER.reset(htoken)


def get_app():
    """get the context app"""
    return GUST.get(None)


def get_handler():
    """get the current handler"""
    return HANDLER.get(None)

def get_current_user():
    """get the context app"""
    return USER.get(None)
