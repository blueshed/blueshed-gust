# pylint: disable=W0611, C0415, W0621
"""a test of chain of events"""

import asyncio
import logging
import urllib.parse

import pytest
from blueshed.gust import Gust, json_utils, web
from tornado.httpclient import HTTPRequest
from tornado.template import DictLoader
from tornado.websocket import websocket_connect

PATH = '/bar/'


@pytest.fixture(scope='module')
def app(web_context):
    """return the app for pytest-asyncio"""
    from . import auth_assets as assets

    appl = Gust(
        login_url='/bar/login',
        cookie_name='test_auth_cookie',
        cookie_secret='it was a dark and stormy test',
        debug=True,
    )
    return appl


@pytest.fixture
async def cookie(http_server, http_server_client):
    """login to get a cookie"""
    response = await http_server_client.fetch(
        f'{PATH}login',
        headers={
            'Content-type': 'application/x-www-form-urlencoded',
            'Accept': 'text/plain',
        },
        method='POST',
        body=urllib.parse.urlencode(
            {'email': 'rpc@ws.com', 'password': '12345', 'submit': 'login'}
        ),
        follow_redirects=False,
        raise_error=False,
    )
    print(response)
    return response.headers['Set-Cookie']


@pytest.fixture
async def ws_client(http_server, http_server_port, cookie):
    """return a websocket client"""
    request = HTTPRequest(
        f'ws://localhost:{http_server_port[1]}{PATH}ws',
        headers={'Cookie': await cookie},
    )
    result = await websocket_connect(request)
    return result


async def test_no_auth(http_server_client, http_client, http_server_port):
    """do we redirect to login"""
    response = await http_server_client.fetch(
        PATH, follow_redirects=False, raise_error=False
    )
    assert response.code == 302
    response = await http_client.fetch(
        f'http://localhost:{http_server_port[1]}{PATH}',
        follow_redirects=False,
        raise_error=False,
    )
    assert response.code == 302


async def test_auth(http_server_client, cookie, caplog):
    """do we redirect to login"""
    print(web.route_map)
    with caplog.at_level(logging.DEBUG):
        response = await http_server_client.fetch(
            PATH,
            follow_redirects=False,
            raise_error=False,
            headers={'Cookie': await cookie},
        )
    assert response.code == 200
    assert response.body == b'hello, world'


async def test_logout(http_server_client, cookie, caplog):
    """do we redirect on logout"""
    print(web.route_map)
    with caplog.at_level(logging.DEBUG):
        response = await http_server_client.fetch(
            PATH + 'logout',
            follow_redirects=False,
            raise_error=False,
            headers={'Cookie': await cookie},
        )
    assert response.code == 302
    assert 'Set-Cookie' in response.headers


async def test_message(ws_client, caplog):
    """test add function via websocket"""
    with caplog.at_level(logging.DEBUG):
        client = await ws_client
        message = 'hi there'
        await client.write_message(message)
        response = await client.read_message()
        print(response)
        assert response == 'ereht ih'
    client.close()
    await asyncio.sleep(0.01)


async def test_ws_no_auth(http_server, http_server_port, caplog):
    """test add function via websocket"""
    with caplog.at_level(logging.DEBUG):
        client = await websocket_connect(
            f'ws://localhost:{http_server_port[1]}{PATH}ws'
        )
        await asyncio.sleep(0.01)
        assert client.close_code == 401
        assert client.close_reason == 'not authenticated'


async def test_broadcast(ws_client, caplog):
    """test add function via websocket"""
    with caplog.at_level(logging.DEBUG):
        client = await ws_client
        message = 'hi there'
        web.broadcast(f'{PATH}ws', 'not hi', [2])
        web.broadcast(f'{PATH}ws', message, [1])
        response = await client.read_message()
        print(response)
        assert response == message
    client.close()
    await asyncio.sleep(0.01)
