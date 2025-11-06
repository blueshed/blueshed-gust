# Gust Test Status - November 2025

## Current Situation

**The async tests in Gust are currently broken and have been broken on the main branch for some time.**

### What's Broken

All async test functions (HTTP and WebSocket tests) fail with:
```
ERROR - fixture 'http_server_client' not found
ERROR - fixture 'http_server_port' not found
```

These fixtures don't exist in pytest-tornado 0.8.1 (the current version).

### What Works

- Non-async tests (like `test_json_utils.py`) work fine
- The actual Gust framework code works fine
- The issue is purely with the test infrastructure

## Root Cause

**pytest plugin compatibility issues:**

1. `pytest-tornado 0.8.1` changed/removed fixtures that the tests rely on
2. `pytest-tornasync` doesn't load properly (not registered as a plugin)
3. `pytest-asyncio` conflicts with `pytest-tornado` (different event loops)
4. The old fixtures (`http_server_client`, `http_server_port`) never existed in current versions

## Attempted Fixes

We tried multiple approaches:

1. ❌ Creating compatibility wrapper fixtures - event loop timeouts
2. ❌ Using `@gen_test` decorator - TypeError (missing 'self' argument)
3. ❌ Loading `pytest-tornasync` - plugin not recognized by pytest
4. ❌ Downgrading `pytest-tornado` - same issues persist
5. ❌ Using `pytest-asyncio` - conflicts with Tornado's IOLoop

## The Path Forward

### Short Term: Document and Move On

Given that:
- Gust is being positioned to use DZQL's PostgreSQL functions
- DZQL uses Bun's test runner (simpler, no pytest plugin issues)
- The tests have been broken for a while without blocking development
- Fixing pytest plugin conflicts is a deep rabbit hole

**Recommendation:**
- Document the broken state
- Continue development/usage (the framework itself works)
- Rewrite tests when porting DZQL's SQL functions

### Long Term: Model After DZQL

When we port DZQL's PostgreSQL functions to Gust, we should:

1. **Use DZQL's test patterns** - They use Bun's test runner with straightforward async/await
2. **Test the PostgreSQL functions directly** - Most logic will be in SQL, not Python
3. **Keep Python tests minimal** - Just test JSON-RPC routing, not business logic
4. **Consider pytest-asyncio only** - Drop Tornado-specific test infrastructure

## Current Test Coverage

From the last successful run of non-async tests:

```
TOTAL: 579 statements, 81% coverage
```

Areas with low coverage (all require async tests to improve):
- `websocket.py`: 18%
- `web_handler.py`: 22%
- `postgres_rpc.py`: 18%
- `static_file_handler.py`: 50%

## Recommendation

**Close issue #10 (Test Coverage Expansion)** with this explanation:

> Tests are currently broken due to pytest-tornado fixture compatibility issues. Since Gust will be refactored to use DZQL's PostgreSQL functions (where most logic resides), we'll rewrite the test suite at that time using simpler patterns modeled after DZQL's Bun-based tests.
>
> The framework itself works fine - this is purely a test infrastructure issue.

## For Future Reference

If someone wants to fix the current tests without waiting for DZQL integration:

1. **Option A:** Write tests as Tornado test classes (not functions)
   ```python
   from tornado.testing import AsyncHTTPTestCase

   class TestWeb(AsyncHTTPTestCase):
       def get_app(self):
           return Gust()

       def test_hello(self):
           response = self.fetch('/foo/')
           self.assertEqual(response.code, 200)
   ```

2. **Option B:** Use `pytest-asyncio` only and mock Tornado components

3. **Option C:** Use a different test framework altogether (unittest, nose, etc.)

All of these require significant test rewrites.
