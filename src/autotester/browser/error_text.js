// Visible alert / error / toast text on the current page. Loaded by
// browser/error_text.py via page.evaluate(). Returns an array of strings.
//
// Read-only, and PRIVACY-FIRST: the page's own error text is evidence, but anything the tester
// typed is not. So (1) input/textarea/select/option, scripts and secret-masked nodes are removed
// from every excerpt, (2) an element that contains a form control is a form wrapper, not a
// message, and is skipped, and (3) every non-trivial value currently held by an input or textarea
// on the page, including inside OPEN shadow roots, is blanked out of the text -- a server that
// echoes the typed email or password back in its error does not leak it into evidence. Typed
// values and page text are whitespace-normalised the same way and compared by a Unicode folded
// key (case, NFC/NFD, sharp s, Kelvin sign, full-width forms) with a plain indexOf scan, so a
// huge typed value cannot throw. A <br> or block boundary counts as a space.
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
  const SEP = '\uE000'; // marks an inserted <br>/block separator until collapse() reads it
  const BLOCKS = 'br,p,div,li,ul,ol,dl,dt,dd,tr,td,th,table,section,article,header,footer,'
    + 'h1,h2,h3,h4,h5,h6,blockquote,pre,hr,form,fieldset';

  // Matching key: NFKD, combining marks dropped, upper then lower case (sharp s -> ss, Kelvin
  // sign -> k, full-width -> ASCII). It can change length, so foldMap() keeps, per folded
  // code unit, the [start, end) offsets (in the original string) of the character it came from.
  const fold = (ch) => ch.normalize('NFKD').replace(/\p{M}/gu, '').toUpperCase().toLowerCase();
  function foldMap(text) {
    let folded = '';
    const starts = [];
    const ends = [];
    let pos = 0;
    for (const ch of text) {
      const f = fold(ch);
      for (let i = 0; i < f.length; i++) {
        starts.push(pos);
        ends.push(pos + ch.length);
      }
      folded += f;
      pos += ch.length;
    }
    return { folded, starts, ends };
  }

  function controlsIn(root, acc) {
    root.querySelectorAll(CONTROLS).forEach((el) => acc.push(el));
    root.querySelectorAll('*').forEach((host) => {
      if (host.shadowRoot) controlsIn(host.shadowRoot, acc);
    });
    return acc;
  }

  const typed = [];
  for (const el of controlsIn(document, [])) {
    const v = foldMap(norm(el.value)).folded;
    if (v.length >= MIN_VALUE && !typed.includes(v)) typed.push(v);
  }

  // Plain indexOf scan (no RegExp, so a huge typed value cannot throw). Matches are collected as
  // [start, end) ranges in the ORIGINAL text, so one blanked value is never re-matched inside the
  // marker of another; only overlapping ranges merge.
  // Typed-value ranges [start, end) in `view`, translated to `text` offsets through `map`
  // (map[i] = offset in `text` of view[i]; null when the view IS the text).
  function spansIn(view, map) {
    const { folded, starts, ends } = foldMap(view);
    const spans = [];
    for (const v of typed) {
      for (let at = folded.indexOf(v); at !== -1; at = folded.indexOf(v, at + v.length)) {
        const [from, to] = [starts[at], ends[at + v.length - 1]];
        spans.push(map ? [map[from], map[to - 1] + 1] : [from, to]);
      }
    }
    return spans;
  }

  // `text` is the message with whitespace collapsed; gap[i] is true where the space at text[i]
  // was only a <br>/block separator we inserted. A typed value is matched against `text` AND
  // against `text` with those inserted spaces removed (a value with no space that the page split
  // across blocks, `<p>Alice</p><p>99</p>`), so both echoes are blanked.
  // Plain indexOf scan (no RegExp, so a huge typed value cannot throw). Ranges are in the ORIGINAL
  // text, so one blanked value is never re-matched inside the marker of another; only overlapping
  // ranges merge.
  function blank(text, gap) {
    const map = [];
    let joined = '';
    for (let i = 0; i < text.length; i++) {
      if (gap[i]) continue;
      joined += text[i];
      map.push(i);
    }
    const spans = spansIn(text, null);
    if (joined.length !== text.length) for (const sp of spansIn(joined, map)) spans.push(sp);
    spans.sort((a, b) => a[0] - b[0] || b[1] - a[1]);
    let out = '';
    let last = 0;
    for (const [start, end] of spans) {
      if (start < last) {
        if (end > last) last = end;
        continue;
      }
      out += text.slice(last, start) + '[input]';
      last = end;
    }
    return out + text.slice(last);
  }

  // Same result as norm(raw with SEP read as a space), plus gap[] (see blank()).
  function collapse(raw) {
    let text = '';
    const gap = [];
    let real = false;
    let sep = false;
    for (const ch of raw) {
      if (ch === SEP) { sep = true; continue; }
      if (/\s/.test(ch)) { real = true; continue; }
      if (text && (real || sep)) { text += ' '; gap.push(!real); }
      real = false;
      sep = false;
      text += ch;
      for (let i = 0; i < ch.length; i++) gap.push(false);
    }
    return { text, gap };
  }

  function messageText(el) {
    const clone = el.cloneNode(true);
    clone.querySelectorAll(DROP).forEach((n) => n.remove());
    // a <br> or block boundary is a visual separator: give it a space so text on either side
    // is neither run together nor able to hide a typed value split across lines
    clone.querySelectorAll(BLOCKS).forEach((n) => {
      if (n.localName === 'br' || n.localName === 'hr') n.replaceWith(SEP);
      else { n.prepend(SEP); n.append(SEP); }
    });
    const { text, gap } = collapse(clone.textContent);
    return blank(text, gap);
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
