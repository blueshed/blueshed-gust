# Expand Test Coverage to 90%+

**Labels:** `testing`, `quality`, `low-priority`
**Milestone:** 1.0.0

## Overview
Increase test coverage to 90%+ and add tests for edge cases, error conditions, and concurrent scenarios.

## Current State
- Test coverage metrics not visible (requires pytest-cov fix first)
- Good coverage of happy paths
- Limited error case testing
- No load/performance tests
- Missing edge case tests

## Coverage Gaps Identified

### 1. Edge Cases
- [ ] Very large payloads (>1MB)
- [ ] Concurrent WebSocket connections (100+)
- [ ] Connection drops during streaming
- [ ] Malformed JSON payloads
- [ ] Unicode/emoji in messages
- [ ] Empty request bodies
- [ ] Missing required fields
- [ ] SQL injection attempts in PostgreSQL RPC

### 2. Error Conditions
- [ ] Network timeouts
- [ ] Database connection failures
- [ ] Out of memory conditions
- [ ] Invalid authentication tokens
- [ ] Expired sessions
- [ ] Race conditions in WebSocket handlers

### 3. Concurrency
- [ ] Multiple simultaneous requests
- [ ] WebSocket broadcast to 1000+ clients
- [ ] Streaming while clients disconnect
- [ ] Thread pool exhaustion

### 4. Uncovered Code Paths
Need to identify after enabling pytest-cov:
```bash
pytest --cov=blueshed.gust --cov-report=html
# Opens htmlcov/index.html to see uncovered lines
```

## Implementation Plan

### Phase 1: Enable Coverage Reporting
```bash
# After pytest-cov fix
pytest --cov=blueshed.gust --cov-report=term-missing
```

### Phase 2: Add Edge Case Tests
**File:** `src/tests/test_edge_cases.py` (new)
```python
async def test_large_payload(http_server_client):
    """Test handling of large request bodies"""
    large_data = {'data': 'x' * 1_000_000}  # 1MB
    response = await http_server_client.fetch(
        '/echo',
        method='POST',
        body=json.dumps(large_data)
    )
    assert response.code == 200

async def test_malformed_json(http_server_client):
    """Test malformed JSON handling"""
    response = await http_server_client.fetch(
        '/api',
        method='POST',
        body='{invalid json',
        raise_error=False
    )
    assert response.code == 400

async def test_unicode_in_websocket(ws_client):
    """Test Unicode/emoji in WebSocket messages"""
    client = await ws_client
    message = {'text': '你好 🎉 مرحبا'}
    await client.write_message(json.dumps(message))
    response = await client.read_message()
    assert '🎉' in response
```

### Phase 3: Add Concurrency Tests
**File:** `src/tests/test_concurrency.py` (new)
```python
async def test_concurrent_websocket_connections():
    """Test 100 concurrent WebSocket connections"""
    clients = []
    for i in range(100):
        client = await websocket_connect(f'ws://localhost:{port}/ws')
        clients.append(client)

    # Send messages from all clients
    for i, client in enumerate(clients):
        await client.write_message(f'Message {i}')

    # Verify all received responses
    for client in clients:
        response = await client.read_message()
        assert response is not None

    # Cleanup
    for client in clients:
        client.close()

async def test_broadcast_to_many_clients():
    """Test broadcast to 1000+ clients"""
    # ... implementation
```

### Phase 4: Add Property-Based Tests
Use Hypothesis for property-based testing:
```python
from hypothesis import given
from hypothesis import strategies as st

@given(st.integers(), st.integers())
async def test_add_commutative(a, b):
    """Addition should be commutative"""
    result1 = await call_rpc('add', [a, b])
    result2 = await call_rpc('add', [b, a])
    assert result1 == result2

@given(st.text(), st.text())
async def test_string_handling(s1, s2):
    """Test arbitrary string inputs"""
    result = await call_rpc('concat', [s1, s2])
    assert result == s1 + s2
```

### Phase 5: Set Coverage Threshold
**File:** `pyproject.toml`
```toml
[tool.coverage.report]
fail_under = 90
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

## Testing Tools

### Required Packages
```toml
[dependency-groups]
dev = [
    # ... existing ...
    "hypothesis>=6.0",      # Property-based testing
    "pytest-asyncio",       # Async test support
    "pytest-benchmark",     # Performance benchmarks
    "pytest-timeout",       # Test timeouts
]
```

### Coverage Commands
```bash
# Run with coverage
pytest --cov=blueshed.gust --cov-report=term-missing

# Generate HTML report
pytest --cov=blueshed.gust --cov-report=html

# Check coverage threshold
pytest --cov=blueshed.gust --cov-fail-under=90
```

## Performance/Load Tests
**File:** `src/tests/test_performance.py` (new)
```python
import pytest

@pytest.mark.benchmark
def test_json_encoding_performance(benchmark):
    """Benchmark JSON encoding"""
    data = {'key': 'value' * 100}
    result = benchmark(json_utils.dumps, data)
    assert result

@pytest.mark.benchmark
async def test_websocket_throughput():
    """Measure WebSocket message throughput"""
    client = await ws_client
    start = time.time()
    for i in range(1000):
        await client.write_message(f'Message {i}')
        await client.read_message()
    duration = time.time() - start
    throughput = 1000 / duration
    print(f'Throughput: {throughput:.1f} msg/sec')
    assert throughput > 100  # Minimum 100 msg/sec
```

## Acceptance Criteria
- [ ] Test coverage ≥ 90%
- [ ] All edge cases covered
- [ ] Concurrency tests pass
- [ ] Property-based tests added
- [ ] Performance benchmarks established
- [ ] Coverage threshold enforced in CI
- [ ] HTML coverage reports generated

## Related
- Code review testing gaps
- Required for 1.0.0 release
- Improves confidence in releases

## Resources
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Hypothesis documentation](https://hypothesis.readthedocs.io/)
- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)
