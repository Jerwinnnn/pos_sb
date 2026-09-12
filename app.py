import os
from dotenv import load_dotenv
load_dotenv()

from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, flash, session, Response)
from config import load_settings, save_settings, get_theme_css, THEME_PRESETS, FONT_OPTIONS
import uuid
from werkzeug.utils import secure_filename

UPLOAD_FOLDER   = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file_field, subfolder):
    """Save uploaded file, return relative URL or None."""
    f = request.files.get(file_field)
    if not f or f.filename == '':
        return None
    if not allowed_file(f.filename):
        return None
    ext      = f.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    dest     = os.path.join(UPLOAD_FOLDER, subfolder, filename)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    f.save(dest)
    return f"uploads/{subfolder}/{filename}" 
from database import (
    init_db,
    get_all_products, get_products_by_category, search_products,
    get_product, add_product, update_product, delete_product,
    get_all_categories, add_category, update_category, delete_category,
    get_active_shift, clock_in, clock_out, get_shift_summary,
    get_all_shifts, get_shift_stats_today,
    get_category_product_count, create_transaction, get_transaction,
    get_all_transactions, get_sales_summary, get_top_products,
    get_hourly_sales, get_sales_report, get_low_stock_items,
    restock_product, void_transaction, get_eod_summary, get_monthly_report
)
from auth import (
    seed_default_users, login_user, logout_user, set_session,
    current_user, login_required, superadmin_required,
    get_all_users, create_user, update_user, delete_user
)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-dev-key')

# Custom Jinja2 filters
app.jinja_env.filters['enumerate'] = enumerate

@app.context_processor
def inject_globals():
    s = load_settings()
    return {
        'current_user':   current_user(),
        'app_name':       s.get('store_name', 'My Store'),
        'store_tagline':  s.get('store_tagline', 'Point of Sale System'),
        'currency':       s.get('currency_symbol', '₱'),
        'logo_emoji':     s.get('logo_emoji', '🛒'),
        'receipt_footer': s.get('receipt_footer', 'Thank you!'),
        'settings':       s,
        'font_url':       FONT_OPTIONS.get(s.get('font','nunito'), FONT_OPTIONS['nunito'])['google'],
        'active_shift':   get_active_shift(session['user_id']) if 'user_id' in session else None,
    }

@app.route('/theme.css')
def theme_css():
    """Dynamic CSS with current brand color variables."""
    s   = load_settings()
    css = get_theme_css(s)
    return Response(css, mimetype='text/css')

# ── Auth ──────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = login_user(username, password)
        if user:
            set_session(user)
            flash(f'Welcome, {user["full_name"]}! 👋', 'success')
            return redirect(url_for('index'))
        flash('Invalid username or password.', 'error')
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    # Auto clock-out any active shift on logout
    if 'user_id' in session:
        shift = get_active_shift(session['user_id'])
        if shift:
            clock_out(shift['id'], notes='Auto clock-out on logout')
    logout_user()
    flash('Signed out successfully.', 'info')
    return redirect(url_for('login'))

# ── POS Terminal ──────────────────────────────────────────

@app.route('/')
@login_required
def index():
    categories = get_all_categories()
    products   = get_products_by_category()
    today, _   = get_sales_summary()
    return render_template('pos/index.html',
                           categories=categories,
                           products=products,
                           today_sales=today)

@app.route('/api/products')
@login_required
def api_products():
    category_id = request.args.get('category')
    query       = request.args.get('q', '').strip()
    if query:
        products = search_products(query)
    elif category_id:
        products = get_products_by_category(category_id)
    else:
        products = get_products_by_category()
    return jsonify([dict(p) for p in products])

