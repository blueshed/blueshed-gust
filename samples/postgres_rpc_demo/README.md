# PostgreSQL RPC Demo

Real end-to-end demonstration of `PostgresRPC` and `AuthPostgresRPC` with a live PostgreSQL database and interactive WebSocket client.

## Quick Start

### Terminal 1: Start PostgreSQL

```bash
cd samples/postgres_rpc_demo
docker compose up -d
```

This starts a PostgreSQL 16 container with:
- Database: `gust_test`
- User: `gust_user`
- Password: `gust_pass`
- Port: `5432` (on localhost)

### Terminal 2: Start the Gust Server

```bash
python server.py
```

Expected output:
```
INFO:__main__:Starting Gust WebSocket server...
INFO:__main__:Connecting to PostgreSQL...
INFO:__main__:✅ Connected to PostgreSQL database
INFO:__main__:🚀 Server running on http://localhost:8080
INFO:__main__:📖 Open index.html in your browser
```

### Terminal 3: Open the Web Client

Open `index.html` in your browser (or navigate to `http://localhost:8080`):

```bash
# macOS
open index.html

# Linux
xdg-open index.html

# Or just open in your browser manually
```

### 🎯 Try It Out!

You'll see an interactive UI with demos:
- **➕ Addition** - Simple math: `add(5, 3)`
- **✖️ Multiplication** - Named params: `multiply(x=6, y=7)`
- **👋 Greeting** - Text function: `greet("World")`
- **👤 User Profile** - JSON return: `get_user_profile(123)`
- **📦 Orders** - Table query: `get_user_orders(1, 2024)`
- **🔐 Authenticated** - User injection demo

Click buttons to see live WebSocket JSON-RPC calls and results!

### Cleanup

```bash
# Stop the server (Ctrl+C in Terminal 2)

# Stop PostgreSQL (Terminal 1)
docker compose down -v
```

The `-v` flag removes volumes to avoid filesystem pollution.

## Test Functions Available

### Basic Functions

```sql
add(a INT, b INT) -> INT
  Example: add(5, 3) -> 8

multiply(x INT, y INT) -> INT
  Example: multiply(6, 7) -> 42

greet(name TEXT) -> TEXT
  Example: greet('World') -> 'Hello, World!'
```

### Authenticated Functions (first param is user_id)

```sql
get_current_user_id(user_id INT) -> INT
  Returns the injected user_id

create_order(user_id INT, product_name TEXT, quantity INT, price DECIMAL)
  -> TABLE(order_id INT, user_id INT, total DECIMAL)

get_user_orders(user_id INT, year INT DEFAULT 2024)
  -> TABLE(order_id INT, amount DECIMAL)

get_user_by_id(user_id INT, requested_id INT)
  -> TABLE(id INT, username TEXT, email TEXT)
```

### Complex Return Types

```sql
get_user_profile(user_id INT) -> JSON
  Returns user profile as JSON object

get_all_users() -> TABLE(id INT, username TEXT, email TEXT)
  Returns all users from users table
```

## Integration with Gust

### WebSocket JSON-RPC Endpoint

```python
from blueshed.gust import Gust, web, PostgresRPC, AuthPostgresRPC
import psycopg

pool = psycopg.AsyncConnectionPool(conninfo="postgresql://gust_user:gust_pass@localhost/gust_test")

# Unauthenticated endpoint
pg_rpc = PostgresRPC(pool)

@web.ws_json_rpc('/api')
async def db_query(method: str, params=None):
    return await pg_rpc.call(method, params)

# Authenticated endpoint - user automatically injected
auth_rpc = AuthPostgresRPC(pool)

@web.ws_json_rpc('/api/auth')
async def db_query_auth(method: str, params=None):
    return await auth_rpc.call(method, params)
```

### Client Usage

```javascript
const ws = new WebSocket('ws://localhost:8080/api');

// Positional parameters
ws.send(JSON.stringify({
  jsonrpc: "2.0",
  id: 1,
  method: "add",
  params: [5, 3]
}));

// Named parameters
ws.send(JSON.stringify({
  jsonrpc: "2.0",
  id: 2,
  method: "multiply",
  params: { x: 6, y: 7 }
}));

// Response
ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log(response.result);  // 8 or 42
};
```

## Files

- **docker-compose.yml** - PostgreSQL 16 container configuration
- **test_db_init.sql** - SQL initialization script with test functions
- **test_postgres_rpc_live.py** - Live test script
- **README.md** - This file

## Troubleshooting

### Database won't connect

```bash
# Check if postgres container is running
docker ps | grep gust_postgres_test

# Check postgres logs
docker-compose logs postgres

# Wait longer for initialization
sleep 5
python test_postgres_rpc_live.py
```

### Connection refused

Make sure port 5432 is available:

```bash
docker-compose ps
docker-compose logs
```

### Test script fails with "module not found"

Make sure you're running from the samples directory:

```bash
cd samples/postgres_rpc_demo
python test_postgres_rpc_live.py
```

### Cleanup doesn't remove volume

```bash
docker-compose down -v
```

## Next Steps

1. ✅ Run this demo to verify PostgresRPC works
2. ✅ Create your own PostgreSQL functions
3. ✅ Integrate with your Gust application
4. ✅ Use with `@web.ws_json_rpc()` decorators
5. ✅ Deploy to production

## Features Demonstrated

- ✅ Positional parameters (arrays)
- ✅ Named parameters (objects) with automatic reordering
- ✅ User injection with AuthPostgresRPC
- ✅ Authentication enforcement
- ✅ Optional authentication (require_auth=False)
- ✅ Complex user objects
- ✅ Various return types (int, text, JSON, tables)
- ✅ Function signature caching
- ✅ Private function blocking (functions starting with `_`)
