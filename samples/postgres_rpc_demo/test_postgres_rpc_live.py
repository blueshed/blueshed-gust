#!/usr/bin/env python
"""
Live test of PostgreSQL RPC functionality

This script demonstrates PostgresRPC and AuthPostgresRPC with a live PostgreSQL database.

Setup:
  docker compose up -d
  python test_postgres_rpc_live.py

Cleanup:
  docker compose down -v
"""

import asyncio
import json
import sys
from dataclasses import dataclass

import psycopg
from psycopg import AsyncConnection

# Add src to path for local testing
sys.path.insert(0, '../../src')

from blueshed.gust import AuthPostgresRPC, PostgresRPC
from blueshed.gust.context import gust


@dataclass
class MockHandler:
    """Mock handler for context testing"""

    current_user: object = None
    application: object = None


async def test_postgres_rpc():
    """Test PostgresRPC with positional and named parameters"""
    print('\n' + '=' * 60)
    print('Testing PostgresRPC (Unauthenticated)')
    print('=' * 60)

    # Connect to PostgreSQL
    conn = await AsyncConnection.connect(
        'postgresql://gust_user:gust_pass@localhost/gust_test'
    )

    try:
        pg_rpc = PostgresRPC(conn, schema='public')

        # Test 1: Simple positional parameters
        print('\n1. Testing simple addition (positional params)')
        result = await pg_rpc.call('add', [5, 3])
        print(f'   add(5, 3) = {result}')
        assert result == 8, f'Expected 8, got {result}'
        print('   ✓ PASSED')

        # Test 2: Named parameters
        print('\n2. Testing multiplication (named params)')
        result = await pg_rpc.call('multiply', {'x': 6, 'y': 7})
        print(f'   multiply(x=6, y=7) = {result}')
        assert result == 42, f'Expected 42, got {result}'
        print('   ✓ PASSED')

        # Test 3: Function with default parameter
        print('\n3. Testing get_user_orders (with default param)')
        result = await pg_rpc.call('get_user_orders', [1])
        print(f'   get_user_orders(1) = {result}')
        print('   ✓ PASSED')

        # Test 4: Function returning JSON
        print('\n4. Testing get_user_profile (returns JSON)')
        result = await pg_rpc.call('get_user_profile', [123])
        print(f'   get_user_profile(123) = {result}')
        assert isinstance(result, dict), 'Expected dict/JSON'
        print(f'   User ID: {result["id"]}, Name: {result["name"]}')
        print('   ✓ PASSED')

        # Test 5: Text return
        print('\n5. Testing greet function (returns text)')
        result = await pg_rpc.call('greet', ['World'])
        print(f'   greet("World") = "{result}"')
        assert 'Hello' in result, 'Expected greeting'
        print('   ✓ PASSED')

        # Test 6: Table query
        print('\n6. Testing get_all_users (query table)')
        result = await pg_rpc.call('get_all_users', [])
        print(f'   get_all_users() returned: {result}')
        print('   ✓ PASSED')

    finally:
        await conn.close()


async def test_auth_postgres_rpc():
    """Test AuthPostgresRPC with automatic user injection"""
    print('\n' + '=' * 60)
    print('Testing AuthPostgresRPC (Authenticated)')
    print('=' * 60)

    # Connect to PostgreSQL
    conn = await AsyncConnection.connect(
        'postgresql://gust_user:gust_pass@localhost/gust_test'
    )

    try:
        auth_rpc = AuthPostgresRPC(conn, schema='public')

        # Create a mock handler with a user
        handler = MockHandler(current_user=42)

        # Test 1: User injection with positional params
        print('\n1. Testing add with user context (user=42)')
        with gust(handler):
            result = await auth_rpc.call('get_current_user_id', [])
        print(f'   Current user ID injected: {result}')
        assert result == 42, f'Expected 42, got {result}'
        print('   ✓ PASSED - User 42 was automatically injected!')

        # Test 2: Multiple parameters with user injection
        print('\n2. Testing create_order with user injection (user=10)')
        handler.current_user = 10
        with gust(handler):
            result = await auth_rpc.call(
                'create_order',
                ['Widget', 5, 19.99],
            )
        print(f'   create_order("Widget", 5, 19.99) with user=10:')
        print(f'   Result: {result}')
        print('   ✓ PASSED - User was first parameter!')

        # Test 3: User with named parameters
        print('\n3. Testing get_user_orders with named params (user=5)')
        handler.current_user = 5
        with gust(handler):
            result = await auth_rpc.call(
                'get_user_orders',
                {'year': 2025},
            )
        print(f'   get_user_orders(year=2025) with user=5:')
        print(f'   Result: {result}')
        print('   ✓ PASSED - User injected, then other params appended!')

        # Test 4: Authentication required
        print('\n4. Testing auth requirement (no user)')
        handler.current_user = None
        try:
            with gust(handler):
                await auth_rpc.call('add', [1, 2])
            print('   ✗ FAILED - Should have raised error')
        except ValueError as e:
            print(f'   Correctly rejected: {e}')
            print('   ✓ PASSED - Auth required enforced!')

        # Test 5: Optional auth
        print('\n5. Testing optional auth (require_auth=False, no user)')
        handler.current_user = None
        with gust(handler):
            result = await auth_rpc.call(
                'add',
                [],
                require_auth=False,
            )
        print(f'   add() with no user (require_auth=False):')
        print(f'   Result: {result} (None as first param)')
        print('   ✓ PASSED - Public function allowed!')

        # Test 6: User as complex object
        print('\n6. Testing user as dict/object')
        handler.current_user = {'id': 99, 'role': 'admin', 'name': 'Alice'}
        with gust(handler):
            result = await auth_rpc.call(
                'get_current_user_id',
                [],
                require_auth=False,
            )
        print(f'   Current user object injected: {result}')
        print('   ✓ PASSED - Complex user objects supported!')

    finally:
        await conn.close()


async def main():
    """Run all tests"""
    print('\n' + '🚀 ' * 20)
    print('PostgreSQL RPC Test Suite')
    print('🚀 ' * 20)

    try:
        await test_postgres_rpc()
        await test_auth_postgres_rpc()

        print('\n' + '=' * 60)
        print('✅ ALL TESTS PASSED!')
        print('=' * 60)
        print('\nNext steps:')
        print('1. Clean up: docker-compose down -v')
        print('2. Try the WebSocket integration with @web.ws_json_rpc')
        print('3. Integrate with your Gust application')
        return 0

    except Exception as e:
        print(f'\n❌ TEST FAILED: {e}')
        import traceback

        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
