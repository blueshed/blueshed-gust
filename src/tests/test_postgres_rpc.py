"""Tests for PostgreSQL RPC handler"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blueshed.gust import context
from blueshed.gust.postgres_rpc import (
    AuthPostgresRPC,
    PostgresRPC,
    _FUNCTION_SIGNATURE_CACHE,
)


class MockCursor:
    """Mock psycopg cursor for testing"""

    def __init__(self):
        self.executed_sql = None
        self.executed_params = None
        self.fetch_result = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def execute(self, sql, params=None):
        self.executed_sql = sql
        self.executed_params = params

    async def fetchone(self):
        return self.fetch_result


class MockConnection:
    """Mock psycopg async connection for testing"""

    def __init__(self):
        self.cursor_instance = MockCursor()

    def cursor(self):
        return self.cursor_instance


@pytest.fixture
def mock_connection():
    """Provide a mock PostgreSQL connection"""
    return MockConnection()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear function signature cache before each test"""
    _FUNCTION_SIGNATURE_CACHE.clear()
    yield
    _FUNCTION_SIGNATURE_CACHE.clear()


async def test_call_with_array_params(mock_connection):
    """Test calling function with positional (array) parameters"""
    pg_rpc = PostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = (42,)

    result = await pg_rpc.call('add', [10, 32])

    assert result == 42
    assert mock_connection.cursor_instance.executed_sql == (
        'SELECT public.add(%s, %s)'
    )
    assert mock_connection.cursor_instance.executed_params == [10, 32]


async def test_call_with_no_params(mock_connection):
    """Test calling function with no parameters"""
    pg_rpc = PostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = ('hello',)

    result = await pg_rpc.call('greeting')

    assert result == 'hello'
    assert mock_connection.cursor_instance.executed_sql == (
        'SELECT public.greeting()'
    )
    assert mock_connection.cursor_instance.executed_params == []


async def test_call_returns_none_when_no_result(mock_connection):
    """Test that None is returned when function returns no rows"""
    pg_rpc = PostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = None

    result = await pg_rpc.call('get_something', [123])

    assert result is None


async def test_call_with_dict_params(mock_connection):
    """Test calling function with named (dict) parameters"""
    pg_rpc = PostgresRPC(mock_connection)

    # First call: queries function signature
    mock_connection.cursor_instance.fetch_result = (
        ['user_id', 'order_count'],
    )
    _ = await pg_rpc._get_function_signature('get_user_orders')

    # Second call: uses cached signature, marshals params
    mock_connection.cursor_instance.fetch_result = (['order1', 'order2'],)

    result = await pg_rpc.call(
        'get_user_orders',
        {'user_id': 123, 'order_count': 10},
    )

    assert result == ['order1', 'order2']
    # Params should be in order: user_id, then order_count
    assert mock_connection.cursor_instance.executed_params == [123, 10]


async def test_call_with_dict_params_wrong_order(mock_connection):
    """Test that dict params are reordered correctly"""
    pg_rpc = PostgresRPC(mock_connection)

    # Cache signature
    mock_connection.cursor_instance.fetch_result = (
        ['first', 'second', 'third'],
    )
    _ = await pg_rpc._get_function_signature('my_function')

    # Call with dict params in different order
    mock_connection.cursor_instance.fetch_result = ('result',)

    await pg_rpc.call(
        'my_function',
        {'third': 3, 'first': 1, 'second': 2},
    )

    # Params should be reordered to: first, second, third
    assert mock_connection.cursor_instance.executed_params == [1, 2, 3]


async def test_call_rejects_private_functions(mock_connection):
    """Test that functions starting with _ are rejected"""
    pg_rpc = PostgresRPC(mock_connection)

    with pytest.raises(ValueError, match='Cannot call private function'):
        await pg_rpc.call('_private_func', [])


async def test_call_with_missing_dict_param(mock_connection):
    """Test that missing required parameters raise ValueError"""
    pg_rpc = PostgresRPC(mock_connection)

    # Cache signature with required params
    mock_connection.cursor_instance.fetch_result = (['user_id', 'limit'],)
    _ = await pg_rpc._get_function_signature('get_users')

    # Try to call without required param
    with pytest.raises(ValueError, match='Missing required parameter'):
        await pg_rpc.call('get_users', {'user_id': 123})


async def test_call_with_invalid_params_type(mock_connection):
    """Test that invalid params type raises ValueError"""
    pg_rpc = PostgresRPC(mock_connection)

    with pytest.raises(
        ValueError, match='Params must be list .* or dict .*'
    ):
        await pg_rpc.call('some_func', 'invalid')


