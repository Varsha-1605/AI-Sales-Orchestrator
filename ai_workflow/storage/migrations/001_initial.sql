CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    items JSONB NOT NULL,
    total NUMERIC(10, 2) NOT NULL,
    payment_method TEXT NOT NULL,
    gateway TEXT,
    transaction_id TEXT,
    store TEXT,
    status TEXT NOT NULL DEFAULT 'confirmed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS preferences (
    customer_id TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    order_id TEXT,
    rating INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
