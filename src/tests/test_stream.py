from blueshed.gust import Stream
from blueshed.gust import json_utils as json
from blueshed.gust.utils import JsonRpcResponse


def test_stream():
    """can we stream"""

    async def response():
        yield 'foo'

    s = Stream(response())
    r = JsonRpcResponse(1, s, None)
    value = json.dumps(r)
    print(value)
    assert (
        value
        == '{"id": 1, "jsonrpc": "2.0", "result": {"stream_id": "'
        + s.id
        + '"}}'
    )
