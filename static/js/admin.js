/* admin.js — Sabbis Burger Admin
   Modals, table search, Swift-style alerts & toasts
*/
'use strict';

// ══════════════════════════════════════════════════════════
//  TOAST NOTIFICATIONS
//  Usage: toast('Saved!', 'success')
//         toast('Something went wrong', 'error')
//         toast('Stock updated', 'success', 3000)
// ══════════════════════════════════════════════════════════

const TOAST_ICONS = {
  success: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7.5" fill="#22C55E" opacity=".15" stroke="#22C55E" stroke-width="1"/><path d="M5 8l2 2 4-4" stroke="#22C55E" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  error:   `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7.5" fill="#EF4444" opacity=".15" stroke="#EF4444" stroke-width="1"/><path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="#EF4444" stroke-width="1.75" stroke-linecap="round"/></svg>`,
  warning: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2L14.5 13.5H1.5L8 2z" fill="#F59E0B" opacity=".15" stroke="#F59E0B" stroke-width="1" stroke-linejoin="round"/><path d="M8 6.5v3" stroke="#F59E0B" stroke-width="1.75" stroke-linecap="round"/><circle cx="8" cy="11.5" r=".75" fill="#F59E0B"/></svg>`,
  info:    `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7.5" fill="#3B82F6" opacity=".15" stroke="#3B82F6" stroke-width="1"/><path d="M8 7.5v4" stroke="#3B82F6" stroke-width="1.75" stroke-linecap="round"/><circle cx="8" cy="5" r=".85" fill="#3B82F6"/></svg>`,
};

let _toastContainer = null;
function _getToastContainer() {
  if (!_toastContainer) {
    _toastContainer = document.createElement('div');
    _toastContainer.id = 'toast-container';
    _toastContainer.style.cssText = `
      position: fixed; top: 1rem; right: 1rem; z-index: 9999;
      display: flex; flex-direction: column; gap: .5rem;
      pointer-events: none;
    `;
    document.body.appendChild(_toastContainer);
  }
  return _toastContainer;
}

function toast(message, type = 'info', duration = 3500) {
  const container = _getToastContainer();
  const colors = {
    success: { bg: '#f0fdf4', border: 'rgba(34,197,94,.3)',  text: '#15803d' },
    error:   { bg: '#fef2f2', border: 'rgba(239,68,68,.3)',  text: '#b91c1c' },
    warning: { bg: '#fffbeb', border: 'rgba(245,158,11,.3)', text: '#92400e' },
    info:    { bg: '#eff6ff', border: 'rgba(59,130,246,.3)', text: '#1d4ed8' },
  };
  const c = colors[type] || colors.info;

  const el = document.createElement('div');
  el.style.cssText = `
    display: flex; align-items: center; gap: .625rem;
    background: ${c.bg}; border: 1.5px solid ${c.border}; color: ${c.text};
    padding: .625rem .875rem; border-radius: 10px;
    font-family: 'Nunito', sans-serif; font-size: .8125rem; font-weight: 700;
    box-shadow: 0 4px 20px rgba(0,0,0,.1), 0 1px 4px rgba(0,0,0,.06);
    pointer-events: all; cursor: pointer; user-select: none;
    max-width: 320px; min-width: 200px;
    opacity: 0; transform: translateX(16px);
    transition: opacity .22s cubic-bezier(.4,0,.2,1),
                transform .22s cubic-bezier(.4,0,.2,1);
  `;
  el.innerHTML = `${TOAST_ICONS[type] || TOAST_ICONS.info}<span style="flex:1">${message}</span>
    <span style="opacity:.45;font-size:.75rem;margin-left:.25rem">✕</span>`;
  el.onclick = () => dismissToast(el);

  container.appendChild(el);
  requestAnimationFrame(() => {
    el.style.opacity = '1';
    el.style.transform = 'translateX(0)';
  });

  setTimeout(() => dismissToast(el), duration);
}

function dismissToast(el) {
  el.style.opacity = '0';
  el.style.transform = 'translateX(16px)';
  setTimeout(() => el.remove(), 220);
}

// ══════════════════════════════════════════════════════════
//  SWIFT-STYLE CONFIRM DIALOG
//  Replaces native window.confirm() with a beautiful modal.
//  Usage:
//    showConfirm({
//      title: 'Delete Item',
//      message: 'This cannot be undone.',
//      type: 'danger',           // 'danger' | 'warning' | 'info'
//      confirmLabel: 'Delete',
//      onConfirm: () => { ... }
//    });
// ══════════════════════════════════════════════════════════

