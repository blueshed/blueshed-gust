-- Test functions for PostgreSQL RPC testing

-- Simple function: add two numbers
CREATE OR REPLACE FUNCTION public.add(a INT, b INT)
RETURNS INT
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT a + b;
$$;

-- Function with named parameters
CREATE OR REPLACE FUNCTION public.multiply(x INT, y INT)
RETURNS INT
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT x * y;
$$;

-- Authenticated function: get user's data (user_id is first param)
CREATE OR REPLACE FUNCTION public.get_user_orders(user_id INT, year INT DEFAULT 2024)
RETURNS TABLE(order_id INT, amount DECIMAL)
LANGUAGE SQL
STABLE
AS $$
  SELECT
    user_id::INT as order_id,
    (amount)::DECIMAL as amount
  FROM (
    SELECT
      user_id,
      (user_id * 100 + year) as amount
  ) t
  WHERE user_id > 0;
$$;

-- Function that echoes back the user ID (useful for auth testing)
CREATE OR REPLACE FUNCTION public.get_current_user_id(user_id INT)
RETURNS INT
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT user_id;
$$;

-- Function with multiple parameters (for auth testing)
CREATE OR REPLACE FUNCTION public.create_order(
  user_id INT,
  product_name TEXT,
  quantity INT,
  price DECIMAL
)
RETURNS TABLE(order_id INT, user_id INT, total DECIMAL)
LANGUAGE SQL
STABLE
AS $$
  SELECT
    (user_id * 1000 + quantity)::INT as order_id,
    user_id,
    (quantity * price) as total;
$$;

-- Simple function returning text
CREATE OR REPLACE FUNCTION public.greet(name TEXT)
RETURNS TEXT
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT 'Hello, ' || name || '!';
$$;

-- Function returning JSON object
CREATE OR REPLACE FUNCTION public.get_user_profile(user_id INT)
RETURNS JSON
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT json_build_object(
    'id', user_id,
    'name', 'User ' || user_id,
    'email', 'user' || user_id || '@example.com',
    'created_at', NOW()::TEXT
  );
$$;

-- Test table for more complex scenarios
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO users (username, email) VALUES
  ('alice', 'alice@example.com'),
  ('bob', 'bob@example.com'),
  ('charlie', 'charlie@example.com')
ON CONFLICT (username) DO NOTHING;

-- Function that queries the users table
CREATE OR REPLACE FUNCTION public.get_all_users()
RETURNS TABLE(id INT, username TEXT, email TEXT)
LANGUAGE SQL
STABLE
AS $$
  SELECT id, username, email FROM users ORDER BY id;
$$;

-- Authenticated function to get user by ID
CREATE OR REPLACE FUNCTION public.get_user_by_id(user_id INT, requested_id INT)
RETURNS TABLE(id INT, username TEXT, email TEXT)
LANGUAGE SQL
STABLE
AS $$
  SELECT id, username, email
  FROM users
  WHERE id = requested_id
    AND requested_id = user_id;  -- Can only access own record
$$;
