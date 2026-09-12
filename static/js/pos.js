/* pos.js — Sabbis Burger POS Terminal */
'use strict';

// ── State ──────────────────────────────────────────────────
const State = {
  cart: [],
  paymentMethod: 'cash',
  currency: '₱',
  numpadValue: '',
  discountVisible: false,
};

// ── Cart operations ────────────────────────────────────────

function addToCart(productId, name, price, stock) {
  const existing = State.cart.find(i => i.product_id === productId);
  if (existing) {
    existing.quantity++;
  } else {
    State.cart.push({ product_id: productId, name, unit_price: price, quantity: 1, stock });
  }
  renderCart();
  updateProductBadge(productId);
  flashCard(productId);
  animateCartBump();
  showToast(`${name} added to order`, 'success', 1800);
}

function removeFromCart(productId) {
  State.cart = State.cart.filter(i => i.product_id !== productId);
  renderCart();
  updateProductBadge(productId);
}

function changeQty(productId, delta) {
  const item = State.cart.find(i => i.product_id === productId);
  if (!item) return;
  const newQty = item.quantity + delta;
  if (newQty <= 0) { removeFromCart(productId); return; }
  item.quantity = newQty;
  renderCart();
  updateProductBadge(productId);
}

function clearCart() {
  if (State.cart.length === 0) return;
  State.cart = [];
  State.numpadValue = '';
  const cashInput = document.getElementById('cash-tendered');
  if (cashInput) cashInput.value = '';
  renderCart();
  // Clear all product badges
  document.querySelectorAll('.product-qty-badge').forEach(b => {
    b.style.display = 'none'; b.textContent = '0';
  });
  document.querySelectorAll('.product-card').forEach(c => c.classList.remove('in-cart'));
}

function getCartTotal() {
  const subtotal = State.cart.reduce((s, i) => s + i.unit_price * i.quantity, 0);
  const discount = getDiscount();
  return Math.max(0, subtotal - discount);
}

function getCartSubtotal() {
  return State.cart.reduce((s, i) => s + i.unit_price * i.quantity, 0);
}

function getDiscount() {
  const inp = document.getElementById('discount-input');
  return inp ? (parseFloat(inp.value) || 0) : 0;
}

function getCartItemCount() {
  return State.cart.reduce((s, i) => s + i.quantity, 0);
}

// ── Render cart ────────────────────────────────────────────

function renderCart() {
  const container   = document.getElementById('cart-items');
  const emptyState  = document.getElementById('cart-empty');
  const countBadge  = document.getElementById('cart-count');
  const subtotalEl  = document.getElementById('cart-subtotal');
  const totalEl     = document.getElementById('cart-total');
  const checkoutBtn = document.getElementById('btn-checkout');
  const checkoutTot = document.getElementById('checkout-total');

  const count    = getCartItemCount();
  const subtotal = getCartSubtotal();
  const discount = getDiscount();
  const total    = Math.max(0, subtotal - discount);

  countBadge.textContent   = count;
  subtotalEl.textContent   = fmt(subtotal);
  // Also update tablet drawer toggle count
  const tabCount = document.getElementById('cart-tab-count');
  if (tabCount) tabCount.textContent = count;
  totalEl.textContent      = fmt(total);
  if (checkoutTot) checkoutTot.textContent = fmt(total);
  validateCheckout();

  // Discount display
  const discRow = document.getElementById('discount-display-row');
  const discDisp = document.getElementById('cart-discount-display');
  if (discount > 0 && discRow) {
    discRow.style.display = '';
    discDisp.textContent  = `-${fmt(discount)}`;
  } else if (discRow) {
    discRow.style.display = 'none';
  }

  // Order number placeholder
  const orderNum = document.getElementById('cart-order-num');
  if (orderNum) orderNum.textContent = State.cart.length ? 'Pending...' : 'New Order';

  // Show/hide column headers
  const colHeaders = document.getElementById('cart-col-headers');
  if (colHeaders) colHeaders.style.display = State.cart.length > 0 ? 'grid' : 'none';

  if (State.cart.length === 0) {
    container.innerHTML = '';
    container.style.display = 'none';
    if (emptyState) emptyState.style.display = 'flex';
    return;
  }
  container.style.display = '';
  if (emptyState) emptyState.style.display = 'none';

  container.innerHTML = State.cart.map((item, idx) => `
    <div class="cart-item" data-id="${item.product_id}">
      <!-- Row: # + Name + Line Total -->
      <div class="ci-row-top">
        <button class="ci-remove" onclick="removeFromCart(${item.product_id})" title="Remove item">✕</button>
        <div class="ci-info">
          <span class="ci-name">${esc(item.name)}</span>
          <span class="ci-unit">${fmt(item.unit_price)}</span>
        </div>
        <span class="ci-subtotal">${fmt(item.unit_price * item.quantity)}</span>
      </div>
      <!-- Row: Qty controls -->
      <div class="ci-row-bottom">
        <div class="ci-qty-wrap">
          <button class="ci-qty-btn" onclick="changeQty(${item.product_id}, -1)">−</button>
          <span class="ci-qty-val">${item.quantity}</span>
          <button class="ci-qty-btn" onclick="changeQty(${item.product_id}, +1)">+</button>
        </div>
        <span class="ci-qty-label">× ${fmt(item.unit_price)} each</span>
      </div>
    </div>
  `).join('');

  updateQuickAmounts(total);
}

