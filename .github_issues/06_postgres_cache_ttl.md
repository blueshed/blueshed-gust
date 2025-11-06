# Add PostgreSQL Function Signature Cache TTL

**Labels:** `enhancement`, `postgres`, `medium-priority`
**Milestone:** 0.2.0

## Overview
Add optional TTL (Time To Live) for PostgreSQL function signature cache to handle runtime schema changes gracefully.

## Problem
**Location:** `postgres_rpc.py:48`
```python
_FUNCTION_SIGNATURE_CACHE: Dict[str, List[str]] = {}
```

The global cache never expires, causing issues when:
- Database functions are altered at runtime
- Schema is updated during deployment
- Development environments with frequent schema changes
- Multiple environments share cache state

## Current Workaround
Manual cache clearing:
```python
PostgresRPC.clear_cache()
```

## Proposed Solution

### 1. Add TTL Support
```python
from dataclasses import dataclass
from time import time
from typing import Optional

@dataclass
class CacheEntry:
    signature: List[str]
    timestamp: float

_FUNCTION_SIGNATURE_CACHE: Dict[str, CacheEntry] = {}

class PostgresRPC:
    def __init__(
        self,
        connection,
        schema: str = 'public',
        cache_ttl: Optional[int] = None,  # seconds, None = infinite
    ):
        self.connection = connection
        self.schema = schema
        self.cache_ttl = cache_ttl
```

### 2. Check TTL on Cache Access
```python
async def _get_function_signature(self, function_name: str) -> Optional[List[str]]:
    cache_key = f'{self.schema}.{function_name}'

    if cache_key in _FUNCTION_SIGNATURE_CACHE:
        entry = _FUNCTION_SIGNATURE_CACHE[cache_key]

        # Check if expired
        if self.cache_ttl is not None:
            age = time() - entry.timestamp
            if age > self.cache_ttl:
                log.debug('Cache entry expired: %s (age: %.1fs)', cache_key, age)
                del _FUNCTION_SIGNATURE_CACHE[cache_key]
            else:
                return entry.signature
        else:
            return entry.signature

    # Query database for signature
    # ... existing code ...

    # Cache with timestamp
    _FUNCTION_SIGNATURE_CACHE[cache_key] = CacheEntry(
        signature=signature,
        timestamp=time()
    )

    return signature
```

### 3. Add Configuration Examples
```python
# Infinite cache (current behavior)
rpc = PostgresRPC(conn)

# 1 hour cache
rpc = PostgresRPC(conn, cache_ttl=3600)

# 5 minute cache for development
rpc = PostgresRPC(conn, cache_ttl=300)

# No cache (always query)
rpc = PostgresRPC(conn, cache_ttl=0)
```

## Implementation Checklist
- [ ] Add CacheEntry dataclass
- [ ] Add cache_ttl parameter to __init__
- [ ] Implement TTL checking in _get_function_signature
- [ ] Add tests for cache expiration
- [ ] Add tests for cache hit/miss
- [ ] Update documentation
- [ ] Ensure backward compatibility

## Testing
```python
async def test_cache_ttl_expiration():
    """Test that cache entries expire after TTL"""
    rpc = PostgresRPC(conn, cache_ttl=1)  # 1 second TTL

    # First call - cache miss
    sig1 = await rpc._get_function_signature('test_func')

    # Second call - cache hit
    sig2 = await rpc._get_function_signature('test_func')
    assert sig1 == sig2

    # Wait for expiration
    await asyncio.sleep(1.5)

    # Third call - cache miss (expired)
    sig3 = await rpc._get_function_signature('test_func')
    # Should query database again

async def test_cache_infinite_ttl():
    """Test that None TTL means infinite cache"""
    rpc = PostgresRPC(conn, cache_ttl=None)

    sig1 = await rpc._get_function_signature('test_func')
    await asyncio.sleep(2)
    sig2 = await rpc._get_function_signature('test_func')

    # Should still be cached
    assert sig1 == sig2
```

## Acceptance Criteria
- [ ] Optional cache_ttl parameter added
- [ ] Cache entries expire after TTL
- [ ] Tests verify expiration behavior
- [ ] Documentation updated with examples
- [ ] Backward compatible (default: infinite cache)
- [ ] Performance not significantly impacted

## Performance Considerations
- TTL checking adds minimal overhead (timestamp comparison)
- Consider using monotonic clock for better accuracy
- Consider per-instance cache vs global cache

## Related
- Code review finding #5: Global cache without TTL
- Improves development workflow
- Better production deployment support

## Future Enhancements
- Per-function TTL configuration
- Cache statistics/metrics
- LRU eviction policy
- Cache size limits