@app.route('/api/checkout', methods=['POST'])
@login_required
def api_checkout():
    data           = request.get_json()
    cart           = data.get('cart', [])
    payment_method = data.get('payment_method', 'cash')
    cash_tendered  = data.get('cash_tendered')
    discount       = data.get('discount', 0)
    notes          = data.get('notes', '')
    gcash_ref = data.get('gcash_ref', '').strip()

    if not cart:
        return jsonify({'error': 'Cart is empty'}), 400

    # Validate GCash reference number
    if payment_method == 'gcash' and not gcash_ref:
        return jsonify({'error': 'GCash reference number is required.'}), 400

    try:
        transaction_id, order_number = create_transaction(
            cart_items=cart, payment_method=payment_method,
            cash_tendered=float(cash_tendered) if cash_tendered else None,
            served_by=session.get('user_id'),
            discount=float(discount) if discount else 0,
            notes=notes,
            gcash_ref=gcash_ref if payment_method == 'gcash' else None
        )
        tx, items = get_transaction(transaction_id)
        return jsonify({
            'success': True, 'transaction_id': transaction_id,
            'order_number': order_number, 'total': tx['total'],
            'discount': tx['discount'], 'change': tx['change_given'],
            'gcash_ref': tx['gcash_ref'],
            'items': [dict(i) for i in items]
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Transaction failed: ' + str(e)}), 500

# ── Dashboard ─────────────────────────────────────────────

@app.route('/dashboard')
@superadmin_required
def dashboard():
    today, overall       = get_sales_summary()
    top_products         = get_top_products()
    recent_tx            = get_all_transactions(limit=5)
    low_stock            = get_low_stock_items(threshold=10)
    active_shifts, today_shifts = get_shift_stats_today()
    return render_template('admin/dashboard.html',
                           today=today, overall=overall,
                           top_products=top_products,
                           recent_tx=recent_tx,
                           low_stock=low_stock,
                           active_shifts=active_shifts,
                           today_shifts=today_shifts)

# ── Dashboard API (live refresh) ─────────────────────────

@app.route('/api/dashboard-stats')
@superadmin_required
def api_dashboard_stats():
    today, overall = get_sales_summary()
    top            = get_top_products(5)
    low_stock      = get_low_stock_items(10)
    return jsonify({
        'today_revenue': today['total'],
        'today_orders':  today['count'],
        'overall_revenue': overall['total'],
        'overall_orders':  overall['count'],
        'top_products': [dict(p) for p in top],
        'low_stock':    [dict(p) for p in low_stock],
    })

# ── Reports ───────────────────────────────────────────────

@app.route('/reports')
@superadmin_required
def reports():
    period = request.args.get('period', 'today')
    summary, top_items, daily_trend, hourly = get_sales_report(period)
    return render_template('admin/reports.html',
                           period=period,
                           summary=summary,
                           top_items=top_items,
                           daily_trend=daily_trend,
                           hourly=hourly)

# ── End of Day ────────────────────────────────────────────

@app.route('/eod')
@superadmin_required
def eod():
    from datetime import datetime
    mode  = request.args.get('mode', 'daily')   # 'daily' or 'monthly'
    now   = datetime.now()

    if mode == 'monthly':
        year  = int(request.args.get('year',  now.year))
        month = int(request.args.get('month', now.month))
        m_summary, daily_breakdown, m_top_items, best_day = get_monthly_report(year, month)
        return render_template('admin/eod.html',
                               mode='monthly',
                               year=year, month=month,
                               m_summary=m_summary,
                               daily_breakdown=daily_breakdown,
                               m_top_items=m_top_items,
                               best_day=best_day,
                               summary=None, top_item=None, transactions=None,
                               now=now.strftime('%b %d, %Y %I:%M %p'))
    else:
        summary, top_item, transactions = get_eod_summary()
        return render_template('admin/eod.html',
                               mode='daily',
                               year=now.year, month=now.month,
                               summary=summary,
                               top_item=top_item,
                               transactions=transactions,
                               m_summary=None, daily_breakdown=None,
                               m_top_items=None, best_day=None,
                               now=now.strftime('%b %d, %Y %I:%M %p'))

# ── Restock ───────────────────────────────────────────────

@app.route('/restock', methods=['POST'])
@superadmin_required
def restock():
    product_id = request.form.get('product_id')
    add_qty    = request.form.get('add_qty', 0)
    try:
        restock_product(int(product_id), int(add_qty))
        flash(f'Stock updated successfully!', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(request.referrer or url_for('dashboard'))

# ── Void transaction ──────────────────────────────────────

@app.route('/transactions/void/<int:transaction_id>', methods=['POST'])
@superadmin_required
def void_transaction_route(transaction_id):
    try:
        void_transaction(transaction_id)
        flash(f'Transaction voided and stock restored.', 'success')
    except Exception as e:
        flash(f'Error voiding transaction: {e}', 'error')
    return redirect(url_for('transactions'))

# ── Products ──────────────────────────────────────────────

@app.route('/products')
@superadmin_required
def products():
    return render_template('admin/products.html',
                           products=get_all_products(),
                           categories=get_all_categories(),
                           cat_counts=get_category_product_count())

@app.route('/products/add', methods=['POST'])
@superadmin_required
def add_product_route():
    name        = request.form.get('name','').strip()
    price       = request.form.get('price')
    stock       = request.form.get('stock', 99)
    category_id = request.form.get('category_id')
    barcode     = request.form.get('barcode','').strip() or None
    description = request.form.get('description','').strip() or None
    is_available= int(request.form.get('is_available', 1))
    if not name or not price:
        flash('Name and price are required.', 'error')
        return redirect(url_for('products'))
    try:
        image = save_upload('image', 'products')
        add_product(name, float(price), int(stock),
                    int(category_id) if category_id else None,
                    barcode, description, is_available, image)
        flash(f'"{name}" added to menu!', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('products'))

@app.route('/products/edit/<int:product_id>', methods=['POST'])
@superadmin_required
def edit_product_route(product_id):
    name        = request.form.get('name','').strip()
    price       = request.form.get('price')
    stock       = request.form.get('stock', 99)
    category_id = request.form.get('category_id')
    barcode     = request.form.get('barcode','').strip() or None
    description = request.form.get('description','').strip() or None
    is_available= int(request.form.get('is_available', 1))
    try:
        remove_image = request.form.get('remove_image') == '1'
        image = save_upload('image', 'products')
        if remove_image and image is None:
            image = ''   # explicitly clear the image
        update_product(product_id, name, float(price), int(stock),
                       int(category_id) if category_id else None,
                       barcode, description, is_available, image)
        flash('Menu item updated!', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('products'))

@app.route('/products/delete/<int:product_id>', methods=['POST'])
@superadmin_required
def delete_product_route(product_id):
    try:
        result = delete_product(product_id)
        if result == 'hidden':
            flash('Item has sales history — it has been hidden from the menu instead of deleted.', 'warning')
        else:
            flash('Item permanently removed from menu.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('products'))

# ── Categories ───────────────────────────────────────────

@app.route('/categories/add', methods=['POST'])
@superadmin_required
def add_category_route():
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', '🍔').strip() or '🍔'
    if not name:
        flash('Category name is required.', 'error')
        return redirect(url_for('products'))
    try:
        image = save_upload('image', 'categories')
        add_category(name, icon, image)
        flash(f'Category "{name}" added!', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('products'))

@app.route('/categories/edit/<int:category_id>', methods=['POST'])
@superadmin_required
def edit_category_route(category_id):
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', '🍔').strip() or '🍔'
    if not name:
        flash('Category name is required.', 'error')
        return redirect(url_for('products'))
    try:
        remove_image = request.form.get('remove_image') == '1'
        image = save_upload('image', 'categories')
        if remove_image and image is None:
            image = ''   # explicitly clear the image
        update_category(category_id, name, icon, image)
        flash(f'Category updated!', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('products'))

@app.route('/categories/delete/<int:category_id>', methods=['POST'])
@superadmin_required
def delete_category_route(category_id):
    try:
        delete_category(category_id)
        flash('Category deleted. Products in this category are now uncategorised.', 'warning')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('products'))

# ── Transactions ──────────────────────────────────────────

@app.route('/transactions')
@superadmin_required
def transactions():
    today, overall = get_sales_summary()
    return render_template('admin/transactions.html',
                           transactions=get_all_transactions(),
                           today=today, overall=overall)

@app.route('/transactions/<int:transaction_id>')
@superadmin_required
def transaction_detail(transaction_id):
    tx, items = get_transaction(transaction_id)
    if not tx:
        flash('Transaction not found.', 'error')
        return redirect(url_for('transactions'))
    return render_template('admin/transaction_detail.html',
                           transaction=tx, items=items)

# ── Users ─────────────────────────────────────────────────

@app.route('/users')
@superadmin_required
def users():
    return render_template('admin/users.html', users=get_all_users())

@app.route('/users/add', methods=['POST'])
@superadmin_required
def add_user_route():
    username  = request.form.get('username','').strip()
    password  = request.form.get('password','')
    full_name = request.form.get('full_name','').strip()
    role      = request.form.get('role','cashier')
    if not username or not password or not full_name:
        flash('All fields are required.', 'error')
        return redirect(url_for('users'))
    try:
        create_user(username, password, full_name, role)
        flash(f'Staff "{full_name}" added!', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('users'))

@app.route('/users/edit/<int:user_id>', methods=['POST'])
@superadmin_required
def edit_user_route(user_id):
    full_name = request.form.get('full_name','').strip()
    role      = request.form.get('role','cashier')
    is_active = int(request.form.get('is_active', 1))
    password  = request.form.get('password','').strip() or None
    if user_id == session.get('user_id') and not is_active:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('users'))
    try:
        update_user(user_id, full_name, role, is_active, password)
        flash('Staff account updated!', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('users'))

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@superadmin_required
def delete_user_route(user_id):
    if user_id == session.get('user_id'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('users'))
    try:
        delete_user(user_id)
        flash('Staff account removed.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('users'))

# ── Shift Management ─────────────────────────────────────

@app.route('/shift/clockin', methods=['POST'])
@login_required
def shift_clock_in():
    opening_cash = request.form.get('opening_cash', 0)
    try:
        clock_in(session['user_id'], float(opening_cash) if opening_cash else 0)
        flash('Shift started! Have a great day. 👋', 'success')
    except Exception as e:
        flash(f'Error starting shift: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/shift/clockout', methods=['POST'])
@login_required
def shift_clock_out():
    shift = get_active_shift(session['user_id'])
    if not shift:
        flash('No active shift found.', 'warning')
        return redirect(url_for('index'))
    closing_cash = request.form.get('closing_cash')
    notes        = request.form.get('notes', '').strip()
    try:
        clock_out(shift['id'],
                  float(closing_cash) if closing_cash else None,
                  notes or None)
        flash('Shift ended. Good work today!', 'success')
    except Exception as e:
        flash(f'Error ending shift: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/shifts')
@superadmin_required
def shifts():
    all_shifts         = get_all_shifts()
    active_count, today_count = get_shift_stats_today()
    return render_template('admin/shifts.html',
                           shifts=all_shifts,
                           active_count=active_count,
                           today_count=today_count)

@app.route('/shifts/<int:shift_id>')
@superadmin_required
def shift_detail(shift_id):
    shift, transactions, stats = get_shift_summary(shift_id)
    if not shift:
        flash('Shift not found.', 'error')
        return redirect(url_for('shifts'))
    return render_template('admin/shift_detail.html',
                           shift=shift,
                           transactions=transactions,
                           stats=stats)

# ── Settings ─────────────────────────────────────────────

@app.route('/settings', methods=['GET'])
@superadmin_required
def settings_page():
    return render_template('admin/settings.html',
                           settings=load_settings(),
                           presets=THEME_PRESETS,
                           fonts=FONT_OPTIONS)

@app.route('/settings/save', methods=['POST'])
@superadmin_required
def save_settings_route():
    data = {
        'store_name':      request.form.get('store_name', '').strip() or 'My Store',
        'store_tagline':   request.form.get('store_tagline', '').strip(),
        'currency_symbol': request.form.get('currency_symbol', '₱').strip() or '₱',
        'theme_preset':    request.form.get('theme_preset', 'red'),
        'theme_color':     request.form.get('theme_color', '#E83B2A').strip(),
        'font':            request.form.get('font', 'nunito'),
        'logo_emoji':      request.form.get('logo_emoji', '🛒').strip(),
        'receipt_footer':  request.form.get('receipt_footer', '').strip(),
    }
    save_settings(data)
    flash('Settings saved! Refresh the page to see changes.', 'success')
    return redirect(url_for('settings_page'))

# ── Errors ────────────────────────────────────────────────

@app.errorhandler(403)
def forbidden(e):
    return render_template('auth/403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('auth/404.html'), 404

# ── Boot ──────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    seed_default_users()
    debug = os.getenv('FLASK_DEBUG','1') == '1'
    port  = int(os.getenv('FLASK_PORT', 5000))
    app.run(debug=debug, port=port)