async def test_call_with_none_params(mock_connection):
    """Test that None params are treated as empty list"""
    pg_rpc = PostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = ('result',)

    await pg_rpc.call('no_args_func', None)

    assert mock_connection.cursor_instance.executed_sql == (
        'SELECT public.no_args_func()'
    )
    assert mock_connection.cursor_instance.executed_params == []


async def test_get_function_signature(mock_connection):
    """Test querying function signature"""
    pg_rpc = PostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = (
        ['param1', 'param2', 'param3'],
    )

    sig = await pg_rpc._get_function_signature('my_func')

    assert sig == ['param1', 'param2', 'param3']
    assert 'public.my_func' in _FUNCTION_SIGNATURE_CACHE


async def test_get_function_signature_caching(mock_connection):
    """Test that function signature is cached"""
    pg_rpc = PostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = (['id', 'name'],)

    # First call: queries database
    sig1 = await pg_rpc._get_function_signature('users_table')
    assert mock_connection.cursor_instance.executed_sql is not None
    original_sql = mock_connection.cursor_instance.executed_sql

    # Reset the executed_sql to verify it's not called again
    mock_connection.cursor_instance.executed_sql = None

    # Second call: should use cache
    sig2 = await pg_rpc._get_function_signature('users_table')

    assert sig1 == sig2
    assert mock_connection.cursor_instance.executed_sql is None


async def test_get_function_signature_not_found(mock_connection):
    """Test that non-existent function returns empty list"""
    pg_rpc = PostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = (None,)

    sig = await pg_rpc._get_function_signature('nonexistent_func')

    assert sig == []


async def test_custom_schema(mock_connection):
    """Test using custom schema"""
    pg_rpc = PostgresRPC(mock_connection, schema='myschema')
    mock_connection.cursor_instance.fetch_result = (42,)

    await pg_rpc.call('add', [1, 2])

    assert mock_connection.cursor_instance.executed_sql == (
        'SELECT myschema.add(%s, %s)'
    )


async def test_custom_schema_in_signature_cache_key(mock_connection):
    """Test that different schemas don't share cache"""
    pg_rpc1 = PostgresRPC(mock_connection, schema='schema1')
    pg_rpc2 = PostgresRPC(mock_connection, schema='schema2')

    mock_connection.cursor_instance.fetch_result = (['x'],)
    sig1 = await pg_rpc1._get_function_signature('func')

    mock_connection.cursor_instance.fetch_result = (['y'],)
    sig2 = await pg_rpc2._get_function_signature('func')

    # Both should be cached with different keys
    assert _FUNCTION_SIGNATURE_CACHE['schema1.func'] == ['x']
    assert _FUNCTION_SIGNATURE_CACHE['schema2.func'] == ['y']
    assert sig1 != sig2


def test_clear_cache():
    """Test clearing the global function signature cache"""
    _FUNCTION_SIGNATURE_CACHE['test.func'] = ['param1']
    assert len(_FUNCTION_SIGNATURE_CACHE) > 0

    PostgresRPC.clear_cache()

    assert len(_FUNCTION_SIGNATURE_CACHE) == 0


async def test_sql_injection_prevention_function_name(mock_connection):
    """Test that function names starting with _ are blocked"""
    pg_rpc = PostgresRPC(mock_connection)

    # These should all be rejected
    for name in ['_private', '__internal', '_']:
        with pytest.raises(ValueError):
            await pg_rpc.call(name, [])


async def test_call_with_various_data_types(mock_connection):
    """Test calling with different parameter data types"""
    pg_rpc = PostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = ('result',)

    params = [123, 'hello', 3.14, True, None]

    await pg_rpc.call('process', params)

    assert mock_connection.cursor_instance.executed_params == params


async def test_integration_positional_to_jsonrpc_format(mock_connection):
    """Test typical JSON-RPC usage pattern with positional params"""
    pg_rpc = PostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = ({'id': 1, 'name': 'Alice'},)

    # Simulate JSON-RPC call: method with array params
    jsonrpc_method = 'get_user'
    jsonrpc_params = [1]  # positional: user_id

    result = await pg_rpc.call(jsonrpc_method, jsonrpc_params)

    assert result == {'id': 1, 'name': 'Alice'}


