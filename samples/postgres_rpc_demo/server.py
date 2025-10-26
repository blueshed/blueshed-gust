#!/usr/bin/env python
"""
Gust WebSocket server with PostgresRPC endpoints

This server provides real PostgreSQL function calling via JSON-RPC over WebSocket.

Usage:
    # Terminal 1: Start PostgreSQL
    docker compose up -d

    # Terminal 2: Start this server
    python server.py

    # Terminal 3: Open browser
    open index.html
"""

import asyncio
import logging
import sys
from pathlib import Path

from psycopg import AsyncConnection

# Add src to path for local testing
sys.path.insert(0, '../../src')

from blueshed.gust import AuthPostgresRPC, Gust, PostgresRPC, web

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
log = logging.getLogger(__name__)

# Global connection
_conn = None
_pg_rpc = None
_auth_rpc = None


async def init_database():
    """Initialize database connection"""
    global _conn, _pg_rpc, _auth_rpc

    log.info('Connecting to PostgreSQL...')
    try:
        _conn = await AsyncConnection.connect(
            'postgresql://gust_user:gust_pass@localhost/gust_test'
        )
        _pg_rpc = PostgresRPC(_conn, schema='public')
        _auth_rpc = AuthPostgresRPC(_conn, schema='public')
        log.info('✅ Connected to PostgreSQL database')
    except Exception as e:
        log.error(f'❌ Failed to connect to PostgreSQL: {e}')
        log.error('Make sure docker compose is running: docker compose up -d')
        raise


async def cleanup_database():
    """Clean up database connection"""
    global _conn

    if _conn:
        await _conn.close()
        log.info('Database connection closed')


# HTTP endpoint to serve the HTML client
@web.get('/(.*)')
def serve_index(request):
    """Serve the HTML client"""
    html_file = Path(__file__).parent / 'index.html'
    if html_file.exists():
        return html_file.read_text()
    return '<h1>404 - index.html not found</h1>'


async def main():
    """Start the server"""
    log.info('Starting Gust WebSocket server...')

    # Initialize database
    await init_database()

    # Unauthenticated RPC endpoint - handler-based routing
    web.ws_json_rpc('/api', handler=_pg_rpc)

    # Authenticated RPC endpoint - handler-based routing
    web.ws_json_rpc('/api/auth', handler=_auth_rpc)

    # Create Gust app
    app = Gust(port=8080, debug=True)

    try:
        log.info('🚀 Server running on http://localhost:8080')
        log.info('📖 Open index.html in your browser')
        await app._run_()
    except KeyboardInterrupt:
        log.info('Shutting down...')
    finally:
        await cleanup_database()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        log.error(f'Fatal error: {e}')
        sys.exit(1)
