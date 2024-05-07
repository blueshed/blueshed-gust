"""
We need authenticated access to static files
"""

from tornado.web import StaticFileHandler

from .utils import UserMixin


class AuthStaticFileHandler(UserMixin, StaticFileHandler):
    """
    This provide integration between tornado.web.authenticated
    and tornado.web.StaticFileHandler.

    It assumes you have set up the cookie name in the application
    settings and that the request already has the cookie set. In
    other words the user has already authenticated.
    """

    def initialize(self, allow: list = None, **kwargs):
        """allow some paths through"""
        super().initialize(**kwargs)
        self.allow = allow if allow else []

    def get(self, path, include_body=True):
        """safe to return what you need"""
        if self.current_user is None and path not in self.allow:
            self.not_authenticated()
        return StaticFileHandler.get(self, path, include_body)
