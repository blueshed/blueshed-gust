"""We handle websocket methods"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, List, Optional

from tornado.util import unicode_type
from tornado.websocket import WebSocketClosedError, WebSocketHandler

from blueshed.gust.stream import Stream

from . import context, json_utils
from .utils import JsonRpcException, JsonRpcResponse, UserMixin

log = logging.getLogger(__name__)


class Websocket(UserMixin, WebSocketHandler):
    """Websocket Class"""

    _clients_ = defaultdict(list)
    _tasks_ = set()

    def initialize(self, method_settings):
        """setup variables"""
        self.method_settings = method_settings
        log.debug('%r', method_settings)

    @classmethod
    def _done_(cls, task: asyncio.Task):
        """task complete, remove reference"""
        try:
            cls._tasks_.remove(task)
        except KeyError:
            log.warning('Task [%s] not found in _tasks_ set', task.get_name())

    @classmethod
    def _background_(cls, *tasks: asyncio.Task):
        for task in tasks:
            cls._tasks_.add(task)
            task.add_done_callback(cls._done_)

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

            elif proc not in self.method_settings.ws_rpc:
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
                    self, handling, *args, **kwargs
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
            if result and isinstance(result, Stream):
                self.create_stream(result.gen, result.id)

    async def open(self, *args, **kwargs):
        """websocket open"""
        log.debug('open')
        self._clients_[self.request.path].append(self)
        with context.gust(self):
            await self.application.on_line(self)
        await self.call_func('ws_open')

    async def on_message(self, message):
        """handle the action"""
        log.debug(message)
        try:
            task = asyncio.create_task(self.call_func('ws_message', message))
            self._background_(task)
        except Exception:  # pragma no cover
            log.exception(message)
            raise

    def on_close(self):
        """
        unregister user
        close is a synchronous so call_func will tidy up
        """
        log.debug('close')
        with context.gust(self):
            self._background_(
                asyncio.create_task(self.call_func('ws_close')),
                asyncio.create_task(self.application.off_line(self)),
            )

    def remove_client(self):
        """remove self from clients"""
        try:
            self._clients_[self.request.path].remove(self)
            log.debug('removed from clients')
        except ValueError:
            log.warning('client removal failed')

    async def send_message(self, message):
        """make sure we're not closed"""
        log.debug('sending: %r', message)
        if self.ws_connection:
            await self.write_message(message)
        else:
            log.warning('message sent after close: %s', message)

    def queue_message(self, message):
        """
        Because io_loops are not alone we remember the
        one we were initialized on. This add_callback
        method is thread safe and will schedule the
        function for next iteration.
        """
        task = asyncio.create_task(self.send_message(message))
        self._background_(task)

    @classmethod
    def broadcast(
        cls,
        tornado_path: str,
        message: str,
        client_ids: Optional[List[int]] = None,
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

    def create_stream(self, gen: Any, stream_id: str = None) -> str:
        """Create a stream and set it to run in the background."""
        task = asyncio.create_task(
            self.stream_results(gen, stream_id), name=stream_id
        )
        self._tasks_.add(task)
        task.add_done_callback(self.stream_done)
        return stream_id

    async def stream_message(self, stream_id: str, **kwargs: Any):
        """Write a stream message."""
        log.debug('streaming: %s', kwargs)
        await self.write_message(
            json_utils.dumps({'stream_id': stream_id} | kwargs)
        )

    async def stream_results(self, gen: Any, stream_id: str = None):
        """Write out stream results."""
        if stream_id is None:
            # stream_id will be the first item
            stream_id = await anext(gen)
            log.debug('stream_id: %s', stream_id)
        count = 0
        async for item in gen:
            await self.stream_message(stream_id, args=item)
            count = count + 1
        await self.stream_message(stream_id, count=count)

    def stream_done(self, task: asyncio.Task):
        """Handle task completion."""
        self._tasks_.discard(task)
        try:
            task.result()
        except WebSocketClosedError:
            pass
        except Exception as ex:
            log.exception(ex)
            self.queue_message(
                json_utils.dumps(
                    {
                        'stream_id': task.get_name(),
                        'args': self.stream_message,
                        'error': str(ex),
                    }
                )
            )
