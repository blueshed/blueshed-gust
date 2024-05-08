"""We handle websocket methods"""

import logging
from collections import defaultdict
from typing import List

from tornado.ioloop import IOLoop
from tornado.util import unicode_type
from tornado.websocket import WebSocketHandler

from . import json_utils
from .utils import JsonRpcException, JsonRpcResponse, UserMixin

log = logging.getLogger(__name__)


class Websocket(UserMixin, WebSocketHandler):
    """Websocket Class"""

    _clients_ = defaultdict(list)

    def initialize(self, method_settings):
        """setup variables"""
        self.method_settings = method_settings
        self.io_loop = IOLoop.current()
        log.debug('%r', method_settings)

    def check_origin(self, origin):
        """in development allow ws from anywhere"""
        if self.settings.get('debug', False):
            return True
        return super().check_origin(origin)

    async def call_func(self, method, data=None):
        """call the function"""
        log.debug('%s %r', method, data)

        if self.method_settings.auth and self.current_user is None:
            self.close(401, 'not authenticated')
            return

        result = error = None
        handling = args = kwargs = None

        ref = None
        if data and data.startswith('{"jsonrpc":'):
            content = json_utils.loads(data)
            log.debug(content)
            ref = content.get('id', None)
            proc = content.get('method')
            if proc is None:
                error = JsonRpcException(-32600, 'no method')

            elif not proc in self.method_settings.ws_rpc:
                error = JsonRpcException(-32600, 'not method')

            if error is None:
                handling = self.method_settings.ws_rpc[proc].func

                params = content.get('params', {})
                if params and not isinstance(content['params'], (dict, list)):
                    error = JsonRpcException(
                        -32602, 'Params neither list or dict'
                    )

                args = params if params and isinstance(params, (list,)) else []
                kwargs = (
                    params if params and isinstance(params, (dict,)) else {}
                )
        else:
            handling = getattr(self.method_settings, method)
            if handling is None:
                log.debug('no func: %s(%s)', method, data)
                if method == 'ws_close':
                    self.remove_client()
                return
            handling = handling.func
            args = [self]
            kwargs = {'message': data} if data else {}

        if error is None:
            try:
                log.debug('calling: %s %r, %r', handling, args, kwargs)
                result = await self.application.perform(
                    self, self.current_user, handling, *args, **kwargs
                )
                if ref:
                    log.debug('have result: %s', result)
            except Exception as ex:  # pylint: disable=W0703
                log.exception('%s: %r', method, data)
                error = ex
            finally:
                # close is a synchronous so we tidy up
                if method == 'ws_close':
                    self.remove_client()
                    ref = None

        if ref:
            self.queue_message(
                json_utils.dumps(
                    JsonRpcResponse(
                        id=ref,
                        result=result,
                        error=error,
                    )
                )
            )

    async def open(self, *args, **kwargs):
        """websocket open"""
        log.debug('open')
        self._clients_[self.request.path].append(self)
        await self.call_func('ws_open')

    async def on_message(self, message):
        """handle the action"""
        log.debug(message)
        try:
            await self.call_func('ws_message', message)
        except Exception:
            log.exception(message)
            raise

    def on_close(self):
        """
        unregister user
        close is a synchronous so call_func will tidy up
        """
        log.debug('close')
        self.io_loop.add_callback(self.call_func, 'ws_close')

    def remove_client(self):
        """remove self from clients"""
        try:
            self._clients_[self.request.path].remove(self)
            log.debug('removed from clients')
        except ValueError:
            pass

    def send_message(self, message):
        """make sure we're not closed"""
        log.debug('sending: %r', message)
        if self.ws_connection:
            self.write_message(message)
        else:
            log.warning('message sent after close: %s', message)

    def queue_message(self, message):
        """
        Because io_loops are not alone we remember the
        one we were initialized on. This add_callback
        method is thread safe and will schedule the
        function for next iteration.
        """
        self.io_loop.add_callback(self.send_message, message)

    @classmethod
    def broadcast(
        cls, tornado_path: str, message: str, client_ids: List[int] = None
    ):
        """send to all connected"""
        if not isinstance(message, (bytes, unicode_type)):
            message = json_utils.dumps(message)
        clients = cls._clients_.get(tornado_path)  # should be a match
        if clients:
            for client in clients:
                if client_ids and (
                    client.current_user is None
                    or client.current_user.get('id') not in client_ids
                ):
                    continue
                client.queue_message(message)
