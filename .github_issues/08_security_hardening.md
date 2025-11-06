# Security Hardening Enhancements

**Labels:** `security`, `enhancement`, `low-priority`
**Milestone:** 1.0.0

## Overview
Add optional security features and document security best practices for production deployments.

## Current Security Posture
**Good:**
- ✅ Secure cookies for authentication
- ✅ Private function protection (PostgreSQL RPC)
- ✅ SQL injection protection via parameterized queries
- ✅ XSS prevention in JSON encoding
- ✅ Debug mode warnings
- ✅ Origin checking for WebSockets (production mode)

**Needs Improvement:**
- ⚠️ No rate limiting
- ⚠️ No request size limits documented
- ⚠️ CSRF protection not configured by default
- ⚠️ Error messages may leak information (addressed in #3)

## Proposed Enhancements

### 1. Rate Limiting Support
**File:** `src/blueshed/gust/rate_limit.py` (new)
```python
"""Rate limiting for HTTP and WebSocket"""

from functools import wraps
from time import time
from collections import defaultdict
from typing import Dict, Tuple

# Simple in-memory rate limiter (use Redis for production)
_rate_limit_store: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0))

def rate_limit(max_requests: int = 100, window: int = 60):
    """
    Rate limit decorator.

    Args:
        max_requests: Maximum requests allowed in window
        window: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            # Get client identifier
            client_id = request.request.remote_ip

            # Check rate limit
            count, reset_time = _rate_limit_store[client_id]
            current_time = time()

            if current_time > reset_time:
                # Reset window
                count = 0
                reset_time = current_time + window

            if count >= max_requests:
                # Rate limit exceeded
                raise HTTPError(
                    429,
                    reason=f"Rate limit exceeded. Try again in {int(reset_time - current_time)}s"
                )

            # Increment counter
            _rate_limit_store[client_id] = (count + 1, reset_time)

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@web.post('/api/sensitive', auth=True)
@rate_limit(max_requests=10, window=60)  # 10 requests per minute
def sensitive_operation(request):
    return {'status': 'ok'}
```

### 2. SECURITY.md Documentation
**File:** `SECURITY.md` (new)
```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.0.x   | :white_check_mark: |

## Reporting a Vulnerability

Please report security vulnerabilities to pete@blueshed.co.uk.
Do not open public GitHub issues for security vulnerabilities.

## Security Best Practices

### Production Configuration

1. **Never use debug mode in production**
   ```python
   app = Gust(debug=False)  # CRITICAL
   ```

2. **Use secure cookies**
   ```python
   app = Gust(
       cookie_secret="use-a-strong-random-secret-here",
       cookie_name="session"
   )
   ```

3. **Enable HTTPS only**
   ```python
   app.settings['cookie_secure'] = True
   app.settings['cookie_httponly'] = True
   ```

4. **Set up CSRF protection**
   ```python
   app.settings['xsrf_cookies'] = True
   ```

5. **Configure request size limits**
   ```python
   app.settings['max_body_size'] = 10 * 1024 * 1024  # 10MB
   ```

### WebSocket Security

1. **Always validate origin in production**
   ```python
   class MyWebsocket(Websocket):
       def check_origin(self, origin):
           parsed = urlparse(origin)
           return parsed.netloc in ['yourdomain.com', 'www.yourdomain.com']
   ```

2. **Use authentication for sensitive WebSocket endpoints**
   ```python
   @web.ws_json_rpc('/api', auth=True)
   def sensitive_rpc(user_id: int):
       # Only authenticated users can call this
       pass
   ```

### Database Security

1. **Never expose internal database functions**
   ```python
   # PostgreSQL function naming convention
   # Public: get_user_orders()
   # Private: _internal_update()  # Rejected by PostgresRPC
   ```

2. **Use row-level security**
   ```sql
   ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
   CREATE POLICY user_orders ON orders
       USING (user_id = current_setting('app.user_id')::int);
   ```

3. **Use AuthPostgresRPC for authenticated endpoints**
   ```python
   from blueshed.gust import AuthPostgresRPC

   auth_rpc = AuthPostgresRPC(conn)
   web.ws_json_rpc('/api/auth', handler=auth_rpc)
   ```

### Rate Limiting

```python
# Use rate limiting for public endpoints
@web.post('/api/public')
@rate_limit(max_requests=100, window=60)
def public_api(request):
    pass
```

### Input Validation

```python
# Always validate input
from blueshed.gust.exceptions import ValidationError

@web.post('/users')
def create_user(request):
    data = request.get_body()
    if not data.get('email'):
        raise ValidationError("Email required")
    # Process...
```

## Security Checklist for Deployment

- [ ] Debug mode disabled
- [ ] Secure cookie configuration
- [ ] HTTPS enforced
- [ ] CSRF protection enabled
- [ ] Rate limiting configured
- [ ] Request size limits set
- [ ] WebSocket origin checking enabled
- [ ] Database row-level security configured
- [ ] Error messages sanitized
- [ ] Logging configured (no sensitive data)
- [ ] Dependencies updated
- [ ] Security headers configured (CSP, HSTS, etc.)
```

### 3. Request Size Limits
Document in README and add to app initialization:
```python
class Gust(Application):
    def __init__(self, ..., max_body_size=10*1024*1024):
        # Default 10MB limit
        kwargs.setdefault('max_body_size', max_body_size)
        super().__init__(routes, **kwargs)
```

### 4. Security Headers
**File:** `src/blueshed/gust/security.py` (new)
```python
"""Security headers middleware"""

def add_security_headers(handler):
    """Add security headers to response"""
    # Only in production
    if not handler.settings.get('debug', False):
        handler.set_header('X-Content-Type-Options', 'nosniff')
        handler.set_header('X-Frame-Options', 'DENY')
        handler.set_header('X-XSS-Protection', '1; mode=block')
        handler.set_header(
            'Strict-Transport-Security',
            'max-age=31536000; includeSubDomains'
        )
        handler.set_header(
            'Content-Security-Policy',
            "default-src 'self'"
        )
```

## Implementation Checklist
- [ ] Create rate_limit.py with basic rate limiter
- [ ] Create SECURITY.md with best practices
- [ ] Add security headers helper
- [ ] Document CSRF setup in README
- [ ] Add security section to documentation
- [ ] Add rate limiting tests
- [ ] Create security checklist

## Acceptance Criteria
- [ ] SECURITY.md exists with comprehensive guide
- [ ] Optional rate limiting available
- [ ] CSRF configuration documented
- [ ] Security checklist for production
- [ ] Example secure configuration provided
- [ ] Tests for security features

## Notes
- Rate limiter should use Redis in production (document this)
- Consider integration with security scanning tools
- May want to add helmet-like security defaults

## Related
- Code review security concerns
- Required for production readiness
- Addresses security review findings

## Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Tornado Security Best Practices](https://www.tornadoweb.org/en/stable/guide/security.html)
- [WebSocket Security](https://owasp.org/www-community/vulnerabilities/WebSocket_Security)
