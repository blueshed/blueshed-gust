<div style="float: right;">
<img src="https://s3.eu-west-1.amazonaws.com/blueshed.info/published/gust3.webp" width="64" title="windy weather">
</div>

# Gust

![PyPI - Version](https://img.shields.io/pypi/v/blueshed-gust?pypiBaseUrl=https%3A%2F%2Fpypi.org&style=social)

Gust is a wrapper of [tornado](https://www.tornadoweb.org/en/stable/). It allows for a hello world such as:

```python
from blueshed.gust import Gust, web

@web.get('/(.*)')
def get(request):
    """just a get"""
    return 'hello, world'

def main():
    """seperate construction from run"""
    Gust().run()

if __name__ == '__main__':
    main()
```

Similarly, you can write:

```python

@web.ws_json_rpc('/websocket')
def add(a:float, b:float) -> float:
    """simple addition"""
    return a + b

```

And use a javascript websocket client to call the function:

```javascript
const ws = new WebSocket("ws://localhost:8080/websocket");
ws.onopen = function () {
  ws.send(
    JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "add",
      params: { a: 2.0, b: 2.0 }, // or [2.0, 2.0]
    }),
  );
};
ws.onmessage = function (evt) {
  const pre = document.createElement("pre");
  pre.textContent = evt.data;
  document.body.appendChild(pre);
};
```

## Direct PostgreSQL Function Calling

Gust also supports calling PostgreSQL stored functions directly via WebSocket JSON-RPC:

```python
from blueshed.gust import Gust, web, PostgresRPC
from psycopg import AsyncConnection

async def main():
    conn = await AsyncConnection.connect("postgresql://user:pass@localhost/mydb")
    pg_rpc = PostgresRPC(conn)
    web.ws_json_rpc('/api', handler=pg_rpc)
    Gust(port=8080).run()
```

Call any PostgreSQL function using the same JSON-RPC protocol shown above. An authenticated variant (`AuthPostgresRPC`) is available for automatic user injection. See `samples/postgres_rpc_demo/` for complete examples.

There are simple sample apps in src/tests.

## Documentation

- **[API Documentation](https://blueshed.github.io/blueshed-gust/blueshed/gust.html)** - Complete API reference
- **[CHANGELOG](CHANGELOG.md)** - Version history and release notes
- **[CLAUDE.md](CLAUDE.md)** - Project guidance for AI-assisted development
- **[Samples](samples/)** - Example applications and demos
