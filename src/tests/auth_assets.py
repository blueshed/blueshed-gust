"""assets for test_web"""

import logging
from dataclasses import dataclass

from blueshed.gust import Redirect, web

log = logging.getLogger(__name__)
PATH = '/bar/'


@dataclass
class User:
    """simple jsonable user"""

    id: int
    email: str


@web.get(f'{PATH}(.*)', auth=True)
async def home_get(request):
    """simple get"""
    return 'hello, world'


@web.post(f'{PATH}login')
async def login(request):
    """simple login"""
    if request.get_argument('password') == '12345':
        request.set_current_user(
            User(id=1, email=request.get_argument('email'))
        )
        raise Redirect('/')
    return {'message': 'hello, world'}


@web.get(f'{PATH}logout')
async def logout(request):
    """simple logout"""
    request.set_current_user(None)
    raise Redirect('/')


@web.ws_message(f'{PATH}ws', auth=True)
async def do_message(handler, message):
    """reverse the message"""
    log.info('got: %r', message)
    handler.queue_message(message[::-1])
