# pylint: disable=W0611, C0415, W0621
"""a test of chain of events"""

import asyncio
import logging

import pytest
from tornado.template import DictLoader

from blueshed.gust import Gust, json_utils, web

PATH = '/foo/'


@pytest.fixture(scope='module')
def app(web_context):
    """return the app for pytest-asyncio"""
    from . import web_assets as assets

    logging.info(assets)  # aggressive linter

    appl = Gust(
        template_loader=DictLoader({'home': 'welcome to: {{message}}!'})
    )
    return appl


async def test_hello_get(http_server_client):
    """can we get hello, world"""
    response = await http_server_client.fetch(PATH)
    assert response.code == 200
    assert response.body == b'hello, world'


async def test_hello_head(http_server_client):
    """can we get hello, world"""
    response = await http_server_client.fetch(PATH, method='HEAD')
    assert response.code == 200


async def test_hello_bad(http_server_client):
    """can we get hello, world"""
    response = await http_server_client.fetch(PATH + 'bad', raise_error=False)
    assert response.code == 500


async def test_hello_delete(http_server_client, caplog):
    """can we get hello, world"""
    print(web.route_map)
    with caplog.at_level(logging.DEBUG):
        response = await http_server_client.fetch(
            PATH + 'bad', method='DELETE', raise_error=False
        )
        assert response.code == 200
        assert response.body == b'ok'


async def test_hello_query(http_server_client):
    """results must be dicts for wrapped list comes back"""
    response = await http_server_client.fetch(PATH + 'query')
    assert response.code == 200
    assert response.body == b'{"result": ["hello, world"]}'


async def test_405(http_server_client):
    """results must be dicts for wrapped list comes back"""
    response = await http_server_client.fetch(
        PATH + 'query', method='POST', raise_error=False, body=''
    )
    assert response.code == 405


async def test_hello_post(http_server_client):
    """can we post and get json back"""
    response = await http_server_client.fetch(PATH, method='POST', body='')
    assert response.code == 200
    assert json_utils.loads(response.body)['message'] == 'hello, world'


async def test_hello_404(http_server_client):
    """no such route"""
    response = await http_server_client.fetch(
        '/bert', method='GET', raise_error=False
    )
    assert response.code == 404


async def test_hello_500(http_server_client):
    """
    post body cannot be None so expect 500
    get to confirm server still happy
    """
    try:
        response = await http_server_client.fetch(PATH, method='POST')
        assert False, 'POST body cannot be None'
    except ValueError:
        pass
    response = await http_server_client.fetch(
        '/', method='GET', raise_error=False
    )
    assert response.code == 404


async def test_harry_put(http_server_client):
    """can we post and get json back"""
    response = await http_server_client.fetch('/harry/', method='PUT', body='')
    assert response.code == 200
    message = response.body.decode('utf-8')
    print(f'harry: {message}')
    assert message == 'welcome to: harry&#x27;s, world!'


async def test_add(ws_client, caplog):
    """test add function via websocket"""
    with caplog.at_level(logging.DEBUG):
        client = await ws_client
        message = {
            'jsonrpc': '2.0',
            'id': '1a',
            'method': 'add',
            'params': [2, 2],
        }
        await client.write_message(json_utils.dumps(message))
        response = await client.read_message()
        result = json_utils.loads(response)
        assert result['result'] == 4

    client.close()
    await asyncio.sleep(0.01)


async def test_a_add(ws_client):
    """test add function via websocket"""
    client = await ws_client
    message = {
        'jsonrpc': '2.0',
        'id': '1a',
        'method': 'a_add',
        'params': {'a': 2, 'b': 2},
    }
    await client.write_message(json_utils.dumps(message))
    response = await client.read_message()
    print(response)
    assert json_utils.loads(response)['result'] == 4
    client.close()
    await asyncio.sleep(0.01)


async def test_a_add_wrong(ws_client, caplog):
    """test add function via websocket"""
    client = await ws_client
    with caplog.at_level(logging.DEBUG):
        message = {
            'jsonrpc': '2.0',
            'id': '1a',
            'method': 'a_add',
            'params': {'a': 2, 'b': 'b'},
        }
        await client.write_message(json_utils.dumps(message))
        response = await client.read_message()
        print(response)
        error = json_utils.loads(response)['error']
        # Error can be dict (with code and message) or string
        if isinstance(error, dict):
            assert (
                error['message']
                == "unsupported operand type(s) for +: 'int' and 'str'"
            )
        else:
            assert (
                error == "unsupported operand type(s) for +: 'int' and 'str'"
            )
    client.close()
    await asyncio.sleep(0.01)


async def test_mising_method(ws_client, caplog):
    """test add function via websocket"""
    client = await ws_client
    with caplog.at_level(logging.DEBUG):
        message = {
            'jsonrpc': '2.0',
            'id': '1a',
            'params': {'a': 2, 'b': 2},
        }
        await client.write_message(json_utils.dumps(message))
        await asyncio.sleep(0.01)
    response = await client.read_message()
    print(response)
    assert {'code': -32600, 'message': 'no method'} == json_utils.loads(
        response
    )['error']
    client.close()
    await asyncio.sleep(0.01)


async def test_not_method(ws_client, caplog):
    """test add function via websocket"""
    client = await ws_client
    with caplog.at_level(logging.DEBUG):
        message = {
            'jsonrpc': '2.0',
            'id': '1a',
            'method': 'foo',
            'params': {'a': 2, 'b': 2},
        }
        await client.write_message(json_utils.dumps(message))
        await asyncio.sleep(0.01)
    response = await client.read_message()
    print(response)
    assert {'code': -32600, 'message': 'not method'} == json_utils.loads(
        response
    )['error']
    client.close()
    await asyncio.sleep(0.01)


async def test_wrong_params(ws_client, caplog):
    """test add function via websocket"""
    client = await ws_client
    with caplog.at_level(logging.DEBUG):
        message = {
            'jsonrpc': '2.0',
            'id': '1a',
            'method': 'add',
            'params': '2,2',
        }
        await client.write_message(json_utils.dumps(message))
        await asyncio.sleep(0.01)
    response = await client.read_message()
    print(response)
    assert 'Params neither list or dict' in str(
        json_utils.loads(response)['error']
    )
    client.close()
    await asyncio.sleep(0.01)


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


async def test_broadcast(ws_client, caplog):
    """test add function via websocket"""
    with caplog.at_level(logging.DEBUG):
        client = await ws_client
        message = 'hi there'
        web.broadcast('/ws', message)
        response = await client.read_message()
        print(response)
        assert response == message
    client.close()
    await asyncio.sleep(0.01)
