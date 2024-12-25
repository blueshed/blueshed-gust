# pylint: disable=attribute-defined-outside-init, unused-argument
"""test our appication"""

import asyncio
import logging

import pytest

from blueshed.gust import Gust, Routes, json_utils, stream

routes = Routes()


@routes.ws_json_rpc('/ws')
@stream
async def people(count=4):
    """stream people"""
    print('here', count)
    for i in range(count):
        yield str(i)


@pytest.fixture(scope='module')
def app(web_context):
    """return the app for pytest-asyncio"""
    appl = Gust()
    routes.install(appl)
    return appl


async def test_add(ws_client, caplog):
    """test add function via websocket"""
    with caplog.at_level(logging.DEBUG):
        ws_client = await ws_client
        message = {
            'jsonrpc': '2.0',
            'method': 'people',
            'params': {'stream_id': 'foo', 'count': 4},
            'id': 1,
        }
        await ws_client.write_message(json_utils.dumps(message))
        await asyncio.sleep(0.01)
        await ws_client.read_message()
        # assert False, msg
        for _ in range(4):
            data = await ws_client.read_message()
            result: dict = json_utils.loads(data)
            if result.get('count') == 4:
                break

    ws_client.close()
    await asyncio.sleep(0.01)
