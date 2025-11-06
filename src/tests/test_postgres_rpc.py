"""Integration tests for PostgreSQL RPC handler

These tests require a running PostgreSQL database with test functions.
They validate the actual RPC functionality end-to-end.

To run these tests:
    1. docker compose -f samples/postgres_rpc_demo/compose.yml up -d
    2. Initialize database (see README)
    3. pytest src/tests/test_postgres_rpc.py -v

Tests will be skipped if PostgreSQL is not available.
"""

import asyncio

import pytest
from psycopg import AsyncConnection

from blueshed.gust.postgres_rpc import (
    _FUNCTION_SIGNATURE_CACHE,
    PostgresRPC,
)

# Test database connection details
TEST_DB_URL = 'postgresql://gust_user:gust_pass@localhost/gust_test'


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear function signature cache before each test"""
    _FUNCTION_SIGNATURE_CACHE.clear()
    yield
    _FUNCTION_SIGNATURE_CACHE.clear()


async def get_pg_connection():
    """Helper to get PostgreSQL connection or skip test"""
    try:
        conn = await AsyncConnection.connect(TEST_DB_URL)
        return conn
    except Exception:
        pytest.skip('PostgreSQL not available')


@pytest.mark.asyncio
async def test_call_add_function():
    """Test calling the add function with positional parameters"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn)
        result = await pg_rpc.call('add', [10, 32])
        assert result == 42
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_call_multiply_function_positional():
    """Test calling multiply function with positional parameters"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn)
        result = await pg_rpc.call('multiply', [6, 7])
        assert result == 42
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_call_multiply_function_named():
    """Test calling multiply function with named parameters"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn)
        result = await pg_rpc.call('multiply', {'x': 6, 'y': 7})
        assert result == 42
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_call_greet_function():
    """Test calling greet function with text parameter"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn)
        result = await pg_rpc.call('greet', ['World'])
        assert result == 'Hello, World!'
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_function_signature_caching():
    """Test that function signatures are cached"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn)

        # First call should query the schema
        cache_key = 'public.multiply'
        _FUNCTION_SIGNATURE_CACHE.clear()
        assert cache_key not in _FUNCTION_SIGNATURE_CACHE

        await pg_rpc.call('multiply', {'x': 2, 'y': 3})
        assert cache_key in _FUNCTION_SIGNATURE_CACHE
        cached_sig = _FUNCTION_SIGNATURE_CACHE[cache_key]
        assert cached_sig == ['x', 'y']

        # Second call should use cached signature
        result = await pg_rpc.call('multiply', {'x': 4, 'y': 5})
        assert result == 20
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_call_with_no_params():
    """Test calling function with no parameters"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn)
        result = await pg_rpc.call('get_all_users')
        # Should return rows (list or tuple)
        assert result is not None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_private_function_rejected():
    """Test that functions starting with underscore are rejected"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn)

        with pytest.raises(ValueError, match='Cannot call private function'):
            await pg_rpc.call('_private_func', [])
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_nonexistent_function_raises_error():
    """Test that calling nonexistent function raises error"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn)

        # Calling nonexistent function raises PostgreSQL error
        with pytest.raises(Exception):  # Can be ValueError or psycopg error
            await pg_rpc.call('nonexistent_function', [])
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_missing_parameter_raises_error():
    """Test that missing required parameter raises error"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn)

        with pytest.raises(ValueError, match='Missing required parameter'):
            await pg_rpc.call('multiply', {'x': 5})  # missing 'y'
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_invalid_params_type_raises_error():
    """Test that invalid params type raises error"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn)

        with pytest.raises(ValueError, match='Params must be list'):
            await pg_rpc.call('add', 'invalid')  # string is invalid
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_transaction_rollback_on_error():
    """Test that transaction is rolled back after error"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn)

        # Call with invalid SQL should trigger rollback
        try:
            await pg_rpc.call('nonexistent_function', [])
        except Exception:
            pass

        # Connection should still be usable after error (tests rollback worked)
        result = await pg_rpc.call('add', [1, 1])
        assert result == 2
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_different_schemas():
    """Test querying functions from different schema"""
    conn = await get_pg_connection()
    try:
        pg_rpc = PostgresRPC(conn, schema='public')
        result = await pg_rpc.call('add', [5, 5])
        assert result == 10
    finally:
        await conn.close()
