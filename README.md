# POS App

A Flask + SQLite point-of-sale system for a small food business. It has a touch-friendly cashier terminal, shift clock-in/clock-out, and an admin back office for menu management, transactions, reports, and end-of-day summaries. Store name, currency, colors, and fonts are all configurable at runtime from the Settings page.

## Requirements

- Python 3.10+
- No external database — SQLite file (`pos.db`) is created automatically

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
python app.py
```

The app creates the schema, seeds the default categories and users, and starts on http://localhost:5000.

### Default accounts

| Username  | Password     | Role       |
|-----------|--------------|------------|
| `admin`   | `admin123`   | superadmin |
| `cashier` | `cashier123` | cashier    |

These are seeded only when the `users` table is empty. **Change them before any real use**, or set `ADMIN_PASSWORD` / `CASHIER_PASSWORD` before the first run.

### Environment variables

Create a `.env` file in the project root (loaded via `python-dotenv`):

```
SECRET_KEY=change-me
DATABASE_PATH=pos.db
FLASK_DEBUG=1
FLASK_PORT=5000
ADMIN_PASSWORD=...
CASHIER_PASSWORD=...
```

All have fallbacks, so the app runs without a `.env`. `SECRET_KEY` must be set for anything other than local development.

### Production

```bash
gunicorn app:app -w 4 -b 0.0.0.0:5000
```

Note that `init_db()` and `seed_default_users()` run only under `python app.py`. When serving through gunicorn, initialize the database once first:

```bash
python -c "from database import init_db; from auth import seed_default_users; init_db(); seed_default_users()"
```

## Roles

- **cashier** — POS terminal, checkout, and their own shift clock-in/out
- **superadmin** — everything above, plus dashboard, products, categories, transactions, shifts, users, reports, EOD, and settings

## Features

**POS terminal** ([templates/pos/](templates/pos/)) — category and search filtering, cart, cash / card / GCash payment (GCash requires a reference number), per-order discount, change calculation, and a receipt. Stock is deducted on every sale.

**Shifts** — cashiers clock in with an opening cash float and clock out with a closing count and notes. Logging out auto-closes an open shift. Admins can review each shift's sales, payment split, and hours worked.

**Admin** ([templates/admin/](templates/admin/)) — live dashboard with today's revenue, top products, and low-stock alerts; product and category CRUD with image upload; transaction history with void (restores stock); sales reports by day/week/month; end-of-day and full-month summaries.

**Settings** ([config.py](config.py)) — store name, tagline, currency symbol, logo emoji, receipt footer, one of eight theme presets or a custom brand color, and one of six Google Fonts. Saved to `settings.json` and served as CSS variables from the `/theme.css` route.

## Project layout

```
app.py           Flask routes, upload handling, app bootstrap
auth.py          Login, session, role decorators, user CRUD
database.py      Connection helper and all SQL queries
config.py        settings.json load/save, theme presets, CSS generation
schema.sql       Table definitions and category seed data
settings.json    Runtime store/theme configuration
templates/       Jinja2 templates — pos/, admin/, auth/
static/          css/, js/, uploads/ (product and category images)
```

## Data model

`categories` → `products` → `transaction_items` → `transactions`, with `users` referenced by `transactions.served_by` and `shifts.user_id`.

Two soft-delete behaviors are intentional: deleting a product that has sales history marks it unavailable instead of removing it, and deleting a category unlinks its products rather than blocking. Deleting a user nulls `served_by` so transaction history survives.

Order numbers are `ORD-YYYYMMDD-NNNN`, with the counter resetting daily.

## Notes

- `pos.db` is currently tracked in git. If this repo is ever shared, add a `.gitignore` for `pos.db`, `.venv/`, `__pycache__/`, `.env`, and `static/uploads/`.
- All date grouping uses SQLite's `'localtime'` modifier, so reports follow the server's timezone.
