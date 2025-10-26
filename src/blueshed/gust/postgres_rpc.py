"""PostgreSQL RPC handler for Gust - call stored functions via JSON-RPC

Example usage with JSON-RPC WebSocket:

    from blueshed.gust import Gust, web, PostgresRPC, AuthPostgresRPC
    from psycopg import AsyncConnection

    async def main():
        conn = await AsyncConnection.connect("postgresql://...")

        # Unauthenticated RPC - direct handler registration
        pg_rpc = PostgresRPC(conn)
        web.ws_json_rpc('/api', handler=pg_rpc)

        # Authenticated RPC - current user automatically injected as first parameter
        auth_rpc = AuthPostgresRPC(conn)
        web.ws_json_rpc('/api/auth', handler=auth_rpc)

        # Create app and run
        app = Gust(port=8080)
        await app._run_()

    # Client calls (from browser or WebSocket client):
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "get_orders",
        "params": [2024, "pending"]  // positional parameters OR
        "params": {"year": 2024, "status": "pending"}  // named parameters
    }

    // Response:
    {
        "jsonrpc": "2.0",
        "id": 1,
        "result": [...]  // or "error": {...}
    }
"""

import logging
from typing import Any, Dict, List, Optional, Union

from . import context

log = logging.getLogger(__name__)

# Global cache for PostgreSQL function signatures
# Maps function_name -> list of parameter names in order
_FUNCTION_SIGNATURE_CACHE: Dict[str, List[str]] = {}


class PostgresRPC:
    """
    Call PostgreSQL stored functions via JSON-RPC with automatic
    parameter marshalling from JSON-RPC format to PostgreSQL format.

    Supports both positional (array) and named (object) parameters.
    Caches function signatures to avoid repeated schema queries.
    """

    def __init__(
        self,
        connection,
        schema: str = 'public',
    ):
        """
        Initialize PostgreSQL RPC handler.

        Args:
            connection: psycopg AsyncConnection or AsyncConnectionPool.
                Must support async context managers and cursor operations.
            schema: PostgreSQL schema to search for functions (default: 'public')
        """
        self.connection = connection
        self.schema = schema

    async def call(
        self,
        method: str,
        params: Union[List, Dict, None] = None,
    ) -> Any:
        """
        Call a PostgreSQL stored function.

        When params is a dict (named parameters), the function signature is
        queried to determine the correct parameter order, then params are
        marshalled to positional arguments.

        When params is a list (positional parameters), they are used as-is.

        Args:
            method: PostgreSQL function name (must not start with '_')
            params: JSON-RPC params as list (positional) or dict (named),
                    or None for no parameters

        Returns:
            The first column of the first row returned by the function

        Raises:
            ValueError: If function name starts with '_' (private convention)
            ValueError: If function not found or parameters are invalid
            Exception: If PostgreSQL execution fails
        """
        # Security: reject private functions (starting with underscore)
        if method.startswith('_'):
            raise ValueError(f'Cannot call private function: {method}')

        # Normalize and validate params
        if params is None:
            params = []
        elif isinstance(params, dict):
            # Named parameters: need to look up function signature
            signature = await self._get_function_signature(method)
            if not signature:
                raise ValueError(f'Function not found: {method}')

            # Reorder params according to function signature
            positional_params = []
            for param_name in signature:
                if param_name not in params:
                    raise ValueError(
                        f'Missing required parameter: {param_name} '
                        f'for function {method}'
                    )
                positional_params.append(params[param_name])
            params = positional_params
        elif not isinstance(params, list):
            raise ValueError(
                'Params must be list (positional) or dict (named)'
            )

        # Build SQL: SELECT method(%s, %s, ...)
        # Note: psycopg3 uses %s placeholders, not $1, $2
        param_placeholders = ', '.join(['%s'] * len(params))
        sql = f'SELECT {self.schema}.{method}({param_placeholders})'

        log.debug('PostgreSQL RPC: %s with params %r', sql, params)

        # Execute function with error handling
        try:
            async with self.connection.cursor() as cur:
                await cur.execute(sql, params)
                result = await cur.fetchone()
            # Return first column of first row, or None
            return result[0] if result else None
        except Exception as e:
            # Rollback failed transaction to reset connection state
            try:
                await self.connection.rollback()
                log.info('Transaction rolled back after error')
            except Exception as rollback_err:
                log.error('Failed to rollback transaction: %s', rollback_err)
            # Re-raise the original error with details
            raise

    async def _get_function_signature(
        self, function_name: str
    ) -> Optional[List[str]]:
        """
        Get function input parameter names in order.

        Queries information_schema and caches the result to avoid
        repeated schema lookups.

        Args:
            function_name: Name of the PostgreSQL function

        Returns:
            List of parameter names in order, or empty list if function
            has no input parameters, or None if function not found
        """
        cache_key = f'{self.schema}.{function_name}'

        if cache_key in _FUNCTION_SIGNATURE_CACHE:
            return _FUNCTION_SIGNATURE_CACHE[cache_key]

        # Query information_schema for function signature
        async with self.connection.cursor() as cur:
            await cur.execute(
                """
                SELECT array_agg(p.parameter_name ORDER BY p.ordinal_position)::text[]
                FROM information_schema.parameters p
                JOIN information_schema.routines r
                  ON r.specific_schema = p.specific_schema
                  AND r.specific_name = p.specific_name
                WHERE r.routine_schema = %s
                  AND r.routine_name = %s
                  AND p.parameter_mode IN ('IN', 'INOUT')
                """,
                [self.schema, function_name],
            )

            result = await cur.fetchone()

        if not result or not result[0]:
            # Function not found or has no input parameters
            signature = []
        else:
            signature = list(result[0])

        # Cache result
        _FUNCTION_SIGNATURE_CACHE[cache_key] = signature

        log.debug(
            'Cached function signature: %s.%s -> %r',
            self.schema,
            function_name,
            signature,
        )

        return signature

    @classmethod
    def clear_cache(cls):
        """Clear the global function signature cache."""
        _FUNCTION_SIGNATURE_CACHE.clear()
        log.debug('Cleared PostgreSQL function signature cache')


