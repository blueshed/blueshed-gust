# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Gust is a lightweight wrapper around [Tornado](https://www.tornadoweb.org/) that simplifies creating HTTP and WebSocket handlers through Python decorators. It provides:
- HTTP route handlers (GET, POST, PUT, DELETE, HEAD)
- WebSocket support with JSON-RPC method calls
- Stream support for async generators
- Built-in authentication hooks
- Static file serving with optional authentication

## Project Setup

### Initial Setup
```bash
make setup
```

This creates a virtual environment using `uv` and installs development dependencies.

### Key Commands

Using `invoke` (aliased as `inv`):
- `inv lint` - Format code with Ruff and fix import sorting
- `inv docs` - Generate API documentation with pdoc
- `inv build` - Build distribution packages (wheel + sdist) after linting and docs
- `inv commit -m "message"` - Commit and push with docs generation
- `inv release -m "message" --part=patch` - Full release pipeline to PyPI

### Testing
```bash
pytest                    # Run all tests with coverage
pytest -k test_web       # Run specific test file
pytest -xvs             # Run with verbose output, stop on first failure
```

Tests are in `src/tests/` and use pytest with pytest-tornado and pytest-tornasync fixtures.

## Architecture

### Core Layers

1. **Route Definition Layer** (`routes.py`):
   - `Routes` class collects decorated handler functions
   - Decorators: `@web.get()`, `@web.post()`, `@web.ws_json_rpc()`, etc.
   - Stores configuration in `route_map` (path → WebConfig/WsConfig)
   - `install()` method converts decorator config into Tornado URL patterns

2. **Application Layer** (`app.py`):
   - `Gust` subclasses `tornado.web.Application`
   - `perform()` method handles both sync and async functions
   - Manages context via `context.gust()` context manager
   - Handles async generators as streams
   - Broadcast support for WebSocket messaging

3. **Handler Layers**:
   - **HTTP Handler** (`web_handler.py`): `WebHandler` extends `tornado.web.RequestHandler`
     - `prepare()` method routes to decorated function
     - Handles authentication check, template rendering, error handling
   - **WebSocket Handler** (`websocket.py`): `Websocket` extends `tornado.websocket.WebSocketHandler`
     - Manages client connections per path
     - Implements JSON-RPC protocol
     - Handles background task tracking

### Request Flow

HTTP Request:
```
HTTP Request → WebHandler.prepare() → calls Gust.perform(func)
→ func executes (sync via thread pool or async) → result rendered
or template applied → response sent
```

WebSocket Request:
```
WS Connection → Websocket.on_open() → calls ws_open handler
WS Message → Websocket.on_message() → routes to ws_rpc or ws_message
WS Close → Websocket.on_close() → calls ws_close handler
```

### Configuration Objects

- **`WebConfig`** (HTTP routes): Stores Optional `WebMethod` for get, post, put, delete, head
- **`WsConfig`** (WebSocket routes): Stores ws_open, ws_message, ws_close WebMethods plus dict of ws_rpc methods
- **`WebMethod`**: Holds func reference, template name, auth requirement

### Key Utilities

- **`json_utils.py`**: JSON encoding/decoding with special handling for datetime and other types
- **`stream.py`**: `Stream` class wraps async generators with UUID for tracking
- **`context.py`**: Context manager for thread-local handler storage
- **`utils.py`**: `UserMixin` (current_user support), `Redirect` exception, `JsonRpcResponse`

## Development Patterns

### Adding HTTP Routes
```python
from blueshed.gust import web

@web.get('/path')
def my_handler(request):
    return {'status': 'ok'}

@web.post('/path', auth=True)
def create_handler(request):
    # request.get_body(), request.get_argument()
    return {'created': True}
```

### Adding WebSocket Routes
```python
@web.ws_json_rpc('/ws')
def my_rpc_method(a: int, b: int) -> int:
    """Called via JSON-RPC"""
    return a + b

@web.ws_message('/ws')
async def handle_ws_message(handler, message):
    """Raw message handler"""
    pass

@web.ws_open('/ws')
async def on_open(handler):
    """Connection opened"""
    pass
```

### Streaming Results
Functions can return async generators which are automatically converted to `Stream` objects:
```python
@web.get('/stream')
async def stream_handler(request):
    async def data_gen():
        for i in range(10):
            yield {'item': i}
    return data_gen()
```

## Testing Patterns

The test suite uses:
- `pytest` with `pytest-tornado` for HTTP server fixtures
- `pytest-tornasync` for async test support
- `web_context` fixture to reset route map between test modules
- `ws_client` fixture for WebSocket client connection testing

Key fixtures from `conftest.py`:
- `http_server` - Tornado test server
- `http_server_port` - (host, port) tuple
- `ws_client` - Connected WebSocket client

## Common Tasks

### Running tests with specific patterns
```bash
pytest -k "test_json" -xvs
```

### Generating documentation
```bash
inv docs --view  # Generate and open in browser
```

### Checking code quality
```bash
ruff format src/
ruff check src/ --select I --fix  # Fix import ordering
```

### Managing version
Uses `bump-my-version` - version is read from `src/blueshed/gust/__init__.py` and bumped there automatically.
