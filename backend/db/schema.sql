
CREATE SCHEMA IF NOT EXISTS ecommerce;
CREATE SCHEMA IF NOT EXISTS support;
CREATE SCHEMA IF NOT EXISTS uploads;

CREATE TABLE IF NOT EXISTS ecommerce.categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS ecommerce.customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    location VARCHAR(255),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS ecommerce.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category_id INTEGER REFERENCES ecommerce.categories (id),
    price DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS ecommerce.orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES ecommerce.customers (id),
    order_date DATE NOT NULL,
    total_value DOUBLE PRECISION NOT NULL,
    status VARCHAR(50) DEFAULT 'completed',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS support.customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    contact_info VARCHAR(512),
    account_status VARCHAR(64),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS support.agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    email VARCHAR(255) UNIQUE
);

CREATE TABLE IF NOT EXISTS support.tickets (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES support.customers (id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'open',
    priority VARCHAR(50) DEFAULT 'medium',
    assigned_agent_id INTEGER REFERENCES support.agents (id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS support.ticket_notes (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES support.tickets (id),
    agent_id INTEGER REFERENCES support.agents (id),
    note TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS uploads.datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id VARCHAR(64) NOT NULL,
    file_name VARCHAR(512) NOT NULL,
    row_count INTEGER NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS uploads.dataset_rows (
    id SERIAL PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES uploads.datasets (id) ON DELETE CASCADE,
    row_index INTEGER NOT NULL,
    data JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON ecommerce.orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON ecommerce.orders (order_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer_date ON ecommerce.orders (customer_id, order_date DESC);
CREATE INDEX IF NOT EXISTS idx_products_category ON ecommerce.products (category_id);
CREATE INDEX IF NOT EXISTS idx_tickets_customer_id ON support.tickets (customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON support.tickets (status);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON support.tickets (priority);
CREATE INDEX IF NOT EXISTS idx_ticket_notes_ticket_id ON support.ticket_notes (ticket_id);
CREATE INDEX IF NOT EXISTS ix_uploads_datasets_conversation_id ON uploads.datasets (conversation_id);
CREATE INDEX IF NOT EXISTS ix_uploads_dataset_rows_dataset_id ON uploads.dataset_rows (dataset_id);
