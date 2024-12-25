"""Simple hello, world"""

import asyncio

from tornado.log import enable_pretty_logging
from tornado.options import options

from blueshed.gust import Gust, web


@web.get('/(.*)')
def get(request):
    """websocket test page"""
    return """
<script>
const ws = new WebSocket('ws://localhost:8080/ws');
ws.onopen = () => {
    ws.send(JSON.stringify({
        "jsonrpc": "2.0",
        "id": "1",
        "method": "add",
        "params": [2,2]
    }))
    ws.send(JSON.stringify({
        "jsonrpc": "2.0",
        "id": "2",
        "method": "a_add",
        "params": {a: 2, b: 3}
    }))
}
ws.onmessage = (evt) => {
    const pre = document.createElement("pre");
    pre.textContent = evt.data;
    document.body.appendChild(pre);
}
</script>
"""


@web.ws_json_rpc('/ws')
def add(a: int, b: int) -> int:
    """returns a plus b"""
    return a + b


@web.ws_json_rpc('/ws')
async def a_add(a: int, b: int, nap: float = 0.01) -> int:
    """returns a plus b"""
    await asyncio.sleep(nap)
    return a + b


def make_app():
    """seperate construction from run"""
    return Gust()


if __name__ == '__main__':
    options.logging = 'DEBUG'
    enable_pretty_logging(options)
    app = make_app()
    app.run()
