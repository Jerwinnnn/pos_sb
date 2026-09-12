"""
config.py — Runtime settings loader
Reads/writes settings.json for all theme and store configuration.
"""
import json, os

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), 'settings.json')

DEFAULTS = {
    # ── Appearance ────────────────────────────────────────────
    'store_name':       'My Store',
    'store_tagline':    'Point of Sale System',
    'currency_symbol':  '₱',
    'theme_color':      '#E83B2A',
    'theme_preset':     'red',
    'font':             'nunito',
    'logo_emoji':       '🛒',
    'receipt_footer':   'Thank you for your purchase!',
    # ── Business Details (BIR / DTI compliance) ───────────────
    'tin_number':       '',          # BIR Tax Identification Number (XXX-XXX-XXX-XXXXX)
    'bir_permit':       '',          # BIR Authority to Print / Accreditation No.
    'dti_sec_number':   '',          # DTI or SEC registration number
    'business_address': '',          # Full registered business address
    'business_contact': '',          # Phone / email shown on receipts
    # ── Tax Settings (Philippine VAT — TRAIN Law, RA 10963) ───
    'tax_enabled':      '0',         # '1' = VAT enabled, '0' = disabled / non-VAT registered
    'tax_rate':         '12',        # VAT rate in percent (12% standard PH rate)
    'tax_inclusive':    '1',         # '1' = prices already include VAT (most common in PH retail)
}

THEME_PRESETS = {
    'red':    {'color': '#E83B2A', 'label': 'Flame Red',    'desc': 'Bold & energetic'},
    'orange': {'color': '#F97316', 'label': 'Burger Orange', 'desc': 'Warm & appetizing'},
    'green':  {'color': '#16A34A', 'label': 'Fresh Green',   'desc': 'Natural & healthy'},
    'blue':   {'color': '#2563EB', 'label': 'Ocean Blue',    'desc': 'Calm & professional'},
    'purple': {'color': '#7C3AED', 'label': 'Royal Purple',  'desc': 'Premium & elegant'},
    'teal':   {'color': '#0D9488', 'label': 'Teal',          'desc': 'Modern & fresh'},
    'pink':   {'color': '#DB2777', 'label': 'Hot Pink',      'desc': 'Fun & playful'},
    'dark':   {'color': '#1E293B', 'label': 'Midnight',      'desc': 'Sleek & minimal'},
    'custom': {'color': '',        'label': 'Custom Color',  'desc': 'Pick any color'},
}

FONT_OPTIONS = {
    'nunito':      {'label': 'Nunito',           'google': 'Nunito:wght@400;600;700;800;900'},
    'inter':       {'label': 'Inter',            'google': 'Inter:wght@400;500;600;700;800'},
    'poppins':     {'label': 'Poppins',          'google': 'Poppins:wght@400;500;600;700;800'},
    'outfit':      {'label': 'Outfit',           'google': 'Outfit:wght@400;500;600;700;800'},
    'dm_sans':     {'label': 'DM Sans',          'google': 'DM+Sans:wght@400;500;600;700;800'},
    'plus_jakarta':{'label': 'Plus Jakarta Sans','google': 'Plus+Jakarta+Sans:wght@400;500;600;700;800'},
}

def load_settings():
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Fill missing keys with defaults
        return {**DEFAULTS, **data}
    except Exception:
        return dict(DEFAULTS)

def save_settings(data):
    current = load_settings()
    current.update(data)
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(current, f, indent=2, ensure_ascii=False)
    return current

def get_theme_css(settings):
    """Generate CSS variable overrides for the current theme."""
    color = settings.get('theme_color', DEFAULTS['theme_color'])
    # Derive hover (lighter) and dim versions
    return f"""
:root {{
  --brand:       {color};
  --brand-h:     {_lighten_hex(color, 20)};
  --brand-dim:   {_hex_to_rgba(color, 0.1)};
  --brand-glow:  {_hex_to_rgba(color, 0.22)};
  --shadow-brand: 0 4px 18px {_hex_to_rgba(color, 0.35)};
}}
"""

def _hex_to_rgba(hex_color, alpha):
    """Convert #RRGGBB to rgba(r,g,b,alpha)."""
    try:
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        return f"rgba({r},{g},{b},{alpha})"
    except Exception:
        return f"rgba(232,59,42,{alpha})"

def _lighten_hex(hex_color, amount):
    """Lighten a hex color by mixing with white."""
    try:
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        r = min(255, r + amount)
        g = min(255, g + amount)
        b = min(255, b + amount)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color