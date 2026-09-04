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
import re
from typing import Any, Dict, List, Optional, Union

from . import context

log = logging.getLogger(__name__)

# Global cache for PostgreSQL function signatures
# Maps function_name -> list of parameter names in order
_FUNCTION_SIGNATURE_CACHE: Dict[str, List[str]] = {}

# Function and schema names are interpolated into SQL, so they must be
# plain identifiers. Anything else is rejected before touching the DB.
_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _check_identifier(kind: str, value: Any) -> str:
    """Return value if it is a safe SQL identifier, else raise ValueError"""
    if not isinstance(value, str) or not _IDENTIFIER.match(value):
        raise ValueError(f'Invalid {kind} name: {value!r}')
    return value


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
        self.schema = _check_identifier('schema', schema)

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
            ValueError: If function name is not a plain SQL identifier
            ValueError: If function not found or parameters are invalid
            Exception: If PostgreSQL execution fails
        """
        params = await self._marshal(method, params)
        return await self._execute(method, params)

    async def _marshal(
        self,
        method: str,
        params: Union[List, Dict, None],
        skip: int = 0,
    ) -> List:
        """
        Validate the method name and convert params to a positional list.

        Args:
            method: PostgreSQL function name
            params: list, dict or None as received from JSON-RPC
            skip: number of leading signature parameters that the caller
                  supplies itself (used by AuthPostgresRPC for the user);
                  client-supplied values for those names are ignored

        Returns:
            Positional parameter list covering signature[skip:]
        """
        # Security: the name is interpolated into SQL, so it must be a
        # plain identifier, and private functions are not callable.
        _check_identifier('function', method)
        if method.startswith('_'):
            raise ValueError(f'Cannot call private function: {method}')

        if params is None:
            return []
        if isinstance(params, list):
            return list(params)
        if not isinstance(params, dict):
            raise ValueError(
                'Params must be list (positional) or dict (named)'
            )

        # Named parameters: need to look up function signature
        signature = await self._get_function_signature(method)
        if not signature:
            raise ValueError(f'Function not found: {method}')

        # Reorder params according to function signature
        positional_params = []
        for param_name in signature[skip:]:
            if param_name not in params:
                raise ValueError(
                    f'Missing required parameter: {param_name} '
                    f'for function {method}'
                )
            positional_params.append(params[param_name])
        return positional_params

    async def _execute(self, method: str, params: List) -> Any:
        """Run SELECT schema.method(params...) and return the first column"""
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
        except Exception:
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
    available via context.get_current_user(). The first parameter of the
    called function is always the server-side user; a client can neither
    omit it nor supply its own value for it, whatever the parameter is
    named. With named params the client supplies the remaining parameters.

    Example PostgreSQL function signature:
        CREATE FUNCTION get_user_orders(current_user_id INT, ...)
            RETURNS TABLE(...)

    Args:
        connection: as for PostgresRPC
        schema: as for PostgresRPC
        user_field: when the current user is a dict (as it is when Gust
            stores a user object in the cookie), pass this field of it,
            e.g. 'id', instead of the whole dict. None passes the user
            value through unchanged.
    """

    def __init__(
        self,
        connection,
        schema: str = 'public',
        user_field: Optional[str] = None,
    ):
        super().__init__(connection, schema)
        self.user_field = user_field

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

        if self.user_field and isinstance(current_user, dict):
            current_user = current_user.get(self.user_field)

        # Named params are marshalled against signature[1:], so the user
        # always occupies the first slot and client values for it are ignored
        params = await self._marshal(method, params, skip=1)

        log.debug(
            'AuthPostgresRPC: calling %s with user=%s, params=%r',
            method,
            current_user,
            params,
        )

        return await self._execute(method, [current_user, *params])
