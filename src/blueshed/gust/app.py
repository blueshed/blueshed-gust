"""main gust module"""

import asyncio
import functools
import inspect
import logging
import os
from typing import Any, Callable, List, Optional

from tornado.options import define, options
from tornado.web import Application

from . import context
from .web import web
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
        self.port: int = port if port else int(os.getenv('PORT', options.port))
        if 'debug' not in kwargs:
            kwargs['debug'] = options.debug
        super().__init__(routes, **kwargs)
        web.install(self)

    async def perform(self, handler, func: Callable, *args, **kwargs) -> Any:
        """await a function or call in a thread_pool, better yet call redis"""
        if inspect.iscoroutinefunction(func):
            log.debug('aperform: %s', func)
            with context.gust(handler):
                result = await func(*args, **kwargs)
        else:
            log.debug('perform: %s', func)
            partial = functools.partial(
                self.call_in_context, handler, func, args, kwargs
            )
            result = await asyncio.to_thread(partial)
        if result:
            if inspect.isawaitable(result):
                result = await result
            if inspect.isasyncgen(result):
                result = handler.create_stream(result)
        return result

    def call_in_context(self, handler, func, args, kwargs):
        """set the context and call function"""
        with context.gust(handler):
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

    async def on_line(self, handler: Websocket):
        """called when a websocket opens"""

    async def off_line(self, handler: Websocket):
        """called when a websocket closes"""
