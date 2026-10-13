"""Click readiness: scroll into view, wait out overlays, expand a collapsed parent menu.

The real PathLynks run lost four cases to a 30 s Playwright timeout: the target link sat in a
collapsed sidebar submenu and the parent `<button class="menu-item">` intercepted the pointer.
`ready_to_click` probes actionability with a short trial click, and only when that fails does it
(1) scroll the target into view, (2) retry, (3) expand the parent menu once -- by the
`aria-expanded="false"` toggle, else the element covering the target, else the nearest preceding
button -- and (4) retry. It NEVER force-clicks; a target still blocked raises the original
error, and every expansion is returned so the caller records it as evidence.
"""

from __future__ import annotations

import contextlib
from typing import Any

PROBE_MS = 2500
_MARK = "data-at-expander"
_FIND_EXPANDER = f"""el => {{
  const TOGGLE = 'button,[role=button],[aria-expanded],[aria-haspopup],summary';
  const mark = (c) => {{ c.setAttribute('{_MARK}', '1'); return true; }};
  const cands = [];
  const r = el.getBoundingClientRect();
  const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  if (r.width > 0 && r.height > 0 && top && !el.contains(top) && !top.contains(el)) {{
    const t = top.closest(TOGGLE); if (t && !t.contains(el)) cands.push(t);
  }}
  for (let a = el; a && a !== document.body; a = a.parentElement) {{
    if (a !== el && a.getAttribute('aria-expanded') === 'false') cands.push(a);
    for (let s = a.previousElementSibling; s; s = s.previousElementSibling) {{
      if (s.matches(TOGGLE)) {{ cands.push(s); break; }}
    }}
  }}
  const pick = cands.find(c => c.getAttribute('aria-expanded') === 'false') || cands[0];
  if (!pick) return null;
  mark(pick);
  return (pick.tagName.toLowerCase() + (pick.className ? '.' + String(pick.className).trim()
    .split(/\s+/)[0] : '') + ' ' + (pick.textContent || '').trim().slice(0, 40)).trim();
}}"""


def _probe(locator: Any) -> bool:
    try:
        locator.click(trial=True, timeout=PROBE_MS)
        return True
    except Exception:
        return False


def ready_to_click(page: Any, locator: Any) -> list[str]:
    """Make `locator` clickable if it can be done honestly; return what was done (may be empty).

    Returns [] when the target is already actionable or nothing safe could be done -- the real
    click that follows then succeeds or raises Playwright's own error."""
    if _probe(locator):
        return []
    done: list[str] = []
    with contextlib.suppress(Exception):
        locator.scroll_into_view_if_needed(timeout=PROBE_MS)
        done.append("scrolled target into view")
    if done and _probe(locator):
        return done
    try:
        described = locator.evaluate(_FIND_EXPANDER)
    except Exception:
        return done
    if not described:
        return done
    marked = page.locator(f"[{_MARK}]").first
    try:
        marked.hover(timeout=PROBE_MS)
        if not _probe(locator):
            marked.click(timeout=PROBE_MS)
        done.append(f"expanded parent menu via {described}")
    except Exception:
        pass
    finally:
        with contextlib.suppress(Exception):
            marked.evaluate(f"el => el.removeAttribute('{_MARK}')", timeout=PROBE_MS)
    _probe(locator)
    return done
