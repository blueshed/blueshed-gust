"""our fixtures"""

import pytest
from tornado.websocket import websocket_connect

from blueshed.gust import web


@pytest.fixture(scope='module')
def web_context():
    """reset our context"""
    web.route_map = {}


@pytest.fixture
async def ws_client(http_server, http_server_port):
    """return a websocket client"""
    result = await websocket_connect(
        f'ws://localhost:{http_server_port[1]}/ws', connect_timeout=0.1
    )
    return result
