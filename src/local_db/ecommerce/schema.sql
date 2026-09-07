-- E-commerce SQLite schema for local analytics and RAG evaluation samples.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    brand TEXT NOT NULL,
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    cost_price REAL NOT NULL CHECK (cost_price >= 0),
    stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories (category_id)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'US',
    signup_date TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    order_number TEXT NOT NULL UNIQUE,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'ordered',
            'cancelled',
            'shipped',
            'delivered'
        )
    ),
    shipping_amount REAL NOT NULL DEFAULT 0 CHECK (shipping_amount >= 0),
    tax_amount REAL NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
    discount_amount REAL NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    total_amount REAL NOT NULL CHECK (total_amount >= 0),
    payment_method TEXT NOT NULL CHECK (
        payment_method IN (
            'credit_card',
            'debit_card',
            'paypal',
            'apple_pay',
            'gift_card'
        )
    ),
    shipping_city TEXT NOT NULL,
    shipping_state TEXT NOT NULL,
    shipping_country TEXT NOT NULL DEFAULT 'US',
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    line_total REAL NOT NULL CHECK (line_total >= 0),
    FOREIGN KEY (order_id) REFERENCES orders (order_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

-- Daily product engagement for conversion-rate analysis.
-- click_count and time_spent_seconds are intentionally correlated with order demand.
CREATE TABLE IF NOT EXISTS product_engagement (
    engagement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    engagement_date TEXT NOT NULL,
    click_count INTEGER NOT NULL CHECK (click_count >= 0),
    view_sessions INTEGER NOT NULL CHECK (view_sessions >= 0),
    time_spent_seconds INTEGER NOT NULL CHECK (time_spent_seconds >= 0),
    UNIQUE (product_id, engagement_date),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products (brand);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders (order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);
CREATE INDEX IF NOT EXISTS idx_product_engagement_product_id
    ON product_engagement (product_id);
CREATE INDEX IF NOT EXISTS idx_product_engagement_date
    ON product_engagement (engagement_date);
CREATE INDEX IF NOT EXISTS idx_product_engagement_product_date
    ON product_engagement (product_id, engagement_date);
