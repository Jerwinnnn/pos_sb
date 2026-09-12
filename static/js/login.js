/* ─────────────────────────────────────────────────────────
   login.js — Login page interactivity
───────────────────────────────────────────────────────── */

'use strict';

/**
 * Toggle password field visibility.
 * Called by the eye button in login.html.
 */
function togglePassword() {
  const pwInput = document.getElementById('password');
  const toggleBtn = document.querySelector('.toggle-pw');

  if (pwInput.type === 'password') {
    pwInput.type = 'text';
    toggleBtn.textContent = '🙈';
    toggleBtn.setAttribute('aria-label', 'Hide password');
  } else {
    pwInput.type = 'password';
    toggleBtn.textContent = '👁';
    toggleBtn.setAttribute('aria-label', 'Show password');
  }
}

/**
 * Fill in credentials from the hint section.
 * Called by clicking a credential row.
 */
function fillCredentials(username, password) {
  document.getElementById('username').value = username;
  document.getElementById('password').value = password;
  document.getElementById('password').type = 'password';
  document.querySelector('.toggle-pw').textContent = '👁';
}

/**
 * Auto-dismiss flash messages after 4 seconds.
 */
function autoDismissAlerts() {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity .5s, max-height .5s';
      alert.style.opacity = '0';
      alert.style.maxHeight = '0';
      alert.style.overflow = 'hidden';
      alert.style.marginBottom = '0';
      alert.style.padding = '0';
      setTimeout(() => alert.remove(), 500);
    }, 4000);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  autoDismissAlerts();

  // Focus username field on load if empty
  const usernameInput = document.getElementById('username');
  if (usernameInput && !usernameInput.value) {
    usernameInput.focus();
  }
});