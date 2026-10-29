// Enumerate interactive elements on the current page. Loaded by
// browser/observe.py via page.evaluate(). Returns an array of
// {role, name, selector, enabled, visible, obscured, href, is_form_submit, in_row,
// target_blank, tag, type, field_label} objects, one per interactive element found.
//
// Selector priority: data-testid > a stable (non-generated-looking) #id >
// [aria-label] > a role+name locator with an nth index > an xpath fallback.
// "in_row" excludes an element from screen-identity's structural signature
// (Track B2) when it sits inside a table row / list item with siblings --
// two list pages differing only in row data should be one screen.
(() => {
  function isVisible(el) {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return false;
    const style = window.getComputedStyle(el);
    return style.visibility !== "hidden" && style.display !== "none";
  }

  // AT-227: CSS visibility is not reachability. A control under a modal veil
  // has a non-zero rect and no `display:none`/`visibility:hidden` -- every
  // measure isVisible() knows says "visible" -- and a human cannot click it.
  // Ask the browser who is actually on top at the control's centre instead.
  function isObscured(el) {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return false;
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    // elementFromPoint returns null for ANY point outside the viewport, so a
    // below-the-fold control would come back "obscured" and the crawl would
    // shrink instead of widening. Unknown is not obscured -- this probe only
    // ever removes a candidate, so it must fail open.
    if (x < 0 || y < 0 || x > window.innerWidth || y > window.innerHeight) return false;
    const top = document.elementFromPoint(x, y);
    if (!top) return false;
    // `top` inside `el` (an icon in a button) or `el` inside `top` (a wrapper
    // reported because the control is pointer-events:none) are both the
    // element itself, not something covering it.
    return !(el === top || el.contains(top) || top.contains(el));
  }

  function roleOf(el) {
    const explicit = el.getAttribute("role");
    if (explicit) return explicit;
    const tag = el.tagName.toLowerCase();
    if (tag === "a" && el.hasAttribute("href")) return "link";
    if (tag === "button") return "button";
    if (tag === "input") {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      if (type === "submit" || type === "button") return "button";
      if (type === "checkbox") return "checkbox";
      if (type === "radio") return "radio";
      return "textbox";
    }
    if (tag === "select") return "combobox";
    if (tag === "textarea") return "textbox";
    if (el.hasAttribute("onclick") || el.tabIndex >= 0) return "button";
    return tag;
  }

  function nameOf(el) {
    const ariaLabel = el.getAttribute("aria-label");
    if (ariaLabel) return ariaLabel.trim();
    const labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      const ref = document.getElementById(labelledBy);
      if (ref && ref.innerText) return ref.innerText.trim().slice(0, 60);
    }
    const title = el.getAttribute("title");
    if (title) return title.trim();
    const text = (el.innerText || "").trim();
    if (text) return text.slice(0, 60);
    const alt = el.querySelector && el.querySelector("img[alt]");
    if (alt) return alt.getAttribute("alt").trim();
    const value = el.getAttribute("value");
    if (value) return value.trim();
    return "";
  }

  // crawl-guidance G3: a data-bearing control's NAME can be its value, shown text or option text
  // (nameOf), which must never leave the machine. This reports its label sources only:
  // aria-label, aria-labelledby (never the control itself or what contains it), an associated
  // <label> (control text removed), a placeholder. null = not a data field. Fields: native
  // input/textarea/select, contenteditable, the ARIA value widgets (combobox, textbox, searchbox,
  // spinbutton, listbox, option, slider) and a button that opens a listbox/tree/grid/dialog
  // (MUI, Ant, react-select). Additive: nameOf, selectors and every other key are unchanged.
  const FIELD_ROLES = ["combobox", "textbox", "searchbox", "spinbutton", "listbox", "option",
    "slider"];
  const FIELD_POPUPS = ["listbox", "tree", "grid", "true", "dialog"];
  function fieldLabelOf(el, tag, type) {
    const caption = ["submit", "button", "reset", "image"].includes(type);
    const role = (el.getAttribute("role") || "").trim().toLowerCase().split(/\s+/)[0];
    const popup = (el.getAttribute("aria-haspopup") || "").trim().toLowerCase();
    const field = (["input", "textarea", "select"].includes(tag) && !caption) ||
      el.isContentEditable || FIELD_ROLES.includes(role) || FIELD_POPUPS.includes(popup);
    if (!field) return null;
    const aria = el.getAttribute("aria-label");
    if (aria && aria.trim()) return aria.trim().slice(0, 60);
    const named = (el.getAttribute("aria-labelledby") || "").split(/\s+/)
      .map((id) => document.getElementById(id))
      .filter((n) => n && n !== el && !n.contains(el) && !el.contains(n))
      .map((n) => (n.innerText || "").trim()).filter(Boolean).join(" ");
    if (named) return named.slice(0, 60);
    const label = el.labels && el.labels[0];
    if (label) {
      const copy = label.cloneNode(true);
      copy.querySelectorAll("input, select, textarea, option").forEach((n) => n.remove());
      const text = (copy.textContent || "").trim().replace(/\s+/g, " ");
      if (text) return text.slice(0, 60);
    }
    const hint = el.getAttribute("placeholder");
    return hint && hint.trim() ? hint.trim().slice(0, 60) : "";
  }

  function isGeneratedId(id) {
    return /^[0-9]+$/.test(id) || /[0-9a-f]{8}/.test(id) || id.length > 40;
  }

  const seen = new Map(); // role|name -> count, for nth disambiguation
  function selectorFor(el, role, name) {
    const testId = el.getAttribute("data-testid");
    if (testId) return `[data-testid="${testId}"]`;
    if (el.id && !isGeneratedId(el.id)) return `#${el.id}`;
    const ariaLabel = el.getAttribute("aria-label");
    if (ariaLabel) return `[aria-label="${ariaLabel}"]`;
    const key = `${role}|${name}`;
    const nth = seen.get(key) || 0;
    seen.set(key, nth + 1);
    if (name) return `role=${role}[name="${name}"] >> nth=${nth}`;
    // last resort: an xpath by tag + index among same-tag siblings
    let path = "";
    let node = el;
    while (node && node.nodeType === 1 && node !== document.body) {
      let index = 1;
      let sibling = node.previousElementSibling;
      while (sibling) {
        if (sibling.tagName === node.tagName) index += 1;
        sibling = sibling.previousElementSibling;
      }
      path = `/${node.tagName.toLowerCase()}[${index}]${path}`;
      node = node.parentElement;
    }
    return `xpath=/html/body${path}`;
  }

  function inRow(el) {
    let node = el.parentElement;
    let depth = 0;
    while (node && depth < 6) {
      const tag = node.tagName.toLowerCase();
      const role = node.getAttribute("role");
      if (tag === "tr" || tag === "li" || role === "row" || role === "listitem") {
        const siblingCount = node.parentElement ? node.parentElement.children.length : 0;
        return siblingCount > 3;
      }
      node = node.parentElement;
      depth += 1;
    }
    return false;
  }

  const SELECTOR = "a, button, input, select, textarea, [onclick], [tabindex]";
  const elements = Array.from(document.querySelectorAll(SELECTOR));
  const out = [];
  for (const el of elements) {
    const role = roleOf(el);
    const name = nameOf(el);
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute("type") || "").toLowerCase();
    out.push({
      role: role,
      name: name,
      selector: selectorFor(el, role, name),
      enabled: !el.disabled,
      visible: isVisible(el),
      obscured: isObscured(el),
      href: el.getAttribute("href") || null,
      is_form_submit: tag === "button" && (type === "" || type === "submit") &&
        !!el.closest("form") || (tag === "input" && type === "submit"),
      in_row: inRow(el),
      target_blank: el.getAttribute("target") === "_blank",
      tag: tag,
      type: tag === "input" ? (el.type || "").toLowerCase() : "",
      field_label: fieldLabelOf(el, tag, type),
    });
  }
  return out;
})();
