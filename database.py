import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE = os.path.join(
    os.path.dirname(__file__),
    os.getenv('DATABASE_PATH', 'pos.db')
)

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with get_db() as conn:
        with open(schema_path, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
    print("✅ Database initialized.")

def migrate_db():
    """Add columns/tables introduced after initial deploy. Safe to re-run."""
    new_cols = [
        ("transactions", "tax_rate",      "REAL DEFAULT 0"),
        ("transactions", "tax_amount",    "REAL DEFAULT 0"),
        ("transactions", "discount_type", "TEXT DEFAULT 'regular'"),
        ("transactions", "vat_exempt",    "INTEGER DEFAULT 0"),
    ]
    with get_db() as conn:
        for table, col, typedef in new_cols:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")
            except Exception:
                pass  # column already exists — safe to ignore
        # void_log is created by schema.sql on fresh DBs; ensure it exists on older ones
        conn.execute("""
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
            )
        """)
        conn.commit()
    print("✅ Database migrated.")

# ── Categories CRUD ──────────────────────────────────────

def add_category(name, icon='🍔', image=None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO categories (name, icon, image) VALUES (?, ?, ?)", (name, icon, image)
        )
        conn.commit()

def update_category(category_id, name, icon, image=None):
    with get_db() as conn:
        if image is not None:
            # image='' means remove photo, image='path/...' means new photo
            conn.execute(
                "UPDATE categories SET name=?, icon=?, image=? WHERE id=?",
                (name, icon, image or None, category_id)
            )
        else:
            conn.execute(
                "UPDATE categories SET name=?, icon=? WHERE id=?",
                (name, icon, category_id)
            )
        conn.commit()

def delete_category(category_id):
    with get_db() as conn:
        # Check if any products use this category
        count = conn.execute(
            "SELECT COUNT(*) FROM products WHERE category_id=?", (category_id,)
        ).fetchone()[0]
        if count > 0:
            # Unlink products from category instead of blocking
            conn.execute(
                "UPDATE products SET category_id=NULL WHERE category_id=?", (category_id,)
            )
        conn.execute("DELETE FROM categories WHERE id=?", (category_id,))
        conn.commit()

def get_category_product_count():
    """Returns dict of category_id -> product count."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT category_id, COUNT(*) AS cnt
            FROM products WHERE category_id IS NOT NULL
            GROUP BY category_id
        """).fetchall()
        return {r['category_id']: r['cnt'] for r in rows}

# ── Products ──────────────────────────────────────────────

def get_all_products():
    with get_db() as conn:
        return conn.execute("""
            SELECT p.*, c.name AS category_name, c.icon AS category_icon, c.image AS category_image
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY c.id, p.name
        """).fetchall()

def get_products_by_category(category_id=None):
    with get_db() as conn:
        if category_id:
            return conn.execute("""
                SELECT p.*, c.name AS category_name, c.icon AS category_icon, c.image AS category_image
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.category_id = ? AND p.is_available = 1
                ORDER BY p.price
            """, (category_id,)).fetchall()
        return conn.execute("""
            SELECT p.*, c.name AS category_name, c.icon AS category_icon, c.image AS category_image
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.is_available = 1
            ORDER BY c.id, p.price
        """).fetchall()

def search_products(query):
    with get_db() as conn:
        like = f"%{query}%"
        return conn.execute("""
            SELECT p.*, c.name AS category_name, c.icon AS category_icon, c.image AS category_image
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE (p.name LIKE ? OR p.barcode LIKE ?) AND p.is_available = 1
            ORDER BY p.price
        """, (like, like)).fetchall()

def get_product(product_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

def add_product(name, price, stock, category_id, barcode=None, description=None, is_available=1, image=None):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO products (name, description, price, stock, category_id, barcode, is_available, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, description, price, stock, category_id, barcode, is_available, image))
        conn.commit()

