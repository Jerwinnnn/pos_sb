-- POS System Schema (SQLite)
-- Sabbis Burger — Filipino Burger Machine

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    icon TEXT DEFAULT '🍔',
    image TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    stock INTEGER NOT NULL DEFAULT 99,
    category_id INTEGER,
    barcode TEXT UNIQUE,
    image TEXT,
    is_available INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL,
    total REAL NOT NULL,
    discount REAL DEFAULT 0,
    tax_rate REAL DEFAULT 0,
    tax_amount REAL DEFAULT 0,
    discount_type TEXT DEFAULT 'regular',
    vat_exempt INTEGER DEFAULT 0,
    cash_tendered REAL,
    change_given REAL,
    payment_method TEXT DEFAULT 'cash',
    gcash_ref TEXT,
    served_by INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (served_by) REFERENCES users(id)
);

-- Void audit log — preserves record of all voided transactions (RA 9178 / BIR compliance)
CREATE TABLE IF NOT EXISTS void_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    order_number TEXT NOT NULL,
    total REAL NOT NULL,
    discount REAL DEFAULT 0,
    tax_amount REAL DEFAULT 0,
    discount_type TEXT DEFAULT 'regular',
    payment_method TEXT,
    voided_by INTEGER,
    voided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    FOREIGN KEY (voided_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS transaction_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('superadmin', 'cashier')),
    is_active INTEGER NOT NULL DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    clock_in TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    clock_out TIMESTAMP,
    opening_cash REAL DEFAULT 0,
    closing_cash REAL,
    notes TEXT,
    status TEXT DEFAULT 'active' CHECK(status IN ('active','closed')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ── Sabbis Burger Seed Data ───────────────────────────────

INSERT OR IGNORE INTO categories (name, icon) VALUES
    ('Burgers',      '🍔'),
    ('Cheese Burgers','🧀'),
    ('Drinks',       '🥤'),
    ('Extras',       '🍟');

-- INSERT OR IGNORE INTO products (name, description, price, stock, category_id, barcode, is_available) VALUES
--     -- Burgers
--     ('Regular Burger',       'Classic Sabbis beef patty',          25.00, 99, 1, 'BRG001', 1),
--     ('Double Burger',        'Two beef patties, extra filling',     40.00, 99, 1, 'BRG002', 1),
--     ('Special Burger',       'With egg and special sauce',          35.00, 99, 1, 'BRG003', 1),
--     ('Jumbo Burger',         'Bigger patty, full loaded',           50.00, 99, 1, 'BRG004', 1),
--     -- Cheese Burgers
--     ('Cheese Burger',        'Regular with cheese',                 30.00, 99, 2, 'CBS001', 1),
--     ('Double Cheese Burger', 'Double patty with cheese',            50.00, 99, 2, 'CBS002', 1),
--     ('Special Cheese Burger','Egg, cheese and special sauce',       45.00, 99, 2, 'CBS003', 1),
--     ('Jumbo Cheese Burger',  'Jumbo with cheese',                   60.00, 99, 2, 'CBS004', 1),
--     -- Drinks
--     ('Bottled Water',        '500ml Mineral Water',                 15.00, 50, 3, 'DRK001', 1),
--     ('Coke 250ml',           'Coca-Cola regular',                   20.00, 50, 3, 'DRK002', 1),
--     ('Coke 500ml',           'Coca-Cola 500ml',                     35.00, 50, 3, 'DRK003', 1),
--     ('Royal 250ml',          'Royal Tru-Orange',                    20.00, 50, 3, 'DRK004', 1),
--     -- Extras
--     ('Extra Patty',          'Add an extra beef patty',             15.00, 99, 4, 'EXT001', 1),
--     ('Extra Cheese',         'Add cheese slice',                    10.00, 99, 4, 'EXT002', 1),
--     ('Extra Egg',            'Add fried egg',                       10.00, 99, 4, 'EXT003', 1),
--     ('Ketchup Pack',         'Extra ketchup sachet',                 2.00, 99, 4, 'EXT004', 1);