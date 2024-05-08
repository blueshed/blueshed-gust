"""main gust module"""

import asyncio
import functools
import inspect
import logging
import os
from typing import Any, List, Optional, Callable

from tornado.options import define, options
from tornado.web import Application

from . import context
from .configs import WebConfig
from .web import web
from .web_handler import WebHandler
from .websocket import Websocket

log = logging.getLogger(__name__)

define('debug', type=bool, default=False, help='auto reload')
define('port', type=int, default=8080, help='port')


class Gust(Application):
    """A minimal sub-class of tornado.web.Application"""

    def __init__(
        self,
        routes: Optional[List] = None,
        port: Optional[int] = None,
        **kwargs,
    ):
        self.port = port if port else os.getenv('PORT', options.port)
        super().__init__(routes, debug=options.debug, **kwargs)
        web.install(self)

    async def perform(self, handler, user, func: Callable, *args, **kwargs) -> Any:
        """await a function or call in a thread_pool, better yet call redis"""
        if inspect.iscoroutinefunction(func):
            log.debug('aperform: %s', func)
            with context.gust(self, user, handler):
                result = await func(*args, **kwargs)
        else:
            log.debug('perform: %s', func)
            partial = functools.partial(
                self.call_in_context, user, handler, func, args, kwargs
            )
            result = await asyncio.to_thread(partial)
        return result

    def call_in_context(self, user, handler, func, args, kwargs):
        """set the context and call function"""
        with context.gust(self, user, handler):
            return func(*args, **kwargs)

    @classmethod
    def broadcast(cls, path, message, client_ids):
        """pass through, maybe point for redis gust"""
        Websocket.broadcast(path, message, client_ids)

    async def _run_(self):  # pragma: no cover
        """listen on self.port and run io_loop"""
        if self.port:
            self.listen(self.port)
            log.info('listening on port: %s', self.port)
        else:
            log.warning("No 'port' in settings")

        if self.settings.get('debug') is True:
            log.info('running in debug mode')

        await asyncio.Event().wait()

    def run(self):  # pragma: no cover
        try:
            asyncio.get_event_loop().run_until_complete(self._run_())
        except (KeyboardInterrupt, SystemExit):
            # graceful shutdown
            pass
