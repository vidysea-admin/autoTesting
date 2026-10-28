// Visible alert / error / toast text on the current page. Loaded by
// browser/error_text.py via page.evaluate(). Returns an array of strings.
//
// Read-only, and PRIVACY-FIRST: the page's own error text is evidence, but anything the tester
// typed is not. So (1) input/textarea/select/option, scripts and secret-masked nodes are removed
// from every excerpt, (2) an element that contains a form control is a form wrapper, not a
// message, and is skipped, and (3) every non-trivial value currently held by an input or textarea
// on the page, including inside OPEN shadow roots, is blanked out of the text -- a server that
// echoes the typed email or password back in its error does not leak it into evidence. Typed
// values and page text are whitespace-normalised the same way and matched case-insensitively.
//
// Hard limits (documented, not hidden): (a) contenteditable regions are never read as message
// text (their content is whatever the user typed); (b) text that lives inside an iframe is never
// read -- iframes (and their fallback content) are dropped, and `document.querySelectorAll` does
// not pierce them -- so a value typed INSIDE an iframe or a CLOSED shadow root is not collected
// either; (c) values shorter than MIN_VALUE chars are not blanked.
(() => {
  const SELECTORS = [
    '[role="alert"]', '[role="alertdialog"]', '[role="status"]',
    '[aria-live="assertive"]', '[aria-live="polite"]',
    '[class*="error" i]', '[class*="alert" i]', '[class*="toast" i]',
    '[class*="snackbar" i]', '[class*="invalid" i]', '[class*="danger" i]',
    '[class*="warning" i]', '[data-sonner-toast]', '[id*="error" i]',
  ].join(',');
  const EDITABLE = '[contenteditable]:not([contenteditable="false"])';
  const DROP = 'input,textarea,select,option,script,style,noscript,iframe,frame,object,embed,'
    + '[data-autotester-secret],' + EDITABLE;
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

  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  function controlsIn(root, acc) {
    root.querySelectorAll(CONTROLS).forEach((el) => acc.push(el));
    root.querySelectorAll('*').forEach((host) => {
      if (host.shadowRoot) controlsIn(host.shadowRoot, acc);
    });
    return acc;
  }

  const typed = [];
  for (const el of controlsIn(document, [])) {
    const v = norm(el.value);
    if (v.length >= MIN_VALUE && !typed.includes(v)) typed.push(v);
  }
  typed.sort((a, b) => b.length - a.length);
  const blankers = typed.map((v) => new RegExp(escapeRe(v), 'gi'));

  function messageText(el) {
    const clone = el.cloneNode(true);
    clone.querySelectorAll(DROP).forEach((n) => n.remove());
    let text = norm(clone.textContent);
    for (const re of blankers) text = text.replace(re, '[input]');
    return text;
  }

  const out = [];
  for (const el of document.querySelectorAll(SELECTORS)) {
    if (out.length >= LIMIT) break;
    if (el === document.body || el === document.documentElement) continue;
    if (el.matches(DROP) || el.isContentEditable || el.querySelector(CONTROLS)) continue;
    if (!isVisible(el)) continue;
    const text = messageText(el);
    if (text) out.push(text);
  }
  return out;
})()
