(function () {
  function buildModal() {
    if (document.getElementById('policy-modal')) return;
    var wrap = document.createElement('div');
    wrap.innerHTML =
      '<div id="policy-modal" role="dialog" aria-modal="true" aria-labelledby="policy-modal-title"' +
      '     style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:10000;overflow-y:auto;padding:1.5rem">' +
      '  <div style="background:#fff;border-radius:14px;width:100%;max-width:720px;margin:2rem auto;' +
      '              box-shadow:0 20px 60px rgba(0,0,0,.3);overflow:hidden">' +
      '    <div style="display:flex;align-items:center;justify-content:space-between;' +
      '                padding:.875rem 1.25rem;border-bottom:1.5px solid #e8e2d9;' +
      '                position:sticky;top:0;background:#fff;z-index:1">' +
      '      <strong id="policy-modal-title" style="font-size:1rem;color:#1a1c22"></strong>' +
      '      <button id="policy-modal-close" onclick="closePolicyModal()" aria-label="Close dialog"' +
      '              style="background:none;border:none;cursor:pointer;font-size:1.125rem;' +
      '                     color:#62687a;line-height:1;padding:.3rem .6rem;border-radius:6px">' +
      '        &#x2715;' +
      '      </button>' +
      '    </div>' +
      '    <div id="policy-modal-body" style="padding:1.5rem 1.75rem;max-height:72vh;overflow-y:auto"></div>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(wrap.firstElementChild);

    document.getElementById('policy-modal').addEventListener('click', function (e) {
      if (e.target === this) closePolicyModal();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closePolicyModal();
    });
  }

  var _prevFocus = null;

  window.openPolicyModal = function (url, title) {
    buildModal();
    _prevFocus = document.activeElement;

    var modal   = document.getElementById('policy-modal');
    var body    = document.getElementById('policy-modal-body');
    var titleEl = document.getElementById('policy-modal-title');

    titleEl.textContent = title;
    body.innerHTML = '<p style="text-align:center;padding:3rem 1rem;color:#8a8f9c;font-size:.9rem">Loading…</p>';
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    document.getElementById('policy-modal-close').focus();

    var sep = url.indexOf('?') === -1 ? '?' : '&';
    fetch(url + sep + 'partial=1')
      .then(function (r) { return r.text(); })
      .then(function (html) { body.innerHTML = html; body.scrollTop = 0; })
      .catch(function () {
        body.innerHTML = '<p style="color:#991b1b;padding:1rem">Failed to load content. Please try again.</p>';
      });
  };

  window.closePolicyModal = function () {
    var modal = document.getElementById('policy-modal');
    if (!modal) return;
    modal.style.display = 'none';
    document.body.style.overflow = '';
    if (_prevFocus) _prevFocus.focus();
  };
})();