let _confirmEl = null;

function _buildConfirmEl() {
  if (_confirmEl) return _confirmEl;
  const el = document.createElement('div');
  el.id = 'swift-confirm-backdrop';
  el.style.cssText = `
    position: fixed; inset: 0;
    background: rgba(26,28,34,.55);
    backdrop-filter: blur(6px);
    z-index: 10000;
    display: flex; align-items: center; justify-content: center;
    padding: 1rem;
    opacity: 0; pointer-events: none;
    transition: opacity .2s cubic-bezier(.4,0,.2,1);
  `;
  el.innerHTML = `
    <div id="swift-confirm-box" style="
      background: #fff; border-radius: 18px;
      padding: 1.75rem; width: 100%; max-width: 360px;
      box-shadow: 0 24px 64px rgba(0,0,0,.18), 0 4px 16px rgba(0,0,0,.08);
      transform: scale(.94) translateY(8px);
      transition: transform .22s cubic-bezier(.34,1.56,.64,1);
      font-family: 'Nunito', sans-serif;
    ">
      <div id="sc-icon-wrap" style="
        width: 52px; height: 52px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto .875rem; font-size: 1.375rem;
      "></div>
      <h3 id="sc-title" style="
        text-align: center; font-size: 1rem; font-weight: 800;
        color: #1A1C22; letter-spacing: -.02em; margin-bottom: .375rem;
      "></h3>
      <p id="sc-message" style="
        text-align: center; font-size: .8125rem; color: #4A4F5C;
        font-weight: 500; line-height: 1.5; margin-bottom: 1.25rem;
      "></p>
      <div style="display: flex; gap: .5rem;">
        <button id="sc-cancel" style="
          flex: 1; padding: .625rem; border-radius: 10px;
          border: 1.5px solid #E8E2D9; background: #F7F5F2;
          color: #4A4F5C; font-family: 'Nunito', sans-serif;
          font-size: .875rem; font-weight: 700; cursor: pointer;
          transition: all .12s;
        ">Cancel</button>
        <button id="sc-confirm" style="
          flex: 1; padding: .625rem; border-radius: 10px;
          border: none; color: #fff;
          font-family: 'Nunito', sans-serif;
          font-size: .875rem; font-weight: 800; cursor: pointer;
          transition: all .12s;
        ">Confirm</button>
      </div>
    </div>
  `;

  // Close on backdrop click
  el.addEventListener('click', e => {
    if (e.target === el) closeConfirm();
  });

  document.getElementById('sc-cancel')?.addEventListener('click', closeConfirm);
  document.body.appendChild(el);
  _confirmEl = el;
  return el;
}

function showConfirm({ title, message, type = 'danger', confirmLabel = 'Confirm', cancelLabel = 'Cancel', onConfirm }) {
  const el    = _buildConfirmEl();
  const box   = document.getElementById('swift-confirm-box');
  const icon  = document.getElementById('sc-icon-wrap');
  const tEl   = document.getElementById('sc-title');
  const mEl   = document.getElementById('sc-message');
  const cfBtn = document.getElementById('sc-confirm');
  const cnBtn = document.getElementById('sc-cancel');

  const styles = {
    danger:  { icon: '🗑️',  bg: 'rgba(239,68,68,.1)',   color: '#EF4444' },
    warning: { icon: '⚠️',  bg: 'rgba(245,158,11,.1)',  color: '#F59E0B' },
    info:    { icon: 'ℹ️',  bg: 'rgba(59,130,246,.1)',  color: '#3B82F6' },
    void:    { icon: '↩️',  bg: 'rgba(239,68,68,.1)',   color: '#EF4444' },
  };
  const s = styles[type] || styles.danger;

  icon.style.background  = s.bg;
  icon.textContent       = s.icon;
  tEl.textContent        = title;
  mEl.textContent        = message;
  cfBtn.textContent      = confirmLabel;
  cfBtn.style.background = s.color;
  cfBtn.style.boxShadow  = `0 4px 14px ${s.bg}`;
  cnBtn.textContent      = cancelLabel;

  // Wire confirm button
  cfBtn.onclick = () => {
    closeConfirm();
    if (onConfirm) onConfirm();
  };

  // Show
  el.style.pointerEvents = 'all';
  requestAnimationFrame(() => {
    el.style.opacity = '1';
    box.style.transform = 'scale(1) translateY(0)';
  });

  // Keyboard
  const onKey = e => {
    if (e.key === 'Enter')  { cfBtn.click(); document.removeEventListener('keydown', onKey); }
    if (e.key === 'Escape') { closeConfirm(); document.removeEventListener('keydown', onKey); }
  };
  document.addEventListener('keydown', onKey);
}

