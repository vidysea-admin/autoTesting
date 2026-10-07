"""Semantic locators: the target grammar and the session's one place that resolves it.

`schema/flowspec.py` promises a step `target` is a semantic locator, "role/name/label, not a
brittle CSS path". This module keeps that promise. A target is one of

    role=button[name="Save"]     -> page.get_by_role("button", name="Save", exact=True)
    label="Email address"        -> page.get_by_label("Email address", exact=True)
    testid[data-qa]="save"       -> the element whose declared test-id attribute equals "save"
    anything else                -> a Playwright/CSS selector, passed through unchanged

Matching is exact on purpose: a locator that "heals" onto a different element is worse than one
that fails (qa/contracts/script-replay.md SR3). A semantic locator must match exactly one
element, or the step raises `LocatorNotFound` -- the run reports it, it never guesses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_QUOTED = r'"((?:[^"\\]|\\.)*)"'
_ROLE = re.compile(rf"^role=([a-z]+)(?:\[name={_QUOTED}\])?$")
_LABEL = re.compile(rf"^label={_QUOTED}$")
_TESTID = re.compile(rf"^testid\[([A-Za-z_][\w:.-]*)\]={_QUOTED}$")
DEFAULT_LOCATE_TIMEOUT_MS = 5000


class LocatorNotFound(RuntimeError):
    """The step's target matched no element (or, in a script, more than one)."""


@dataclass(frozen=True)
class Semantic:
    """A parsed semantic target. `kind` is role, label or testid."""

    kind: str
    name: str | None = None
    role: str | None = None
    attr: str | None = None


def _quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _unquote(text: str) -> str:
    return re.sub(r"\\(.)", r"\1", text)


def format_role(role: str, name: str | None) -> str:
    return f"role={role}" + (f"[name={_quote(name)}]" if name else "")


def format_label(text: str) -> str:
    return f"label={_quote(text)}"


def format_testid(attr: str, value: str) -> str:
    return f"testid[{attr}]={_quote(value)}"


def parse_target(target: str) -> Semantic | None:
    """The semantic form of `target`, or None when it is an ordinary selector."""
    if match := _ROLE.match(target):
        name = match.group(2)
        return Semantic("role", role=match.group(1), name=None if name is None else _unquote(name))
    if match := _LABEL.match(target):
        return Semantic("label", name=_unquote(match.group(1)))
    if match := _TESTID.match(target):
        return Semantic("testid", attr=match.group(1), name=_unquote(match.group(2)))
    return None


def resolve(page: Any, target: str) -> Any:
    """The Playwright locator for `target` (semantic or selector). Never waits, never raises."""
    spec = parse_target(target)
    if spec is None:
        return page.locator(target)
    if spec.kind == "role":
        return page.get_by_role(spec.role, name=spec.name, exact=True)
    if spec.kind == "label":
        return page.get_by_label(spec.name, exact=True)
    escaped = (spec.name or "").replace("\\", "\\\\").replace('"', '\\"')
    return page.locator(f'[{spec.attr}="{escaped}"]')


class LocatorMixin:
    """`locate()` and the replay/record switches -- mixed into `BrowserSession`."""

    recorder: Any = None
    """Set by `stages/script_replay.py` while a live run is being recorded; `run_case` calls
    `recorder.capture(session, step)` before each step. None means nothing is recording."""
    replaying: bool = False
    """True while `stages/script_replay.py` replays a stored script (errors then name the step)."""
    locate_timeout_ms: int = DEFAULT_LOCATE_TIMEOUT_MS

    def locate(self, target: str) -> Any:
        """The locator for a step target. A plain selector is returned untouched (the
        pre-T-176 behaviour); a semantic one must resolve to exactly one element."""
        loc = resolve(self.page, target)  # type: ignore[attr-defined]
        if parse_target(target) is None:
            return loc
        try:
            loc.first.wait_for(state="attached", timeout=self.locate_timeout_ms)
        except Exception as exc:
            raise LocatorNotFound(f"no element matched {target}") from exc
        if (count := loc.count()) > 1:
            raise LocatorNotFound(f"{target} matched {count} elements, expected exactly one")
        return loc
