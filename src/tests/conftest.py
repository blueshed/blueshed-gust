"""our fixtures"""

import pytest
from tornado.websocket import websocket_connect

from blueshed.gust import web

pytest_plugins = ['pytest_tornado', 'pytest_asyncio']


@pytest.fixture(scope='module')
def web_context():
    """reset our context"""
    web.route_map = {}


@pytest.fixture
async def http_server_client(http_client, base_url):
    """
    Compatibility fixture that wraps http_client to work like the old http_server_client.
    Automatically prepends base_url to all fetch requests.
    """
    class ClientWrapper:
        def __init__(self, client, base):
            self._client = client
            self._base = base

        async def fetch(self, path, **kwargs):
            # If path doesn't start with http://, prepend base_url
            if not path.startswith('http://') and not path.startswith('https://'):
                path = self._base + path
            return await self._client.fetch(path, **kwargs)

    return ClientWrapper(http_client, base_url)


@pytest.fixture
def http_server_port(http_port):
    """Compatibility fixture for old http_server_port format"""
    return ('localhost', http_port)


@pytest.fixture
async def ws_client(http_server, http_port):
    """return a websocket client"""
    result = await websocket_connect(
        f'ws://localhost:{http_port}/ws', connect_timeout=0.1
    )
    return result
