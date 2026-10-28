// Visible alert / error / toast text on the current page. Loaded by
// browser/error_text.py via page.evaluate(). Returns an array of strings.
//
// Read-only, and PRIVACY-FIRST: the page's own error text is evidence, but anything the tester
// typed is not. So (1) input/textarea/select/option, scripts and secret-masked nodes are removed
// from every excerpt, (2) an element that contains a form control is a form wrapper, not a
// message, and is skipped, and (3) every non-trivial value currently held by an input on the
// page is blanked out of the text -- a server that echoes the typed email or password back in
// its error does not leak it into evidence.
(() => {
  const SELECTORS = [
    '[role="alert"]', '[role="alertdialog"]', '[role="status"]',
    '[aria-live="assertive"]', '[aria-live="polite"]',
    '[class*="error" i]', '[class*="alert" i]', '[class*="toast" i]',
    '[class*="snackbar" i]', '[class*="invalid" i]', '[class*="danger" i]',
    '[class*="warning" i]', '[data-sonner-toast]', '[id*="error" i]',
  ].join(',');
  const DROP = 'input,textarea,select,option,script,style,noscript,[data-autotester-secret]';
  const CONTROLS = 'input,textarea,select';
  const MIN_VALUE = 3;
  const LIMIT = 40;

  function isVisible(el) {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return false;
    const style = window.getComputedStyle(el);
    return style.visibility !== 'hidden' && style.display !== 'none'
      && parseFloat(style.opacity || '1') > 0;
  }

  const typed = [];
  document.querySelectorAll(CONTROLS).forEach((el) => {
    const v = (el.value || '').trim();
    if (v.length >= MIN_VALUE) typed.push(v);
  });
  typed.sort((a, b) => b.length - a.length);

  function messageText(el) {
    const clone = el.cloneNode(true);
    clone.querySelectorAll(DROP).forEach((n) => n.remove());
    let text = (clone.textContent || '').replace(/\s+/g, ' ').trim();
    for (const v of typed) text = text.split(v).join('[input]');
    return text;
  }

  const out = [];
  for (const el of document.querySelectorAll(SELECTORS)) {
    if (out.length >= LIMIT) break;
    if (el === document.body || el === document.documentElement) continue;
    if (el.matches(DROP) || el.querySelector(CONTROLS)) continue;
    if (!isVisible(el)) continue;
    const text = messageText(el);
    if (text) out.push(text);
  }
  return out;
})()
