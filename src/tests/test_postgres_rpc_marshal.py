"""Unit tests for PostgresRPC parameter marshalling and name validation.

These use a fake connection so they run without PostgreSQL.
"""

import pytest

from blueshed.gust.context import gust
from blueshed.gust.postgres_rpc import (
    _FUNCTION_SIGNATURE_CACHE,
    AuthPostgresRPC,
    PostgresRPC,
)


class FakeCursor:
    """records executed sql and answers with a canned row"""

    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, params=None):
        self.conn.calls.append((sql, params))

    async def fetchone(self):
        sql, _ = self.conn.calls[-1]
        if 'information_schema' in sql:
            return (self.conn.signature,)
        return (self.conn.result,)


class FakeConnection:
    """enough of psycopg AsyncConnection for PostgresRPC"""

    def __init__(self, signature=None, result='ok'):
        self.calls = []
        self.signature = signature
        self.result = result

    def cursor(self):
        return FakeCursor(self)

    async def rollback(self):
        self.calls.append(('ROLLBACK', None))


class Handler:
    """stands in for a websocket handler in the context"""

    def __init__(self, current_user):
        self.current_user = current_user


@pytest.fixture(autouse=True)
def clear_cache():
    _FUNCTION_SIGNATURE_CACHE.clear()
    yield
    _FUNCTION_SIGNATURE_CACHE.clear()


@pytest.mark.parametrize(
    'method',
    [
        'add(1,2) UNION SELECT usename FROM pg_shadow --',
        'add(1,2); DROP TABLE orders --',
        'pg_sleep(10) --',
        'add;',
        'my.func',
        'add name',
        '',
        None,
        42,
    ],
)
async def test_rejects_non_identifier_method(method):
    """anything that is not a plain identifier never reaches the database"""
    conn = FakeConnection()
    with pytest.raises(ValueError, match='Invalid function name'):
        await PostgresRPC(conn).call(method, [])
    assert conn.calls == []


async def test_rejects_private_method():
    conn = FakeConnection()
    with pytest.raises(ValueError, match='private'):
        await PostgresRPC(conn).call('_secret', [])
    assert conn.calls == []


def test_rejects_non_identifier_schema():
    with pytest.raises(ValueError, match='Invalid schema name'):
        PostgresRPC(FakeConnection(), schema='public; DROP TABLE x --')


async def test_positional_params_pass_through():
    conn = FakeConnection(result=42)
    result = await PostgresRPC(conn).call('add', [10, 32])
    assert result == 42
    assert conn.calls == [('SELECT public.add(%s, %s)', [10, 32])]


async def test_named_params_reordered_by_signature():
    conn = FakeConnection(signature=['user_id', 'year'])
    await PostgresRPC(conn).call(
        'get_user_orders', {'year': 2025, 'user_id': 7}
    )
    sql, params = conn.calls[-1]
    assert sql == 'SELECT public.get_user_orders(%s, %s)'
    assert params == [7, 2025]


async def test_auth_prepends_user_to_positional():
    conn = FakeConnection()
    with gust(Handler(current_user=42)):
        await AuthPostgresRPC(conn).call('create_order', ['Widget', 5])
    assert conn.calls[-1] == (
        'SELECT public.create_order(%s, %s, %s)',
        [42, 'Widget', 5],
    )


async def test_auth_named_params_fill_signature_after_user():
    """the user takes the first slot; the client supplies the rest"""
    conn = FakeConnection(signature=['user_id', 'year'])
    with gust(Handler(current_user=5)):
        await AuthPostgresRPC(conn).call('get_user_orders', {'year': 2025})
    assert conn.calls[-1] == (
        'SELECT public.get_user_orders(%s, %s)',
        [5, 2025],
    )


async def test_auth_named_params_ignore_client_user():
    """a client-supplied value for the user parameter is never used"""
    conn = FakeConnection(signature=['user_id', 'year'])
    with gust(Handler(current_user=5)):
        await AuthPostgresRPC(conn).call(
            'get_user_orders', {'user_id': 999, 'year': 2025}
        )
    assert conn.calls[-1][1] == [5, 2025]


async def test_auth_user_field_extracts_from_dict_user():
    conn = FakeConnection()
    user = {'id': 9, 'email': 'a@b.c'}
    with gust(Handler(current_user=user)):
        await AuthPostgresRPC(conn, user_field='id').call('whoami')
    assert conn.calls[-1] == ('SELECT public.whoami(%s)', [9])


async def test_auth_requires_user_by_default():
    conn = FakeConnection()
    with gust(Handler(current_user=None)):
        with pytest.raises(ValueError, match='Authentication required'):
            await AuthPostgresRPC(conn).call('add', [1, 2])
    assert conn.calls == []


async def test_auth_optional_passes_none():
    conn = FakeConnection()
    with gust(Handler(current_user=None)):
        await AuthPostgresRPC(conn).call('add', [1], require_auth=False)
    assert conn.calls[-1] == ('SELECT public.add(%s, %s)', [None, 1])
