# Improve Error Handling and Response Standardization

**Labels:** `enhancement`, `refactoring`, `security`, `high-priority`
**Milestone:** 0.1.0

## Overview
Standardize error handling across HTTP and WebSocket handlers, and sanitize error messages for production to prevent information leakage.

## Problems Identified

### 1. Inconsistent Error Response Formats
- HTTP handlers return different error formats
- WebSocket handlers mix JSON-RPC and custom formats
- No standard structure for error responses

### 2. Information Leakage (Security Risk)
**Location:** `websocket.py:120-125`
```python
except Exception as ex:
    error_msg = str(ex)
    # For psycopg3 errors, try to get the primary diagnostic message
    if hasattr(ex, 'diag') and hasattr(ex.diag, 'message_primary'):
        error_msg = f'{ex.diag.message_primary} (Connection rolled back)'
    error = JsonRpcException(-32603, error_msg)
```
- Database error messages sent to client may reveal:
  - Schema information (table names, column names)
  - SQL query structure
  - Database constraint names
  - Internal implementation details

### 3. Broad Exception Catching
**Location:** `websocket.py:117`
```python
except Exception as ex:  # pylint: disable=W0703
```
- Catches all exceptions, may hide specific error types
- Makes debugging harder
- No differentiation between expected and unexpected errors

### 4. No Debug vs Production Distinction
- Same error verbosity in debug and production modes
- No environment-based error message filtering

## Requirements

### Must Have
- [ ] Standardized error response format
- [ ] Production-safe error messages (no schema leaks)
- [ ] More specific exception handling
- [ ] Debug vs production error verbosity
- [ ] Backward compatible changes

### Nice to Have
- [ ] Error codes documentation
- [ ] Custom exception hierarchy
- [ ] Error logging improvements
- [ ] Client-friendly error messages

## Implementation Plan

### 1. Create Custom Exception Classes

**File:** `src/blueshed/gust/exceptions.py` (new)
```python
"""Custom exception classes for Gust"""

class GustException(Exception):
    """Base exception for Gust"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class ValidationError(GustException):
    """Input validation failed"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

class AuthenticationError(GustException):
    """Authentication required or failed"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)

class AuthorizationError(GustException):
    """User not authorized for this action"""
    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, status_code=403)

class NotFoundError(GustException):
    """Resource not found"""
    def __init__(self, message: str = "Not found"):
        super().__init__(message, status_code=404)

class DatabaseError(GustException):
    """Database operation failed"""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, status_code=500)
        self.original_error = original_error
```

### 2. Add Error Sanitization

**File:** `src/blueshed/gust/utils.py` (add function)
```python
def sanitize_error_message(error: Exception, debug: bool = False) -> str:
    """
    Sanitize error messages for production use.

    In debug mode, return full error details.
    In production, return safe generic messages.
    """
    if debug:
        # Full details in debug mode
        return str(error)

    # Production mode - sanitize based on error type
    if isinstance(error, GustException):
        # Our custom exceptions are already safe
        return error.message

    # Database errors - never expose details
    if 'psycopg' in type(error).__module__:
        return "Database operation failed"

    # Generic errors - safe message
    return "An error occurred while processing your request"
```

### 3. Refactor WebSocket Error Handling

**File:** `websocket.py:109-131` (refactor)
```python
if error is None:
    try:
        log.debug('calling: %s %r, %r', handling, args, kwargs)
        result = await self.application.perform(
            self, handling, *args, **kwargs
        )
        if ref:
            log.debug('have result: %s', result)

    # Specific exception types first
    except ValidationError as ex:
        log.warning('%s: validation error: %s', method, ex.message)
        error = JsonRpcException(-32602, ex.message)

    except AuthenticationError as ex:
        log.warning('%s: auth error', method)
        self.close(401, 'Authentication required')
        return

    except DatabaseError as ex:
        log.error('%s: database error: %s', method, ex.original_error)
        safe_message = sanitize_error_message(
            ex.original_error,
            self.settings.get('debug', False)
        )
        error = JsonRpcException(-32603, safe_message)

    except Exception as ex:
        log.exception('%s: unexpected error', method)
        safe_message = sanitize_error_message(
            ex,
            self.settings.get('debug', False)
        )
        error = JsonRpcException(-32603, safe_message)

    finally:
        if method == 'ws_close':
            self.remove_client()
            ref = None
```

