"""assets for test_web"""

import asyncio
import logging

from blueshed.gust import web

log = logging.getLogger(__name__)
PATH = '/foo/'


@web.get(f'{PATH}(.*)')
async def home_get(request):
    """simple get"""
    return 'hello, world'


@web.head(f'{PATH}(.*)')
async def home_head(request):
    """simple get"""
    request.set_header('Content-Type', 'text/text')
    request.set_header('Content-Length', len('hello, world'))


@web.get(f'{PATH}query')
async def home_list(request):
    """return a list"""
    return ['hello, world']


@web.get(f'{PATH}bad')
def bad(request):
    """return a list"""
    raise Exception('helo, bad')


@web.post(f'{PATH}(.*)')
async def home_post(request):
    """simple post"""
    return {'message': 'hello, world'}


@web.put('/harry(.*)', template='home')
async def harry_put(request):
    """simple put"""
    return {'message': "harry's, world"}


@web.delete(f'{PATH}bad')
async def delete_something(request):
    """it's gone"""
    return 'ok'


@web.ws_json_rpc('/ws')
def add(a: int, b: int) -> int:
    """returns a plus b"""
    return a + b


@web.ws_json_rpc('/ws')
async def a_add(a: int, b: int, nap: float = 0.01) -> int:
    """returns a plus b"""
    await asyncio.sleep(nap)
    return a + b


@web.ws_open('/ws')
async def do_open(handler):
    """what to do?"""


@web.ws_close('/ws')
async def do_close(handler):
    """what to do?"""


@web.ws_message('/ws')
async def do_message(handler, message):
    """reverse the message"""
    log.info('got: %r', message)
    handler.queue_message(message[::-1])
