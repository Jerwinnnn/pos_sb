import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, redirect, url_for, flash, abort
from database import get_db

# ── Seed default accounts (called once on init_db) ────────

def seed_default_users():
    """Create default superadmin and cashier if none exist."""
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            defaults = [
                ('admin',   os.getenv('ADMIN_PASSWORD', 'admin123'),   'Administrator', 'superadmin'),
                ('cashier', os.getenv('CASHIER_PASSWORD', 'cashier123'), 'Default Cashier', 'cashier'),
            ]
            for username, password, full_name, role in defaults:
                conn.execute("""
                    INSERT INTO users (username, password_hash, full_name, role)
                    VALUES (?, ?, ?, ?)
                """, (username, generate_password_hash(password), full_name, role))
            conn.commit()
            print("✅ Default users seeded.")

# ── Auth helpers ───────────────────────────────────────────

def login_user(username, password):
    """Validate credentials. Returns user row on success, None on failure."""
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)
        ).fetchone()
    if user and check_password_hash(user['password_hash'], password):
        # Update last_login
        with get_db() as conn:
            conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
            conn.commit()
        return user
    return None

def logout_user():
    session.clear()

def set_session(user):
    session['user_id']   = user['id']
    session['username']  = user['username']
    session['full_name'] = user['full_name']
    session['role']      = user['role']

def current_user():
    if 'user_id' not in session:
        return None
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ? AND is_active = 1", (session['user_id'],)
        ).fetchone()

def is_logged_in():
    return 'user_id' in session

# ── Decorators ─────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'superadmin':
            flash('Access denied. Superadmin only.', 'error')
            abort(403)
        return f(*args, **kwargs)
    return decorated

# ── User CRUD (superadmin only) ────────────────────────────

def get_all_users():
    with get_db() as conn:
        return conn.execute(
            "SELECT id, username, full_name, role, is_active, last_login, created_at FROM users ORDER BY role, username"
        ).fetchall()

def get_user(user_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

def create_user(username, password, full_name, role):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
        """, (username, generate_password_hash(password), full_name, role))
        conn.commit()

def update_user(user_id, full_name, role, is_active, password=None):
    with get_db() as conn:
        if password:
            conn.execute("""
                UPDATE users SET full_name=?, role=?, is_active=?, password_hash=?
                WHERE id=?
            """, (full_name, role, is_active, generate_password_hash(password), user_id))
        else:
            conn.execute("""
                UPDATE users SET full_name=?, role=?, is_active=? WHERE id=?
            """, (full_name, role, is_active, user_id))
        conn.commit()

def delete_user(user_id):
    with get_db() as conn:
        # Nullify served_by on transactions before deleting user
        # so transaction history is preserved
        conn.execute(
            "UPDATE transactions SET served_by = NULL WHERE served_by = ?", (user_id,)
        )
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()