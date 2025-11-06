# Add JSON-RPC Error Code Constants

**Labels:** `enhancement`, `code-quality`, `medium-priority`
**Milestone:** 0.2.0

## Overview
Replace magic numbers for JSON-RPC error codes with named constants for better maintainability and documentation.

## Current State
Error codes are hardcoded throughout `websocket.py`:
- `-32700`: Parse Error
- `-32600`: Invalid Request
- `-32601`: Method Not Found
- `-32602`: Invalid Params
- `-32603`: Internal Error

**Examples in code:**
```python
# websocket.py:67
error = JsonRpcException(-32600, 'no method')

# websocket.py:74-76
error = JsonRpcException(-32602, 'Params neither list or dict')

# websocket.py:83
error = JsonRpcException(-32600, 'not method')

# websocket.py:126
error = JsonRpcException(-32603, error_msg)
```

## Problems
- Magic numbers reduce code readability
- Error codes not documented centrally
- Harder to maintain consistency
- Users need to look up JSON-RPC spec for meaning

## Proposed Solution

### 1. Create Constants Class

**File:** `src/blueshed/gust/utils.py` (add class)
```python
class JsonRpcErrorCode:
    """
    JSON-RPC 2.0 error codes as defined in the specification.
    https://www.jsonrpc.org/specification#error_object
    """
    # Standard JSON-RPC 2.0 errors
    PARSE_ERROR = -32700      # Invalid JSON
    INVALID_REQUEST = -32600  # Invalid JSON-RPC request
    METHOD_NOT_FOUND = -32601 # Method does not exist
    INVALID_PARAMS = -32602   # Invalid method parameters
    INTERNAL_ERROR = -32603   # Internal JSON-RPC error

    # Server errors (-32000 to -32099 reserved for implementation-defined)
    # Add custom error codes here if needed
```

### 2. Update websocket.py to Use Constants
```python
from .utils import JsonRpcErrorCode

# Line 67
if proc is None:
    error = JsonRpcException(
        JsonRpcErrorCode.INVALID_REQUEST,
        'no method'
    )

# Line 74-76
if params and not isinstance(content['params'], (dict, list)):
    error = JsonRpcException(
        JsonRpcErrorCode.INVALID_PARAMS,
        'Params neither list or dict'
    )

# Line 83
elif proc not in self.method_settings.ws_rpc:
    error = JsonRpcException(
        JsonRpcErrorCode.METHOD_NOT_FOUND,
        f'Method not found: {proc}'
    )

# Line 126
error = JsonRpcException(
    JsonRpcErrorCode.INTERNAL_ERROR,
    error_msg
)
```

### 3. Export from __init__.py
```python
from .utils import JsonRpcErrorCode

__all__ = [
    'Gust',
    'Routes',
    'Redirect',
    'stream',
    'Stream',
    'web',
    'get_handler',
    'AuthStaticFileHandler',
    'PostgresRPC',
    'AuthPostgresRPC',
    'JsonRpcErrorCode',  # Add this
]
```

### 4. Update Tests
```python
# test_web.py - update error code assertions
from blueshed.gust import JsonRpcErrorCode

async def test_missing_method(ws_client):
    # ...
    assert JsonRpcErrorCode.INVALID_REQUEST == response['error']['code']

async def test_not_method(ws_client):
    # ...
    assert JsonRpcErrorCode.METHOD_NOT_FOUND == response['error']['code']

async def test_wrong_params(ws_client):
    # ...
    assert JsonRpcErrorCode.INVALID_PARAMS == response['error']['code']
```

### 5. Document Error Codes
Add to API documentation and README:
```markdown
## JSON-RPC Error Codes

Gust follows the JSON-RPC 2.0 specification for error codes:

| Code   | Constant                    | Meaning               |
|--------|-----------------------------|-----------------------|
| -32700 | PARSE_ERROR                 | Invalid JSON          |
| -32600 | INVALID_REQUEST             | Invalid JSON-RPC      |
| -32601 | METHOD_NOT_FOUND            | Method doesn't exist  |
| -32602 | INVALID_PARAMS              | Invalid parameters    |
| -32603 | INTERNAL_ERROR              | Server error          |

Usage:
```python
from blueshed.gust import JsonRpcErrorCode
from blueshed.gust.utils import JsonRpcException

raise JsonRpcException(
    JsonRpcErrorCode.INVALID_PARAMS,
    "Missing required parameter: user_id"
)
```
```

## Implementation Checklist
- [ ] Create `JsonRpcErrorCode` class in utils.py
- [ ] Update all hardcoded error codes in websocket.py
- [ ] Export JsonRpcErrorCode from __init__.py
- [ ] Update tests to use constants
- [ ] Add docstrings with JSON-RPC spec link
- [ ] Document error codes in README
- [ ] Update API documentation

## Acceptance Criteria
- [ ] No hardcoded error codes remain in websocket.py
- [ ] All error codes use named constants
- [ ] Tests pass and use constants
- [ ] Documentation includes error code reference
- [ ] Backward compatible (error code values unchanged)

## Benefits
- **Readability**: `JsonRpcErrorCode.METHOD_NOT_FOUND` is clearer than `-32601`
- **Discoverability**: IDE autocomplete shows available error codes
- **Maintainability**: Change error codes in one place
- **Documentation**: Constants serve as self-documentation
- **Consistency**: Harder to use wrong error code

## Related
- Code review finding #9: Magic numbers in error codes
- Improves code quality and maintainability
- Aligns with JSON-RPC 2.0 specification

## References
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [Error object definition](https://www.jsonrpc.org/specification#error_object)