async def test_integration_named_to_jsonrpc_format(mock_connection):
    """Test typical JSON-RPC usage pattern with named params"""
    pg_rpc = PostgresRPC(mock_connection)

    # Cache the function signature
    mock_connection.cursor_instance.fetch_result = (['user_id', 'start_date'],)
    _ = await pg_rpc._get_function_signature('get_user_orders')

    # Simulate JSON-RPC call: method with object params
    mock_connection.cursor_instance.fetch_result = ([],)

    result = await pg_rpc.call(
        'get_user_orders',
        {'user_id': 123, 'start_date': '2024-01-01'},
    )

    # Verify params were marshalled correctly
    assert mock_connection.cursor_instance.executed_params == [
        123,
        '2024-01-01',
    ]


# Tests for AuthPostgresRPC


class MockHandler:
    """Mock WebSocket/HTTP handler for testing"""

    def __init__(self, current_user=None):
        self.current_user = current_user


async def test_auth_rpc_with_array_params(mock_connection):
    """Test authenticated RPC with positional parameters"""
    auth_rpc = AuthPostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = (42,)

    with patch.object(context, 'get_current_user', return_value=99):
        result = await auth_rpc.call('process_data', [10, 32])

    assert result == 42
    # User should be prepended: [99, 10, 32]
    assert mock_connection.cursor_instance.executed_params == [99, 10, 32]


async def test_auth_rpc_with_no_additional_params(mock_connection):
    """Test authenticated RPC with only user, no additional params"""
    auth_rpc = AuthPostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = ('result',)

    with patch.object(context, 'get_current_user', return_value=123):
        result = await auth_rpc.call('get_user_profile')

    assert result == 'result'
    # Only user should be passed
    assert mock_connection.cursor_instance.executed_params == [123]


async def test_auth_rpc_requires_auth_by_default(mock_connection):
    """Test that auth RPC raises error when user not authenticated"""
    auth_rpc = AuthPostgresRPC(mock_connection)

    with patch.object(context, 'get_current_user', return_value=None):
        with pytest.raises(ValueError, match='Authentication required'):
            await auth_rpc.call('get_user_profile')


async def test_auth_rpc_allows_no_auth_when_require_auth_false(
    mock_connection,
):
    """Test that auth RPC allows no user when require_auth=False"""
    auth_rpc = AuthPostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = ('result',)

    with patch.object(context, 'get_current_user', return_value=None):
        result = await auth_rpc.call(
            'public_data',
            require_auth=False,
        )

    assert result == 'result'
    # None (no user) should be passed
    assert mock_connection.cursor_instance.executed_params == [None]


async def test_auth_rpc_with_user_id_string(mock_connection):
    """Test authenticated RPC with different user types (e.g., UUID string)"""
    auth_rpc = AuthPostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = ('data',)

    user_uuid = '550e8400-e29b-41d4-a716-446655440000'

    with patch.object(context, 'get_current_user', return_value=user_uuid):
        result = await auth_rpc.call('get_data', [1, 2])

    assert result == 'data'
    # User UUID should be prepended
    assert mock_connection.cursor_instance.executed_params == [user_uuid, 1, 2]


async def test_auth_rpc_with_user_dict(mock_connection):
    """Test authenticated RPC with user as dict/object"""
    auth_rpc = AuthPostgresRPC(mock_connection)
    mock_connection.cursor_instance.fetch_result = ('result',)

    user_obj = {'id': 123, 'name': 'Alice', 'role': 'admin'}

    with patch.object(context, 'get_current_user', return_value=user_obj):
        result = await auth_rpc.call('process', [])

    assert result == 'result'
    # Full user object should be passed
    assert mock_connection.cursor_instance.executed_params == [user_obj]


async def test_auth_rpc_still_blocks_private_functions(mock_connection):
    """Test that auth RPC still respects private function blocking"""
    auth_rpc = AuthPostgresRPC(mock_connection)

    with patch.object(context, 'get_current_user', return_value=123):
        with pytest.raises(ValueError, match='Cannot call private function'):
            await auth_rpc.call('_internal_func', [])


async def test_auth_rpc_with_custom_schema(mock_connection):
    """Test authenticated RPC with custom schema"""
    auth_rpc = AuthPostgresRPC(mock_connection, schema='private')
    mock_connection.cursor_instance.fetch_result = (42,)

    with patch.object(context, 'get_current_user', return_value=99):
        await auth_rpc.call('calculate', [5, 7])

    # Should use custom schema
    assert mock_connection.cursor_instance.executed_sql == (
        'SELECT private.calculate(%s, %s, %s)'
    )
    # User 99 should be first param, then 5, then 7
    assert mock_connection.cursor_instance.executed_params == [99, 5, 7]