// ── Numpad ─────────────────────────────────────────────────

function numpadPress(key) {
  const display = document.getElementById('cash-tendered');
  if (!display) return;

  if (key === 'back') {
    State.numpadValue = State.numpadValue.slice(0, -1);
  } else if (key === '.') {
    if (!State.numpadValue.includes('.')) State.numpadValue += '.';
  } else {
    // Prevent more than 2 decimal places
    const parts = State.numpadValue.split('.');
    if (parts[1] && parts[1].length >= 2) return;
    if (State.numpadValue.length >= 8) return;
    State.numpadValue += key;
  }
  display.value = State.numpadValue;
}

function setCashAmount(val) {
  const display = document.getElementById('cash-tendered');
  if (!display) return;
  if (val === 'exact') {
    const total = getCartTotal();
    State.numpadValue = total.toFixed(2);
  } else {
    State.numpadValue = String(val);
  }
  display.value = State.numpadValue;
}

function updateQuickAmounts(total) {
  // Dynamic quick buttons already in HTML — just update 'exact'
}

// ── Payment method ─────────────────────────────────────────

function selectPaymentMethod(method) {
  State.paymentMethod = method;
  document.querySelectorAll('.pay-method-btn').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.method === method));

  // Show/hide numpad (cash only)
  const numpad = document.getElementById('numpad-wrap');
  if (numpad) numpad.style.display = method === 'cash' ? '' : 'none';

  // Show/hide GCash ref input
  const gcashWrap = document.getElementById('gcash-ref-wrap');
  if (gcashWrap) {
    gcashWrap.style.display = method === 'gcash' ? '' : 'none';
    if (method !== 'gcash') {
      const inp = document.getElementById('gcash-ref-input');
      if (inp) { inp.value = ''; inp.classList.remove('valid','invalid'); }
    }
  }

  // Update checkout button state
  validateCheckout();
}

function validateGcashRef() {
  const inp = document.getElementById('gcash-ref-input');
  if (!inp) return;
  const val = inp.value.trim();
  inp.classList.remove('valid', 'invalid');
  if (val.length >= 10) inp.classList.add('valid');
  else if (val.length > 0) inp.classList.add('invalid');
  validateCheckout();
}

function validateCheckout() {
  const btn = document.getElementById('btn-checkout');
  if (!btn) return;
  const hasItems = State.cart.length > 0;
  const gcashOk  = State.paymentMethod !== 'gcash' ||
    (document.getElementById('gcash-ref-input')?.value.trim().length >= 10);
  btn.disabled = !(hasItems && gcashOk);
}

// ── Discount toggle ────────────────────────────────────────

