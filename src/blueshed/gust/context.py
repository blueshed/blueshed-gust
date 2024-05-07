"""when functions are called we set up a context"""

import contextlib
import contextvars

GUST = contextvars.ContextVar('_gust_GUST')
USER = contextvars.ContextVar('_gust_USER')


@contextlib.contextmanager
def gust(app, user):
    """With this we setup contextvars and reset for our app"""
    token = GUST.set(app)
    utoken = USER.set(user)
    try:
        yield
    finally:
        GUST.reset(token)
        USER.reset(utoken)


def get_app():
    """get the context app"""
    return GUST.get(None)


def get_current_user():
    """get the context app"""
    return USER.get(None)
