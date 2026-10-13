"""Click readiness with fakes: probe first, recover honestly, never force."""

from __future__ import annotations

from typing import Any

from autotester.browser.click_recovery import ready_to_click


class _Loc:
    def __init__(self, blocked_until: int, expander: str | None = "button.menu-item Menu") -> None:
        self.probes, self.blocked_until, self.expander = 0, blocked_until, expander
        self.calls: list[str] = []

    def click(self, **kw: Any) -> None:
        assert kw.get("trial") is True, "recovery must never perform a real/forced click"
        self.probes += 1
        if self.probes <= self.blocked_until:
            raise TimeoutError("intercepts pointer events")

    def scroll_into_view_if_needed(self, **_: Any) -> None:
        self.calls.append("scroll")

    def evaluate(self, *_: Any, **__: Any) -> str | None:
        return self.expander

    def hover(self, **_: Any) -> None:
        self.calls.append("hover")


class _Marked:
    def __init__(self, log: list[str]) -> None:
        self.log, self.first = log, self

    def hover(self, **_: Any) -> None:
        self.log.append("hover-parent")

    def click(self, **_: Any) -> None:
        self.log.append("click-parent")

    def evaluate(self, *_: Any, **__: Any) -> None:
        self.log.append("unmark")


class _Page:
    def __init__(self) -> None:
        self.log: list[str] = []

    def locator(self, _: str) -> _Marked:
        return _Marked(self.log)


def test_actionable_target_needs_no_recovery() -> None:
    assert ready_to_click(_Page(), _Loc(0)) == []


def test_collapsed_parent_is_expanded_once_and_recorded() -> None:
    page, loc = _Page(), _Loc(blocked_until=3)
    done = ready_to_click(page, loc)
    assert done == ["scrolled target into view", "expanded parent menu via button.menu-item Menu"]
    assert page.log == ["hover-parent", "click-parent", "unmark"]


def test_still_blocked_target_is_left_for_the_real_click_to_fail_honestly() -> None:
    loc = _Loc(blocked_until=99, expander=None)
    assert ready_to_click(_Page(), loc) == ["scrolled target into view"]