function toggleDiscount() {
  State.discountVisible = !State.discountVisible;
  const row = document.getElementById('cart-discount-row');
  if (row) row.style.display = State.discountVisible ? 'flex' : 'none';
  const btn = document.getElementById('btn-discount');
  if (btn) btn.classList.toggle('active', State.discountVisible);
  if (State.discountVisible) {
    const inp = document.getElementById('discount-input');
    if (inp) { inp.focus(); inp.value = ''; }
  } else {
    const inp = document.getElementById('discount-input');
    if (inp) inp.value = '0';
    renderCart();
  }
}

// ── Product filtering ──────────────────────────────────────

function filterByCategory(categoryId) {
  document.querySelectorAll('.cat-tab').forEach(tab =>
    tab.classList.toggle('active', tab.dataset.id === String(categoryId)));
  fetch(`/api/products?category=${categoryId || ''}`)
    .then(r => r.json())
    .then(products => renderProducts(products))
    .catch(() => showToast('Failed to load products', 'error'));
}

function renderProducts(products) {
  const grid = document.getElementById('product-grid');
  if (!grid) return;
  if (products.length === 0) {
    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:3rem;color:var(--muted)">
      <div style="font-size:2rem;margin-bottom:.5rem">🔍</div><p>No items found</p></div>`;
    return;
  }
  grid.innerHTML = products.map(p => {
    const out      = !p.is_available || p.stock <= 0;
    const cartItem = State.cart.find(i => i.product_id === p.id);
    const qty      = cartItem ? cartItem.quantity : 0;
    const inCart   = qty > 0;
    return `
    <div class="product-card ${out ? 'out-of-stock' : ''} ${inCart ? 'in-cart' : ''}"
         id="pcard-${p.id}"
         onclick="${out ? '' : `addToCart(${p.id}, '${escJs(p.name)}', ${p.price}, ${p.stock})`}">
      ${out ? '<span class="out-of-stock-label">Unavailable</span>' : ''}
      <div class="product-card-top">
        ${p.image
          ? `<img src="/static/${p.image}" style="width:44px;height:44px;object-fit:cover;border-radius:var(--r-sm);flex-shrink:0" alt="${esc(p.name)}">`
          : `<span class="product-cat-icon">${p.category_icon || '🍔'}</span>`
        }
        <div class="product-qty-badge" id="qty-${p.id}" style="${inCart ? '' : 'display:none'}">${qty}</div>
      </div>
      <span class="product-name">${esc(p.name)}</span>
      ${p.description ? `<span class="product-desc">${esc(p.description)}</span>` : ''}
      <span class="product-price">${fmt(p.price)}</span>
    </div>`;
  }).join('');
}

// ── Checkout ───────────────────────────────────────────────

async function checkout() {
  if (State.cart.length === 0) return;

  const cashInput   = document.getElementById('cash-tendered');
  const cashTendered = State.paymentMethod === 'cash' && cashInput
    ? parseFloat(cashInput.value) || null : null;

  if (State.paymentMethod === 'cash' && cashTendered !== null) {
    if (cashTendered < getCartTotal()) {
      showToast('Cash is less than total amount', 'error'); return;
    }
  }

  const btn = document.getElementById('btn-checkout');
  btn.disabled = true;
  btn.innerHTML = 'Processing…';

  try {
    const gcashRef = State.paymentMethod === 'gcash'
      ? (document.getElementById('gcash-ref-input')?.value.trim() || '')
      : '';

    const res = await fetch('/api/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cart:           State.cart.map(({ product_id, unit_price, quantity }) =>
                          ({ product_id, unit_price, quantity })),
        payment_method: State.paymentMethod,
        cash_tendered:  cashTendered,
        discount:       getDiscount(),
        gcash_ref:      gcashRef,
      }),
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      showToast(data.error || 'Checkout failed', 'error'); return;
    }

    showToast(`Order ${data.order_number} complete!`, 'success', 3000);
    closeCartDrawer();
    showReceipt(data);

  } catch (err) {
    showToast('Network error. Please try again.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `Charge <span id="checkout-total">${fmt(getCartTotal())}</span>`;
  }
}

// ── Receipt modal ──────────────────────────────────────────

function showReceipt(data) {
  const modal = document.getElementById('receipt-modal-backdrop');
  if (!modal) return;

  document.getElementById('receipt-order-num').textContent = data.order_number;
  document.getElementById('receipt-subtotal').textContent  = fmt(data.total + (data.discount || 0));
  document.getElementById('receipt-total').textContent     = fmt(data.total);

  // Discount row
  const discRow = document.getElementById('receipt-discount-row');
  const discEl  = document.getElementById('receipt-discount');
  if (data.discount && data.discount > 0) {
    discRow.style.display = '';
    discEl.textContent    = `-${fmt(data.discount)}`;
  } else {
    discRow.style.display = 'none';
  }

  // Items
  document.getElementById('receipt-items-list').innerHTML =
    data.items.map(i => `
      <div class="receipt-item">
        <span>${esc(i.product_name)} ×${i.quantity}</span>
        <span>${fmt(i.subtotal)}</span>
      </div>`).join('');

  // GCash ref
  const gcashRow = document.getElementById('receipt-gcash-row');
  const gcashEl  = document.getElementById('receipt-gcash-ref');
  if (gcashRow && gcashEl) {
    if (data.gcash_ref) {
      gcashRow.style.display = '';
      gcashEl.textContent    = data.gcash_ref;
    } else {
      gcashRow.style.display = 'none';
    }
  }

  // Change
  const changeWrap = document.getElementById('receipt-change-wrap');
  if (data.change !== null && data.change >= 0 && State.paymentMethod === 'cash') {
    changeWrap.style.display = '';
    document.getElementById('receipt-change').textContent = fmt(data.change);
  } else {
    changeWrap.style.display = 'none';
  }

  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeReceipt() {
  document.getElementById('receipt-modal-backdrop').classList.remove('open');
  document.body.style.overflow = '';
}

function newOrder() {
  closeReceipt();
  clearCart();
  State.numpadValue = '';
  const cashInput  = document.getElementById('cash-tendered');
  if (cashInput) cashInput.value = '';
  const gcashInput = document.getElementById('gcash-ref-input');
  if (gcashInput) { gcashInput.value = ''; gcashInput.classList.remove('valid','invalid'); }
  // Reset to cash payment
  selectPaymentMethod('cash');
  // Hide discount
  if (State.discountVisible) toggleDiscount();
}

// ── Product card helpers ───────────────────────────────────

function updateProductBadge(productId) {
  const badge = document.getElementById(`qty-${productId}`);
  const card  = document.getElementById(`pcard-${productId}`);
  const item  = State.cart.find(i => i.product_id === productId);
  if (!badge) return;
  if (item && item.quantity > 0) {
    badge.style.display = 'flex';
    badge.textContent   = item.quantity;
    if (card) card.classList.add('in-cart');
  } else {
    badge.style.display = 'none';
    if (card) card.classList.remove('in-cart');
  }
}

function flashCard(productId) {
  const card = document.getElementById(`pcard-${productId}`);
  if (!card) return;
  card.classList.remove('flash');
  void card.offsetWidth;
  card.classList.add('flash');
}

// ── Clock ──────────────────────────────────────────────────

function updateClock() {
  const el = document.getElementById('pos-clock');
  if (!el) return;
  const now = new Date();
  const h   = String(now.getHours()).padStart(2, '0');
  const m   = String(now.getMinutes()).padStart(2, '0');
  el.textContent = `${h}:${m}`;
}

// ── Keyboard shortcuts ─────────────────────────────────────

function initKeyboard() {
  document.addEventListener('keydown', e => {
    // '/' focuses search
    if (e.key === '/' && e.target.tagName !== 'INPUT') {
      e.preventDefault();
      document.getElementById('pos-search')?.focus();
    }
    // Escape clears search or closes receipt
    if (e.key === 'Escape') {
      const receipt = document.getElementById('receipt-modal-backdrop');
      if (receipt?.classList.contains('open')) { closeReceipt(); return; }
      const search = document.getElementById('pos-search');
      if (document.activeElement === search) { search.blur(); search.value = ''; filterByCategory(''); }
    }
    // Enter to checkout
    if (e.key === 'Enter' && e.ctrlKey) {
      const btn = document.getElementById('btn-checkout');
      if (!btn.disabled) checkout();
    }
  });
}

// ── Search debounce ────────────────────────────────────────

function initSearch() {
  const input = document.getElementById('pos-search');
  if (!input) return;
  let timer;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const q = input.value.trim();
      if (!q) {
        filterByCategory('');
        document.querySelectorAll('.cat-tab').forEach(t =>
          t.classList.toggle('active', t.dataset.id === ''));
      } else {
        fetch(`/api/products?q=${encodeURIComponent(q)}`)
          .then(r => r.json())
          .then(renderProducts)
          .catch(() => {});
      }
    }, 250);
  });
}

// ── Discount input watcher ─────────────────────────────────

function initDiscountInput() {
  const inp = document.getElementById('discount-input');
  if (inp) inp.addEventListener('input', () => renderCart());
}

// ── Toast ──────────────────────────────────────────────────

let toastTimer;
function showToast(msg, type = 'info') {
  let t = document.getElementById('pos-toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'pos-toast';
    t.style.cssText = `position:fixed;bottom:1.5rem;left:50%;transform:translateX(-50%) translateY(20px);
      background:var(--surface);border:1px solid var(--border-light);color:var(--text);
      padding:.6rem 1.1rem;border-radius:var(--radius);font-size:.82rem;font-family:var(--font-body);
      box-shadow:var(--shadow);z-index:9999;opacity:0;transition:opacity .22s,transform .22s;
      white-space:nowrap;pointer-events:none;`;
    document.body.appendChild(t);
  }
  const cols = { error:'var(--danger)', success:'var(--success)', warning:'var(--warning)', info:'var(--amber)' };
  t.style.borderColor = cols[type] || cols.info;
  t.textContent = msg;
  requestAnimationFrame(() => { t.style.opacity='1'; t.style.transform='translateX(-50%) translateY(0)'; });
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.style.opacity='0'; t.style.transform='translateX(-50%) translateY(20px)'; }, 2500);
}

function animateCartBump() {
  const b = document.getElementById('cart-count');
  if (!b) return;
  b.classList.remove('bump'); void b.offsetWidth; b.classList.add('bump');
}

// ── Utilities ──────────────────────────────────────────────

function fmt(amount) {
  return `${State.currency}${Number(amount).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escJs(s) {
  return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'");
}

// ── Init ───────────────────────────────────────────────────

// ── Cart drawer (tablet mode) ──────────────────────────────

let drawerOpen = false;

function toggleCartDrawer() {
  drawerOpen = !drawerOpen;
  const cart     = document.querySelector('.cart-pane');
  const backdrop = document.getElementById('cart-drawer-backdrop');
  if (cart)     cart.classList.toggle('drawer-open', drawerOpen);
  if (backdrop) backdrop.classList.toggle('show', drawerOpen);
  document.body.style.overflow = drawerOpen ? 'hidden' : '';
}

function closeCartDrawer() {
  drawerOpen = false;
  const cart     = document.querySelector('.cart-pane');
  const backdrop = document.getElementById('cart-drawer-backdrop');
  if (cart)     cart.classList.remove('drawer-open');
  if (backdrop) backdrop.classList.remove('show');
  document.body.style.overflow = '';
}

// Auto-close drawer after checkout on tablet
const _origNewOrder = typeof newOrder === 'function' ? newOrder : null;

document.addEventListener('DOMContentLoaded', () => {
  const meta = document.getElementById('currency-meta');
  if (meta) State.currency = meta.dataset.currency || '₱';

  selectPaymentMethod('cash');
  renderCart();
  validateCheckout();
  updateClock();
  setInterval(updateClock, 30000);
  initKeyboard();
  initSearch();
  initDiscountInput();
});