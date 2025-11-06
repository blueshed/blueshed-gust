# Add Optional Input Validation Support

**Labels:** `enhancement`, `validation`, `medium-priority`
**Milestone:** 0.2.0

## Overview
Add optional schema validation for HTTP request bodies and WebSocket messages using Pydantic or dataclasses.

## Current State
- No built-in input validation
- Handlers receive raw request data
- Developers must write custom validation
- Type hints exist but aren't enforced

## Proposed Solution

### Option 1: Pydantic Integration (Recommended)
```python
from pydantic import BaseModel
from blueshed.gust import web

class UserCreate(BaseModel):
    username: str
    email: str
    age: int = 18

@web.post('/users', validate=UserCreate)
def create_user(request, data: UserCreate):
    # data is validated UserCreate instance
    return {'id': 123, 'username': data.username}

# WebSocket validation
@web.ws_json_rpc('/api', validate=UserCreate)
def create_user_ws(username: str, email: str, age: int = 18):
    # Parameters automatically validated
    return {'id': 123}
```

### Option 2: Dataclass Validation
```python
from dataclasses import dataclass
from blueshed.gust import web

@dataclass
class UserCreate:
    username: str
    email: str
    age: int = 18

@web.post('/users', validate=UserCreate)
def create_user(request, data: UserCreate):
    return {'id': 123}
```

## Implementation Steps

### 1. Add Pydantic as Optional Dependency
```toml
[dependency-groups]
validation = [
    "pydantic>=2.0",
]
```

### 2. Create Validation Decorator
**File:** `src/blueshed/gust/validation.py` (new)
```python
"""Input validation support"""

from functools import wraps
from typing import Type, Union
import inspect

try:
    from pydantic import BaseModel, ValidationError as PydanticValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None

from .exceptions import ValidationError


def validate_input(schema: Type):
    """
    Decorator to validate input against a schema.

    Supports Pydantic models and dataclasses.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request data
            if 'request' in kwargs:
                request = kwargs['request']
                try:
                    body = request.get_body()
                    data = json.loads(body) if body else {}
                except Exception:
                    raise ValidationError("Invalid JSON in request body")
            else:
                data = kwargs

            # Validate with Pydantic
            if PYDANTIC_AVAILABLE and isinstance(schema, type) and issubclass(schema, BaseModel):
                try:
                    validated = schema(**data)
                    kwargs['data'] = validated
                except PydanticValidationError as e:
                    raise ValidationError(str(e))

            # Validate with dataclass
            elif hasattr(schema, '__dataclass_fields__'):
                try:
                    validated = schema(**data)
                    kwargs['data'] = validated
                except TypeError as e:
                    raise ValidationError(f"Invalid input: {e}")

            return await func(*args, **kwargs)

        return wrapper
    return decorator
```

### 3. Integrate with Routes
**File:** `routes.py` - Add validate parameter
```python
def post(self, path, template=None, auth=False, validate=None):
    """wrap a POST with optional validation"""
    return self.default_wrap(
        method='post',
        path=path,
        template=template,
        auth=auth,
        validate=validate
    )
```

### 4. Add Validation Tests
```python
from pydantic import BaseModel
from blueshed.gust import web

class Item(BaseModel):
    name: str
    price: float

@web.post('/items', validate=Item)
def create_item(request, data: Item):
    return {'created': True, 'name': data.name}

async def test_validation_success(http_server_client):
    response = await http_server_client.fetch(
        '/items',
        method='POST',
        body=json.dumps({'name': 'Widget', 'price': 9.99})
    )
    assert response.code == 200

async def test_validation_failure(http_server_client):
    response = await http_server_client.fetch(
        '/items',
        method='POST',
        body=json.dumps({'name': 'Widget'}),  # Missing price
        raise_error=False
    )
    assert response.code == 400
    assert 'price' in response.body.decode()
```

## Acceptance Criteria
- [ ] Pydantic added as optional dependency
- [ ] Validation decorator works for HTTP POST/PUT
- [ ] Validation decorator works for WebSocket JSON-RPC
- [ ] Clear error messages for validation failures
- [ ] Tests for valid and invalid inputs
- [ ] Documentation with examples
- [ ] Backward compatible (validation is opt-in)
- [ ] Works without Pydantic installed (graceful degradation)

## Documentation
Add validation guide:
- How to use Pydantic models
- How to use dataclasses
- Custom validation logic
- Error handling
- Performance considerations

## Related
- Code review finding #8: No input validation
- Security improvement
- Developer experience enhancement

## Future Enhancements
- OpenAPI/Swagger schema generation from Pydantic models
- Automatic API documentation
- Request/response validation
- Custom validators
