"""Derive the most meaningful locator for an element that is on screen right now.

Used while a case runs live and its script is being recorded (`stages/script_replay.py`). The
ladder, first rung that is unique AND points at the very same element wins:

    1. a declared test-id attribute, in the project's declared order (nothing off the list)
    2. role + accessible name  (Playwright's own aria snapshot -- no re-implemented a11y rules)
    3. label
    4. the original selector, flagged `brittle` so the report names it

Every rung is verified by resolving the candidate and comparing element identity, so a derived
locator can never silently point somewhere else. No model is involved.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from autotester.browser.locators import (
    format_label,
    format_role,
    format_testid,
    parse_target,
    resolve,
)

_ARIA_HEAD = re.compile(r'^- ([a-z]+)(?: "((?:[^"\\]|\\.)*)")?')
_LABEL_JS = "el => ((el.labels && el.labels[0] && el.labels[0].innerText) || '').trim()"


@dataclass(frozen=True)
class Derived:
    """The locator a script will use for one step, and how it was chosen."""

    locator: str
    strategy: str  # testid | role | label | css
    brittle: bool


def _is_same_unique(page: Any, candidate: str, element: Any) -> bool:
    found = resolve(page, candidate)
    if found.count() != 1:
        return False
    return bool(found.evaluate("(el, other) => el === other", element.element_handle()))


def _role_and_name(element: Any) -> tuple[str, str] | None:
    head = _ARIA_HEAD.match(element.aria_snapshot().strip())
    if head is None or head.group(2) is None or head.group(1) in {"generic", "text"}:
        return None
    return head.group(1), re.sub(r"\\(.)", r"\1", head.group(2))


def _candidates(page: Any, element: Any, attrs: Sequence[str]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for attr in attrs:
        if value := element.get_attribute(attr):
            found.append(("testid", format_testid(attr, value)))
    if pair := _role_and_name(element):
        found.append(("role", format_role(*pair)))
    if label := element.evaluate(_LABEL_JS):
        found.append(("label", format_label(label)))
    return found


def derive(page: Any, target: str, test_id_attributes: Sequence[str]) -> Derived:
    """The best verified locator for the element `target` resolves to; the original target,
    flagged brittle, when it resolves to nothing unique or no semantic locator is unique."""
    fallback = Derived(target, "css", True)
    try:
        element = resolve(page, target)
        if element.count() != 1:
            return fallback
        for strategy, candidate in _candidates(page, element, test_id_attributes):
            if _is_same_unique(page, candidate, element):
                return Derived(candidate, strategy, False)
    except Exception:  # recording must never fail a run that executed fine
        return fallback
    if (spec := parse_target(target)) is not None:
        return Derived(target, spec.kind, False)
    return fallback