### 4. Update PostgreSQL RPC Handler

**File:** `postgres_rpc.py:140-154` (refactor)
```python
try:
    async with self.connection.cursor() as cur:
        await cur.execute(sql, params)
        result = await cur.fetchone()
    return result[0] if result else None

except psycopg.errors.ProgrammingError as e:
    # Syntax errors, missing functions, etc.
    await self.connection.rollback()
    log.error('PostgreSQL programming error: %s', e)
    raise ValidationError(f'Invalid function or parameters: {method}')

except psycopg.errors.DatabaseError as e:
    # General database errors
    await self.connection.rollback()
    log.error('PostgreSQL database error: %s', e)
    raise DatabaseError('Database operation failed', original_error=e)

except Exception as e:
    await self.connection.rollback()
    log.exception('Unexpected error in PostgreSQL RPC')
    raise
```

### 5. Add Error Response Tests

**File:** `src/tests/test_error_handling.py` (new)
```python
"""Test error handling and sanitization"""

import pytest
from blueshed.gust import Gust, web
from blueshed.gust.exceptions import ValidationError, DatabaseError

@web.post('/test-validation')
def validation_test(request):
    raise ValidationError("Invalid input: missing field 'name'")

@web.post('/test-database')
def database_test(request):
    # Simulate database error with sensitive info
    import psycopg
    try:
        raise psycopg.errors.ProgrammingError(
            "relation 'secret_user_table' does not exist"
        )
    except Exception as e:
        raise DatabaseError("Query failed", original_error=e)

@pytest.fixture(scope='module')
def app(web_context):
    return Gust(debug=False)  # Production mode

async def test_validation_error_message(http_server_client):
    """Validation errors should show specific message"""
    response = await http_server_client.fetch(
        '/test-validation',
        method='POST',
        body='',
        raise_error=False
    )
    assert response.code == 400
    assert "Invalid input" in response.body.decode()
    assert "name" in response.body.decode()

async def test_database_error_sanitized(http_server_client):
    """Database errors should be sanitized in production"""
    response = await http_server_client.fetch(
        '/test-database',
        method='POST',
        body='',
        raise_error=False
    )
    assert response.code == 500
    body = response.body.decode()
    # Should NOT contain sensitive schema info
    assert "secret_user_table" not in body
    assert "relation" not in body
    # Should contain generic message
    assert "Database operation failed" in body
```

### 6. Update Documentation

Add error handling guide to docs:
- Custom exception usage
- Error sanitization behavior
- Debug vs production modes
- Best practices for error handling

## Acceptance Criteria

- [ ] Custom exception classes defined and documented
- [ ] Error messages sanitized in production mode (debug=False)
- [ ] Specific exception handling in websocket.py
- [ ] PostgreSQL errors don't leak schema information
- [ ] Tests verify error sanitization works
- [ ] Backward compatible (existing code still works)
- [ ] Documentation includes error handling guide

## Testing Checklist

- [ ] Test custom exceptions in HTTP handlers
- [ ] Test custom exceptions in WebSocket handlers
- [ ] Test error sanitization in debug mode (shows details)
- [ ] Test error sanitization in production mode (hides details)
- [ ] Test database errors don't leak schema info
- [ ] Test JSON-RPC error format consistency
- [ ] Test backward compatibility with existing error handling

## Related Issues
- Code review finding #4: Error handling could be more specific
- Code review finding #7: Inconsistent error response format
- Security concern: Error messages may leak information

## Breaking Changes
None - all changes are backward compatible additions.

## Migration Guide
```python
# Old way (still works)
def my_handler(request):
    if not valid:
        raise Exception("Invalid")  # Generic error

# New way (recommended)
from blueshed.gust.exceptions import ValidationError

def my_handler(request):
    if not valid:
        raise ValidationError("Invalid: missing field 'name'")
```