def update_product(product_id, name, price, stock, category_id, barcode=None, description=None, is_available=1, image=None):
    with get_db() as conn:
        if image is not None:
            # image='' means remove, image='path/...' means new photo
            conn.execute("""
                UPDATE products SET name=?, description=?, price=?, stock=?,
                category_id=?, barcode=?, is_available=?, image=? WHERE id=?
            """, (name, description, price, stock, category_id, barcode, is_available,
                    image or None, product_id))
        else:
            # image=None means no change to existing image
            conn.execute("""
                UPDATE products SET name=?, description=?, price=?, stock=?,
                category_id=?, barcode=?, is_available=? WHERE id=?
            """, (name, description, price, stock, category_id, barcode, is_available, product_id))
        conn.commit()

def delete_product(product_id):
    with get_db() as conn:
        # Check if product has been sold — if yes, just hide it instead of hard delete
        sold = conn.execute(
            "SELECT COUNT(*) FROM transaction_items WHERE product_id = ?", (product_id,)
        ).fetchone()[0]
        if sold > 0:
            # Product has sales history — mark unavailable instead of deleting
            conn.execute(
                "UPDATE products SET is_available = 0 WHERE id = ?", (product_id,)
            )
            conn.commit()
            return 'hidden'   # caller can show appropriate message
        else:
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
            return 'deleted'

# ── Categories ────────────────────────────────────────────

def get_all_categories():
    with get_db() as conn:
        return conn.execute("SELECT * FROM categories ORDER BY id").fetchall()

# ── Order Number ──────────────────────────────────────────

def generate_order_number():
    """Generate order number like ORD-0001, resetting daily."""
    from datetime import date
    today = date.today().strftime('%Y%m%d')
    with get_db() as conn:
        count = conn.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE DATE(created_at,'localtime') = DATE('now','localtime')
        """).fetchone()[0]
    return f"ORD-{today}-{str(count + 1).zfill(4)}"

# ── Transactions ──────────────────────────────────────────

def create_transaction(cart_items, payment_method, cash_tendered=None, served_by=None,
                        discount=0, notes=None, gcash_ref=None,
                        discount_type='regular', tax_rate=0.0,
                        tax_enabled=False, tax_inclusive=True):
    """
    Computes tax per Philippine TRAIN Law (RA 10963):
      - Regular: 12% VAT inclusive (extract from price) or exclusive (add on top)
      - Senior Citizen / PWD (RA 9994 / RA 10754):
          1. Remove VAT from subtotal → net price
          2. Apply 20% mandatory discount on net price
          3. Transaction is VAT-exempt (zero VAT charged)
    """
    subtotal = sum(item['quantity'] * item['unit_price'] for item in cart_items)
    actual_discount = float(discount or 0)
    tax_amount = 0.0
    vat_exempt = 0
    rate = float(tax_rate) if tax_enabled else 0.0

    if discount_type in ('senior_citizen', 'pwd'):
        vat_exempt = 1
        if tax_enabled and tax_inclusive and rate > 0:
            net_of_vat = subtotal / (1 + rate / 100)
        else:
            net_of_vat = subtotal
        sc_discount = net_of_vat * 0.20
        total = round(net_of_vat - sc_discount, 2)
        actual_discount = round(subtotal - total, 2)  # effective discount = VAT removed + 20% off net
        tax_amount = 0.0
    else:
        post_disc = max(0.0, subtotal - actual_discount)
        if tax_enabled and rate > 0:
            if tax_inclusive:
                # VAT is embedded in the price; extract the component
                tax_amount = round(post_disc * (rate / (100 + rate)), 2)
            else:
                # VAT added on top of the discounted subtotal
                tax_amount = round(post_disc * (rate / 100), 2)
                post_disc = post_disc + tax_amount
        total = round(max(0.0, post_disc), 2)

    change = round((cash_tendered - total), 2) if cash_tendered else 0
    order_number = generate_order_number()

    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO transactions
                (order_number, total, discount, tax_rate, tax_amount, discount_type, vat_exempt,
                 cash_tendered, change_given, payment_method, gcash_ref, served_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_number, total, actual_discount, rate, tax_amount, discount_type, vat_exempt,
              cash_tendered, change, payment_method, gcash_ref, served_by, notes))
        transaction_id = cur.lastrowid

        for item in cart_items:
            product = conn.execute("SELECT name, stock FROM products WHERE id=?", (item['product_id'],)).fetchone()
            if not product:
                conn.rollback()
                raise ValueError(f"Product {item['product_id']} not found")

            conn.execute("""
                INSERT INTO transaction_items
                    (transaction_id, product_id, product_name, quantity, unit_price, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (transaction_id, item['product_id'], product['name'],
                  item['quantity'], item['unit_price'],
                  item['quantity'] * item['unit_price']))

            # Deduct stock after every item sold
            conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (item['quantity'], item['product_id'])
            )

        conn.commit()
        return transaction_id, order_number

