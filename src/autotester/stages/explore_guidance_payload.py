"""The pure half of crawl guidance: what is sent, and how the answer is read (G1, G3).

One job: turn one screen's candidate controls into a redacted TEXT-ONLY payload, and turn
whatever came back into a validated order. No network, no clock, no model import (qa/contracts/
crawl-guidance.md G9: `explore_guidance.py` owns the call). A control is numbered `0..n-1`; the
answer is indices only, cleaned in ONE place (`clean_indices`) and completed in rule order, so
the result is always a permutation of the code's own list: a model can order a control, never add,
drop or invent one.

Sent per screen: url template (query and fragment stripped, never the example URL), title, depth,
known screen templates (capped). Sent per control: index, role, name (trimmed, scrubbed), tag,
type, is_form_submit, in_row, has_href and the href PATH only (http(s) only, templated; any
other scheme is just `<mailto>`, `<tel>` ...). A form control (input, textarea, select) sends its
label text (aria-label, <label>, placeholder) or `<field:type>`, never its value or option text.
A control inside a list row has its name replaced by a fixed placeholder (rows are where student
names live) and no href.
Never sent: images, input values, cookies, headers, tokens, query strings, the example URL.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypeVar
from urllib.parse import urlsplit

from autotester.core.ids import content_hash
from autotester.core.urls import url_template
from autotester.schema.screen_graph import ElementRef, ScreenNode

T = TypeVar("T")
MAX_CANDIDATES = 80
"""G1: controls ranked per call; the rest follow in rule order after the ranked head."""
NAME_CHARS = 60
TITLE_CHARS = 80
KNOWN_CAP = 30
ROW_PLACEHOLDER = "<row item>"
FIELD_TAGS = ("input", "textarea", "select")
CAPTION_TYPES = ("submit", "button", "reset", "image")
"""A button-like input's `value` is its caption, not user data, so its name is still sent."""


def href_path(href: str | None) -> str:
    """What a link may say: an http(s) path templated by `core/urls.url_template` with no host,
    `;params`, query or fragment; any other scheme (mailto, tel, javascript, data) as `<scheme>`
    only, since its payload is an address, a number or code. "" when there is no path."""
    if not href:
        return ""
    parts = urlsplit(href.strip())
    if parts.scheme and parts.scheme.lower() not in ("http", "https"):
        return f"<{parts.scheme.lower()}>"
    path = "/".join(seg.split(";")[0] for seg in parts.path.split("/"))
    return url_template(path, keep_host=False) if path.strip() else ""


def is_field(el: ElementRef) -> bool:
    """A data-bearing form control: its name may be its value or option text (B1)."""
    return el.field_label is not None or (
        el.tag in FIELD_TAGS and el.type not in CAPTION_TYPES)


def _template(url_template: str) -> str:
    return href_path(url_template) or "/"


def candidate_hash(cands: list[ElementRef]) -> str:
    """Content hash of the numbered candidate set (role, folded name, selector), order included,
    so a changed or reordered control set misses the stored ranking (G7)."""
    return content_hash([[c.role, " ".join(c.name.casefold().split()), c.selector] for c in cands])


def _control(i: int, el: ElementRef, scrub: Callable[[str | None], str | None]) -> dict[str, Any]:
    shown = (el.field_label or f"<field:{el.type or el.tag}>") if is_field(el) else el.name
    name = ROW_PLACEHOLDER if el.in_row else (scrub(shown.strip()) or "")  # scrub, THEN cut
    path = "" if el.in_row else scrub(href_path(el.href)) or ""
    return {"i": i, "role": el.role, "name": name[:NAME_CHARS], "tag": el.tag, "type": el.type,
            "is_form_submit": el.is_form_submit, "in_row": el.in_row,
            "has_href": bool(el.href), "href_path": path}


def build_payload(node: ScreenNode, cands: list[ElementRef], known: list[str],
                  scrub: Callable[[str | None], str | None]) -> dict[str, Any]:
    """The redacted payload for `cands[:MAX_CANDIDATES]` (the caller passes the head)."""
    return {
        "screen": {"url_template": scrub(_template(node.url_template)),
                   "title": (scrub(node.title.strip()) or "")[:TITLE_CHARS], "depth": node.depth},
        "known_screens": [scrub(_template(k)) or "" for k in known[:KNOWN_CAP]],
        "controls": [_control(i, el, scrub) for i, el in enumerate(cands)],
    }


def render_prompt(skill_body: str, body: dict[str, Any]) -> str:
    """The finished prompt text: the versioned skill body, then the payload as JSON."""
    return f"{skill_body.rstrip()}\n\n{json.dumps(body, ensure_ascii=True, sort_keys=True)}\n"


def clean_indices(ints: list[int], n: int) -> list[int] | None:
    """THE range and duplicate filter (G1): in-range, first occurrence only, order kept.
    None when nothing usable is left (an answer of garbage is a failure, not an empty order)."""
    kept = [i for i in dict.fromkeys(ints) if 0 <= i < n]
    return kept or None


def parse_ranking(raw: Any, n: int) -> list[int] | None:
    """The usable ranked indices of a model answer, or None for any failure: wrong shape, a
    non-integer entry (strings and bools are not indices), empty, or nothing in range."""
    ranked = raw.get("ranked") if isinstance(raw, dict) else getattr(raw, "ranked", raw)
    if not isinstance(ranked, list):
        return None
    if any(isinstance(i, bool) or not isinstance(i, int) for i in ranked):
        return None
    return clean_indices(ranked, n)


def complete_order(ranked: list[int], n: int) -> list[int]:
    """`ranked` (already cleaned) then every index it did not mention, in rule order."""
    mentioned = set(ranked)
    return [*ranked, *(i for i in range(n) if i not in mentioned)]


def reorder(items: list[T], order: list[int]) -> list[T]:
    return [items[i] for i in order]