function closeConfirm() {
  if (!_confirmEl) return;
  const box = document.getElementById('swift-confirm-box');
  _confirmEl.style.opacity = '0';
  _confirmEl.style.pointerEvents = 'none';
  if (box) box.style.transform = 'scale(.94) translateY(8px)';
}

// ══════════════════════════════════════════════════════════
//  CONFIRM DELETE — replaces old window.confirm version
//  Now uses showConfirm() instead of native dialog
// ══════════════════════════════════════════════════════════

function confirmDelete(formId, message, type = 'danger') {
  const parts   = (message || 'Delete this item?').split('?');
  const title   = parts[0].replace(/^(Delete|Remove|Void)\s+/i, '').trim();
  const verb    = (message || '').match(/^(void|remove|delete)/i)?.[0] || 'Delete';
  const isVoid  = /void/i.test(verb);

  showConfirm({
    title:        isVoid ? 'Void Transaction' : `${verb} Item`,
    message:      message || 'This action cannot be undone.',
    type:         isVoid ? 'void' : 'danger',
    confirmLabel: isVoid ? 'Yes, Void It' : `Yes, ${verb} It`,
    cancelLabel:  'Cancel',
    onConfirm:    () => {
      const form = document.getElementById(formId);
      if (form) form.submit();
    }
  });
  return false;
}

// ══════════════════════════════════════════════════════════
//  FLASH MESSAGE → AUTO TOAST
//  Converts Flask flash messages into toasts on page load
// ══════════════════════════════════════════════════════════

function flashToToasts() {
  document.querySelectorAll('.alert').forEach(alert => {
    const type = alert.classList.contains('alert-success') ? 'success'
               : alert.classList.contains('alert-error')   ? 'error'
               : alert.classList.contains('alert-warning')  ? 'warning'
               : 'info';
    const msg = alert.textContent.trim().replace(/^[⚠️✅🔔ℹ️]\s*/u, '');
    if (msg) toast(msg, type, 4500);
    alert.remove(); // remove original HTML alert
  });
}

// ══════════════════════════════════════════════════════════
//  MODAL HELPERS
// ══════════════════════════════════════════════════════════

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
  setTimeout(() => {
    const first = modal.querySelector('input, select, textarea');
    if (first) first.focus();
  }, 120);
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  modal.classList.remove('open');
  document.body.style.overflow = '';
}

function openEditModal(modalId, data) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  Object.entries(data).forEach(([key, value]) => {
    const el = modal.querySelector(`[name="${key}"]`);
    if (!el) return;
    el.type === 'checkbox' ? (el.checked = Boolean(Number(value))) : (el.value = value);
  });
  const form = modal.querySelector('form');
  if (form && data.id) {
    // Replace placeholder ID (0) with real ID, no trailing slash
    form.action = form.action
      .replace(/\/\d+(\/?)$/, `/${data.id}`);
  }
  openModal(modalId);
}

function initModalBackdropClose() {
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', e => {
      if (e.target === backdrop) {
        backdrop.classList.remove('open');
        document.body.style.overflow = '';
      }
    });
  });
}

function initEscapeClose() {
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    document.querySelectorAll('.modal-backdrop.open').forEach(m => {
      m.classList.remove('open');
      document.body.style.overflow = '';
    });
  });
}

// ══════════════════════════════════════════════════════════
//  TABLE SEARCH
// ══════════════════════════════════════════════════════════

function initTableSearch(inputId, tableId) {
  const input = document.getElementById(inputId);
  const table = document.getElementById(tableId);
  if (!input || !table) return;
  input.addEventListener('input', () => {
    const q = input.value.toLowerCase().trim();
    table.querySelectorAll('tbody tr').forEach(row => {
      row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });
}

// ══════════════════════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  initModalBackdropClose();
  initEscapeClose();
  flashToToasts();   // convert Flask flash → toast
});