def get_transaction(transaction_id):
    with get_db() as conn:
        tx = conn.execute("""
            SELECT t.*, u.full_name AS cashier_name
            FROM transactions t
            LEFT JOIN users u ON t.served_by = u.id
            WHERE t.id = ?
        """, (transaction_id,)).fetchone()
        items = conn.execute(
            "SELECT * FROM transaction_items WHERE transaction_id=?", (transaction_id,)
        ).fetchall()
        return tx, items

def get_all_transactions(limit=100):
    with get_db() as conn:
        return conn.execute("""
            SELECT t.*, COUNT(ti.id) AS item_count, u.full_name AS cashier_name
            FROM transactions t
            LEFT JOIN transaction_items ti ON t.id = ti.transaction_id
            LEFT JOIN users u ON t.served_by = u.id
            GROUP BY t.id
            ORDER BY t.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()

def get_sales_summary():
    with get_db() as conn:
        today = conn.execute("""
            SELECT COALESCE(SUM(total),0) AS total, COUNT(*) AS count
            FROM transactions
            WHERE DATE(created_at,'localtime') = DATE('now','localtime')
        """).fetchone()
        overall = conn.execute("""
            SELECT COALESCE(SUM(total),0) AS total, COUNT(*) AS count
            FROM transactions
        """).fetchone()
        return today, overall

def get_top_products(limit=5):
    with get_db() as conn:
        return conn.execute("""
            SELECT ti.product_name, SUM(ti.quantity) AS total_qty, SUM(ti.subtotal) AS total_revenue
            FROM transaction_items ti
            JOIN transactions t ON ti.transaction_id = t.id
            WHERE DATE(t.created_at,'localtime') = DATE('now','localtime')
            GROUP BY ti.product_name
            ORDER BY total_qty DESC
            LIMIT ?
        """, (limit,)).fetchall()

def get_hourly_sales():
    with get_db() as conn:
        return conn.execute("""
            SELECT strftime('%H:00', created_at, 'localtime') AS hour,
                   COUNT(*) AS orders,
                   COALESCE(SUM(total),0) AS revenue
            FROM transactions
            WHERE DATE(created_at,'localtime') = DATE('now','localtime')
            GROUP BY hour ORDER BY hour
        """).fetchall()

# ── Reports & Analytics ───────────────────────────────────

def get_sales_report(period='today'):
    """period: today | week | month"""
    with get_db() as conn:
        if period == 'today':
            date_filter = "DATE(created_at,'localtime') = DATE('now','localtime')"
        elif period == 'week':
            date_filter = "DATE(created_at,'localtime') >= DATE('now','-6 days','localtime')"
        else:  # month
            date_filter = "strftime('%Y-%m', created_at,'localtime') = strftime('%Y-%m','now','localtime')"

        summary = conn.execute(f"""
            SELECT
                COALESCE(SUM(total),0)   AS revenue,
                COUNT(*)                  AS orders,
                COALESCE(AVG(total),0)   AS avg_order,
                COALESCE(SUM(CASE WHEN payment_method='cash' THEN total ELSE 0 END),0) AS cash_revenue,
                COALESCE(SUM(CASE WHEN payment_method='card' THEN total ELSE 0 END),0) AS card_revenue,
                COUNT(CASE WHEN payment_method='cash' THEN 1 END) AS cash_orders,
                COUNT(CASE WHEN payment_method='card' THEN 1 END) AS card_orders
            FROM transactions WHERE {date_filter}
        """).fetchone()

        top_items = conn.execute(f"""
            SELECT ti.product_name,
                   SUM(ti.quantity)  AS total_qty,
                   SUM(ti.subtotal)  AS total_revenue
            FROM transaction_items ti
            JOIN transactions t ON ti.transaction_id = t.id
            WHERE {date_filter}
            GROUP BY ti.product_name
            ORDER BY total_qty DESC LIMIT 8
        """).fetchall()

        daily_trend = conn.execute("""
            SELECT DATE(created_at,'localtime') AS day,
                   COUNT(*)                      AS orders,
                   COALESCE(SUM(total),0)        AS revenue
            FROM transactions
            WHERE DATE(created_at,'localtime') >= DATE('now','-6 days','localtime')
            GROUP BY day ORDER BY day
        """).fetchall()

        hourly = conn.execute(f"""
            SELECT strftime('%H', created_at,'localtime') AS hr,
                   COUNT(*)                AS orders,
                   COALESCE(SUM(total),0) AS revenue
            FROM transactions
            WHERE {date_filter}
            GROUP BY hr ORDER BY hr
        """).fetchall()

        return dict(summary), [dict(r) for r in top_items], \
               [dict(r) for r in daily_trend], [dict(r) for r in hourly]

def get_low_stock_items(threshold=10):
    with get_db() as conn:
        return conn.execute("""
            SELECT p.*, c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.stock <= ? AND p.is_available = 1
            ORDER BY p.stock ASC
        """, (threshold,)).fetchall()

def restock_product(product_id, add_qty):
    with get_db() as conn:
        conn.execute("UPDATE products SET stock = stock + ? WHERE id = ?",
                     (int(add_qty), product_id))
        conn.commit()

def void_transaction(transaction_id, voided_by=None, reason=None):
    """Write void audit log, restore stock, then delete transaction."""
    with get_db() as conn:
        tx = conn.execute(
            "SELECT * FROM transactions WHERE id=?", (transaction_id,)
        ).fetchone()
        if not tx:
            raise ValueError(f"Transaction {transaction_id} not found")

        # Write immutable void audit record before any deletion (BIR compliance)
        conn.execute("""
            INSERT INTO void_log
                (transaction_id, order_number, total, discount, tax_amount,
                 discount_type, payment_method, voided_by, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (transaction_id, tx['order_number'], tx['total'], tx['discount'],
              tx['tax_amount'] if 'tax_amount' in tx.keys() else 0,
              tx['discount_type'] if 'discount_type' in tx.keys() else 'regular',
              tx['payment_method'], voided_by, reason))

        items = conn.execute(
            "SELECT product_id, quantity FROM transaction_items WHERE transaction_id=?",
            (transaction_id,)
        ).fetchall()
        for item in items:
            conn.execute("UPDATE products SET stock = stock + ? WHERE id = ?",
                         (item['quantity'], item['product_id']))
        conn.execute("DELETE FROM transaction_items WHERE transaction_id=?", (transaction_id,))
        conn.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
        conn.commit()

def get_eod_summary():
    """End-of-day complete summary."""
    with get_db() as conn:
        summary = conn.execute("""
            SELECT
                COALESCE(SUM(total),0)  AS total_revenue,
                COUNT(*)                 AS total_orders,
                COALESCE(AVG(total),0)  AS avg_order,
                COALESCE(MAX(total),0)  AS biggest_order,
                COALESCE(SUM(CASE WHEN payment_method='cash' THEN total ELSE 0 END),0) AS cash_total,
                COALESCE(SUM(CASE WHEN payment_method='card' THEN total ELSE 0 END),0) AS card_total,
                COALESCE(SUM(discount),0) AS total_discounts
            FROM transactions
            WHERE DATE(created_at,'localtime') = DATE('now','localtime')
        """).fetchone()

        top = conn.execute("""
            SELECT ti.product_name, SUM(ti.quantity) AS qty
            FROM transaction_items ti
            JOIN transactions t ON ti.transaction_id = t.id
            WHERE DATE(t.created_at,'localtime') = DATE('now','localtime')
            GROUP BY ti.product_name ORDER BY qty DESC LIMIT 1
        """).fetchone()

        txs = conn.execute("""
            SELECT t.order_number, t.total, t.payment_method,
                   t.created_at, u.full_name AS cashier
            FROM transactions t
            LEFT JOIN users u ON t.served_by = u.id
            WHERE DATE(t.created_at,'localtime') = DATE('now','localtime')
            ORDER BY t.created_at DESC
        """).fetchall()

        return dict(summary), dict(top) if top else None, [dict(r) for r in txs]

def get_monthly_report(year, month):
    """Full month report — daily breakdown, top items, payment split."""
    ym = f"{year}-{str(month).zfill(2)}"
    with get_db() as conn:
        summary = conn.execute("""
            SELECT
                COALESCE(SUM(total),0)    AS total_revenue,
                COUNT(*)                   AS total_orders,
                COALESCE(AVG(total),0)    AS avg_order,
                COALESCE(MAX(total),0)    AS biggest_order,
                COALESCE(SUM(CASE WHEN payment_method='cash' THEN total ELSE 0 END),0) AS cash_total,
                COALESCE(SUM(CASE WHEN payment_method='card' THEN total ELSE 0 END),0) AS card_total,
                COALESCE(SUM(discount),0) AS total_discounts,
                COUNT(CASE WHEN payment_method='cash' THEN 1 END) AS cash_orders,
                COUNT(CASE WHEN payment_method='card' THEN 1 END) AS card_orders
            FROM transactions
            WHERE strftime('%Y-%m', created_at, 'localtime') = ?
        """, (ym,)).fetchone()

        # Daily breakdown
        daily = conn.execute("""
            SELECT
                DATE(created_at,'localtime')  AS day,
                COUNT(*)                       AS orders,
                COALESCE(SUM(total),0)        AS revenue,
                COALESCE(SUM(CASE WHEN payment_method='cash' THEN total ELSE 0 END),0) AS cash,
                COALESCE(SUM(CASE WHEN payment_method='card' THEN total ELSE 0 END),0) AS card
            FROM transactions
            WHERE strftime('%Y-%m', created_at, 'localtime') = ?
            GROUP BY day ORDER BY day
        """, (ym,)).fetchall()

        # Top items for the month
        top_items = conn.execute("""
            SELECT ti.product_name,
                   SUM(ti.quantity)  AS total_qty,
                   SUM(ti.subtotal)  AS total_revenue
            FROM transaction_items ti
            JOIN transactions t ON ti.transaction_id = t.id
            WHERE strftime('%Y-%m', t.created_at, 'localtime') = ?
            GROUP BY ti.product_name
            ORDER BY total_qty DESC LIMIT 10
        """, (ym,)).fetchall()

        # Best day of the month
        best_day = conn.execute("""
            SELECT DATE(created_at,'localtime') AS day,
                   COALESCE(SUM(total),0) AS revenue,
                   COUNT(*) AS orders
            FROM transactions
            WHERE strftime('%Y-%m', created_at, 'localtime') = ?
            GROUP BY day ORDER BY revenue DESC LIMIT 1
        """, (ym,)).fetchone()

        return (dict(summary),
                [dict(r) for r in daily],
                [dict(r) for r in top_items],
                dict(best_day) if best_day else None)

# ── Shift Management ──────────────────────────────────────

def get_active_shift(user_id):
    """Get the currently active shift for a user, if any."""
    with get_db() as conn:
        return conn.execute("""
            SELECT s.*, u.full_name, u.role
            FROM shifts s
            JOIN users u ON s.user_id = u.id
            WHERE s.user_id = ? AND s.status = 'active'
            ORDER BY s.clock_in DESC LIMIT 1
        """, (user_id,)).fetchone()

def clock_in(user_id, opening_cash=0):
    """Start a new shift. Closes any orphaned active shifts first."""
    with get_db() as conn:
        # Auto-close any forgotten open shifts
        conn.execute("""
            UPDATE shifts SET status='closed', clock_out=CURRENT_TIMESTAMP
            WHERE user_id=? AND status='active'
        """, (user_id,))
        conn.execute("""
            INSERT INTO shifts (user_id, opening_cash, status)
            VALUES (?, ?, 'active')
        """, (user_id, opening_cash or 0))
        conn.commit()

def clock_out(shift_id, closing_cash=None, notes=None):
    """End a shift."""
    with get_db() as conn:
        conn.execute("""
            UPDATE shifts
            SET status='closed', clock_out=CURRENT_TIMESTAMP,
                closing_cash=?, notes=?
            WHERE id=? AND status='active'
        """, (closing_cash, notes, shift_id))
        conn.commit()

def get_shift_summary(shift_id):
    """Sales stats for a specific shift."""
    with get_db() as conn:
        shift = conn.execute("""
            SELECT s.*, u.full_name, u.role
            FROM shifts s JOIN users u ON s.user_id = u.id
            WHERE s.id = ?
        """, (shift_id,)).fetchone()

        if not shift:
            return None, [], None

        # Transactions during this shift window
        query_args = [shift['user_id'], shift['clock_in']]
        time_filter = "t.served_by=? AND t.created_at >= ?"
        if shift['clock_out']:
            time_filter += " AND t.created_at <= ?"
            query_args.append(shift['clock_out'])

        stats = conn.execute(f"""
            SELECT
                COUNT(*) AS total_orders,
                COALESCE(SUM(total),0) AS total_revenue,
                COALESCE(SUM(CASE WHEN payment_method='cash' THEN total ELSE 0 END),0) AS cash_sales,
                COALESCE(SUM(CASE WHEN payment_method='card' THEN total ELSE 0 END),0) AS card_sales,
                COALESCE(SUM(CASE WHEN payment_method='gcash' THEN total ELSE 0 END),0) AS gcash_sales,
                COALESCE(SUM(discount),0) AS total_discounts
            FROM transactions t WHERE {time_filter}
        """, query_args).fetchone()

        transactions = conn.execute(f"""
            SELECT t.*, COUNT(ti.id) AS item_count
            FROM transactions t
            LEFT JOIN transaction_items ti ON t.id = ti.transaction_id
            WHERE {time_filter}
            GROUP BY t.id ORDER BY t.created_at DESC
        """, query_args).fetchall()

        return dict(shift), [dict(r) for r in transactions], dict(stats)

def get_all_shifts(limit=50):
    """All shifts for admin view."""
    with get_db() as conn:
        return conn.execute("""
            SELECT s.*,
                   u.full_name, u.role,
                   ROUND((JULIANDAY(COALESCE(s.clock_out, DATETIME('now'))) -
                          JULIANDAY(s.clock_in)) * 24, 2) AS hours_worked
            FROM shifts s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.clock_in DESC
            LIMIT ?
        """, (limit,)).fetchall()

def get_shift_stats_today():
    """Quick stats for dashboard — active shifts and today's shift count."""
    with get_db() as conn:
        active = conn.execute("""
            SELECT COUNT(*) FROM shifts WHERE status='active'
        """).fetchone()[0]
        today = conn.execute("""
            SELECT COUNT(*) FROM shifts
            WHERE DATE(clock_in,'localtime') = DATE('now','localtime')
        """).fetchone()[0]
        return active, today