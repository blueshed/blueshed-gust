# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- BSD-3-Clause LICENSE file
- Comprehensive CLAUDE.md project guidance for AI-assisted development
- GitHub issue templates for planned improvements (9 issues)
- Code documentation comments (route sorting explanation)
- `JsonRpcErrorCode` class with named constants for JSON-RPC 2.0 error codes
- Documentation section in README with error code reference

### Changed
- WebSocket error handling now uses `JsonRpcErrorCode` constants instead of magic numbers
- METHOD_NOT_FOUND error now correctly uses error code -32601 (was incorrectly -32600)
- Error messages for method not found now include the method name

### Fixed
- pytest-cov dependency (was incorrectly named pytest-coverage)
- .gitignore now includes __pycache__, .pytest_cache, .ruff_cache, *.egg-info

## [0.0.26] - 2025-10-26

### Added
- PostgreSQL RPC handler (`PostgresRPC`) for direct database function calls via WebSocket
- Authenticated PostgreSQL RPC handler (`AuthPostgresRPC`) with automatic user injection
- Function signature caching for PostgreSQL RPC calls
- Comprehensive PostgreSQL RPC demo in `samples/postgres_rpc_demo/`
- Docker Compose setup for PostgreSQL testing
- Live integration tests for PostgreSQL RPC

### Fixed
- Database initialization now happens before WebSocket handler registration
- PostgreSQL RPC error handling improvements

### Changed
- Enhanced PostgreSQL RPC documentation and examples
- Improved WebSocket error messages for database operations
- Updated API documentation

## [0.0.25] - 2025-01-30

### Added
- JSON handling improvements in WebSocket communications

### Fixed
- Stream bug fixes for async generator handling

## [0.0.24] - 2025-01-11

### Added
- Streaming support enhancements (part 2)
- Experimental streaming features

### Fixed
- Stream reliability improvements

## Earlier Versions

Versions prior to 0.0.24 include:
- Task management improvements
- Context simplification
- Documentation enhancements
- Application argument handling improvements
- Online/offline handler hooks
- Icon and asset management

For detailed commit history, see: https://github.com/blueshed/blueshed-gust/commits/main

---

## Release Notes

### Version 0.0.26 Highlights

This release introduces powerful PostgreSQL integration, allowing you to call database stored functions directly via WebSocket JSON-RPC:

```python
from blueshed.gust import Gust, web, PostgresRPC
from psycopg import AsyncConnection

async def main():
    conn = await AsyncConnection.connect("postgresql://...")
    pg_rpc = PostgresRPC(conn)
    web.ws_json_rpc('/api', handler=pg_rpc)

    app = Gust(port=8080)
    await app._run_()
```

Clients can then call any PostgreSQL function:
```javascript
ws.send(JSON.stringify({
  jsonrpc: "2.0",
  id: 1,
  method: "get_user_orders",
  params: [2024, "pending"]
}));
```

See `samples/postgres_rpc_demo/` for a complete working example.

### Unreleased Changes

Recent improvements focused on code quality, documentation, and developer experience:
- Fixed critical pytest-cov dependency issue that prevented test coverage reporting
- Added LICENSE file for better open source compliance
- Created comprehensive issue templates for future improvements
- Enhanced project documentation for AI-assisted development

---

[Unreleased]: https://github.com/blueshed/blueshed-gust/compare/v0.0.26...HEAD
[0.0.26]: https://github.com/blueshed/blueshed-gust/commits/main
[0.0.25]: https://github.com/blueshed/blueshed-gust/commits/main
[0.0.24]: https://github.com/blueshed/blueshed-gust/commits/main
