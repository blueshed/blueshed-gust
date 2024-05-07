"""We gather routes"""

import logging
from typing import List

from .configs import WebConfig, WebMethod, WsConfig
from .web_handler import WebHandler
from .websocket import Websocket

log = logging.getLogger(__name__)


class Routes:
    """to organise our decorators"""

    def __init__(self) -> None:
        self.route_map = {}
        self.broadcaster = None

    def get(
        self,
        path,
        template=None,
        auth=False,
    ):
        """wrap a GET"""
        return self.default_wrap(
            method='get', path=path, template=template, auth=auth
        )

    def post(
        self,
        path,
        template=None,
        auth=False,
    ):
        """wrap a POST"""
        return self.default_wrap(
            method='post', path=path, template=template, auth=auth
        )

    def put(
        self,
        path,
        template=None,
        auth=False,
    ):
        """wrap a PUT"""
        return self.default_wrap(
            method='put', path=path, template=template, auth=auth
        )

    def delete(
        self,
        path,
        template=None,
        auth=False,
    ):
        """wrap a DELETE"""
        return self.default_wrap(
            method='delete', path=path, template=template, auth=auth
        )

    def head(
        self,
        path,
        template=None,
        auth=False,
    ):
        """wrap a HEAD"""
        return self.default_wrap(
            method='head', path=path, template=template, auth=auth
        )

    def ws_open(
        self,
        path,
        auth=False,
    ):
        """wrap an on_open"""
        return self.default_wrap(
            method='ws_open', path=path, template=None, auth=auth
        )

    def ws_message(
        self,
        path,
        auth=False,
    ):
        """wrap an on_message"""
        return self.default_wrap(
            method='ws_message', path=path, template=None, auth=auth
        )

    def ws_close(
        self,
        path,
        auth=False,
    ):
        """wrap an on_close"""
        return self.default_wrap(
            method='ws_close', path=path, template=None, auth=auth
        )

    def ws_json_rpc(
        self,
        path,
        auth=False,
    ):
        """wrap a json remote procedure"""
        return self.default_wrap(
            method='ws_rpc', path=path, template=None, auth=auth
        )

    def broadcast(self, path: str, message: str, client_ids: List[int] = None):
        """broadcast to a path"""
        self.broadcaster.broadcast(path, message, client_ids)

    def default_wrap(
        self,
        method,
        path,
        template=None,
        auth=False,
    ):
        """wrap a method"""

        def inner_decorator(func):
            """we have the function"""
            web_method = WebMethod(func=func, template=template, auth=auth)
            if method.startswith('ws_'):
                cfg = self.route_map.setdefault(path, WsConfig())
                if method.startswith('ws_rpc'):
                    cfg.ws_rpc[func.__name__] = web_method
                else:
                    setattr(cfg, method, web_method)
                if auth is True:
                    cfg.auth = True
            else:
                cfg = self.route_map.setdefault(path, WebConfig())
                setattr(cfg, method, web_method)
            return func

        return inner_decorator

    def install(self, app):
        routes = []
        for path, cfg in self.route_map.items():
            handler = (
                WebHandler if isinstance(cfg, (WebConfig,)) else Websocket
            )
            routes.append((rf'{path}', handler, {'method_settings': cfg}))
        routes.sort(reverse=True)
        self.broadcaster = app
        app.add_handlers('.*', routes)
        return routes