class AuthPostgresRPC(PostgresRPC):
    """
    Authenticated PostgreSQL RPC handler that automatically injects
    the current user as the first parameter to all function calls.

    This is useful for:
    - Row-level security (functions filter by user)
    - Audit trails (functions can log who made the change)
    - Multi-tenant systems (functions can enforce tenant isolation)

    The current user is obtained from the request context and must be
    available via context.get_current_user().

    Example PostgreSQL function signature:
        CREATE FUNCTION get_user_orders(current_user_id INT, ...)
            RETURNS TABLE(...)
    """

    async def call(
        self,
        method: str,
        params: Union[List, Dict, None] = None,
        require_auth: bool = True,
    ) -> Any:
        """
        Call a PostgreSQL stored function with automatic user injection.

        The current user from the request context is automatically prepended
        as the first parameter.

        Args:
            method: PostgreSQL function name (must not start with '_')
            params: JSON-RPC params as list (positional) or dict (named),
                    or None for no parameters beyond the user
            require_auth: If True, raise ValueError if no current user.
                         If False, pass None as user if not authenticated.

        Returns:
            The first column of the first row returned by the function

        Raises:
            ValueError: If require_auth is True and no current user exists
            ValueError: If function name starts with '_' (private convention)
            Exception: If PostgreSQL execution fails
        """
        # Get current user from context
        current_user = context.get_current_user()

        if current_user is None and require_auth:
            raise ValueError('Authentication required: no current user')

        # Prepare params with user prepended
        if params is None:
            params_with_user = [current_user]
        elif isinstance(params, list):
            # Positional params: prepend user to the list
            params_with_user = [current_user] + params
        elif isinstance(params, dict):
            # Named params: prepend user and let parent handle reordering
            # The user will be first in the function signature
            params_with_user = {**params, '_user': current_user}
        else:
            raise ValueError(
                'Params must be list (positional) or dict (named)'
            )

        log.debug(
            'AuthPostgresRPC: calling %s with user=%s, params=%r',
            method,
            current_user,
            params,
        )

        # Call parent with user-injected params
        return await super().call(method, params_with_user)
