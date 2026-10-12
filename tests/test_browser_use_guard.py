"""T-177 slice 2: the per-action SDK guard and the AF6 dependency-isolation tests.

The controller is the REAL installed browser-use `Controller` subclass; only its dispatch
(`Controller.act`) and the page are faked, so no browser, network or LLM is involved.
"""

from __future__ import annotations

import asyncio
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from autotester.providers.mock import MockProvider
from autotester.schema.agent_fallback import FallbackAction
from autotester.schema.project import Project
from autotester.stages.agent_actuator import ActionGuard, ActionRefused, BoundExhausted
from autotester.stages.browser_use_backend import BrowserUseBackend, _guarded_controller

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "autotester"
GOOD, EVIL = "https://pathlynks.test/home", "https://evil.example/x"


class Page:
    def __init__(self, url: str) -> None:
        self.url, self.closed = url, False

    def is_closed(self) -> bool:
        return self.closed


def node(**attrs: str) -> Any:
    return SimpleNamespace(attributes=attrs, tag_name="a" if "href" in attrs else "button",
                           get_all_text_till_next_clickable_element=lambda: attrs.get("t", ""))


def session(url: str = GOOD, nodes: dict | None = None) -> Any:
    return SimpleNamespace(agent_current_page=Page(url), _cached_browser_state_summary=(
        SimpleNamespace(selector_map=nodes or {})))


def model(**one: Any) -> Any:
    return SimpleNamespace(model_dump=lambda exclude_unset=True: one)


class FakeGuard:
    """Stands in for ActionGuard: records vets, refuses by url / landing host."""

    def __init__(self, fail_write: bool = False) -> None:
        self.vetted: list[FallbackAction] = []
        self.fail_write = fail_write

    def __call__(self, action: FallbackAction) -> None:
        if self.fail_write and action.kind.value in ("fill", "select", "upload"):
            raise ActionRefused("write refused under read_only")
        if action.url and "evil" in action.url:
            raise ActionRefused("destination outside allowed domains")
        self.vetted.append(action)

    def landed(self, url: str) -> None:
        if "evil" in url:
            raise ActionRefused(f"landed outside allowed domains: {url}")


def controller(monkeypatch: pytest.MonkeyPatch, guard: Any, lands: str | None = None,
               fails: bool = False):
    import browser_use

    dispatched: list[Any] = []

    async def fake_act(self: Any, action: Any, browser_session: Any, **kw: Any) -> str:
        dispatched.append(action)
        if lands:
            browser_session.agent_current_page.url = lands
        if fails:
            raise RuntimeError("click failed")
        return "ok"

    monkeypatch.setattr(browser_use.Controller, "act", fake_act)
    taken: list = []
    stopped: list = []
    halted: list = []
    ctl = _guarded_controller(guard, taken, stopped, lambda: halted.append(1))
    return ctl, dispatched, taken, stopped, halted


def act(ctl: Any, ses: Any, action: Any) -> Any:
    return asyncio.run(ctl.act(action, ses))


def test_in_domain_actions_dispatch_and_are_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    ses = session(nodes={1: node(t="Next", href="/a")})
    ctl, dispatched, taken, stopped, _ = controller(monkeypatch, FakeGuard())
    assert act(ctl, ses, model(click_element_by_index={"index": 1})) == "ok"
    act(ctl, ses, model(scroll={"down": True}))
    assert len(dispatched) == 2 and len(taken) == 2 and stopped == []
    assert taken[0].url == "https://pathlynks.test/a"


def test_off_domain_destination_is_refused_before_dispatch(
        monkeypatch: pytest.MonkeyPatch) -> None:
    ctl, dispatched, taken, stopped, halted = controller(monkeypatch, FakeGuard())
    with pytest.raises(ActionRefused, match="destination"):
        act(ctl, session(), model(go_to_url={"url": EVIL}))
    assert dispatched == [] and taken == [] and len(stopped) == 1 and halted == [1]


def test_write_action_is_refused_before_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    ses = session(nodes={2: node(t="Email", type="text")})
    ctl, dispatched, *_ = controller(monkeypatch, FakeGuard(fail_write=True))
    with pytest.raises(ActionRefused, match="write"):
        act(ctl, ses, model(input_text={"index": 2, "text": "x"}))
    assert dispatched == []


def test_off_domain_landing_prevents_the_next_action(monkeypatch: pytest.MonkeyPatch) -> None:
    ses = session(nodes={1: node(t="Go")})
    ctl, dispatched, _, stopped, halted = controller(monkeypatch, FakeGuard(), lands=EVIL)
    with pytest.raises(ActionRefused, match="landed outside"):
        act(ctl, ses, model(click_element_by_index={"index": 1}))
    assert len(dispatched) == 1 and halted == [1]
    with pytest.raises(ActionRefused, match="run already stopped"):
        act(ctl, ses, model(scroll={"down": True}))  # action 2 of the same SDK step
    assert len(dispatched) == 1 and len(stopped) == 2


def test_a_failed_action_still_gets_the_landing_check(monkeypatch: pytest.MonkeyPatch) -> None:
    ses = session(nodes={1: node(t="Go")})
    ctl, *_ = controller(monkeypatch, FakeGuard(), lands=EVIL, fails=True)
    with pytest.raises(ActionRefused, match="landed outside"):
        act(ctl, ses, model(click_element_by_index={"index": 1}))


def test_unmapped_action_and_unknown_element_fail_closed(
        monkeypatch: pytest.MonkeyPatch) -> None:
    ctl, dispatched, *_ = controller(monkeypatch, FakeGuard())
    for bad in (model(write_file={"file_name": "a"}), model(click_element_by_index={"index": 9})):
        with pytest.raises(ActionRefused):
            act(ctl, session(), bad)
    assert dispatched == []


def test_absent_or_closed_page_fails_closed_without_recovery(
        monkeypatch: pytest.MonkeyPatch) -> None:
    ses = session()
    ses.agent_current_page.closed = True
    ses.get_current_page = ses.start = ses.new_page = lambda *a, **k: pytest.fail("recovery")
    ctl, dispatched, *_ = controller(monkeypatch, FakeGuard())
    with pytest.raises(ActionRefused, match="no active page"):
        act(ctl, ses, model(scroll={"down": True}))
    ses.agent_current_page = None
    with pytest.raises(ActionRefused, match="no active page"):
        act(ctl, ses, model(scroll={"down": True}))
    assert dispatched == []


def test_done_is_not_a_page_operation(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = FakeGuard()
    ctl, dispatched, taken, *_ = controller(monkeypatch, guard)
    act(ctl, session(), model(done={"text": "fin", "success": True}))
    assert dispatched and taken == [] and guard.vetted == []


def real_guard(max_steps: int = 2) -> ActionGuard:
    project = Project(slug="d", name="D", base_url="https://pathlynks.test/",
                      allowed_domains=["pathlynks.test"])  # write_policy defaults to READ_ONLY
    return ActionGuard(SimpleNamespace(project=project), max_steps, 5.0, lambda: 0.0)


def test_the_real_guard_spends_one_unit_per_action(monkeypatch: pytest.MonkeyPatch) -> None:
    real = real_guard()
    ctl, dispatched, *_ = controller(monkeypatch, real)
    act(ctl, session(), model(wait={"seconds": 1}))
    act(ctl, session(), model(scroll={"down": True}))
    with pytest.raises(BoundExhausted, match="max_steps=2"):
        act(ctl, session(), model(scroll={"down": True}))
    assert len(dispatched) == 2 and len(real.vetted) == 2


def test_the_real_guard_enforces_read_only_and_keys_before_dispatch(
        monkeypatch: pytest.MonkeyPatch) -> None:
    ses = session(nodes={3: node(t="Email", type="text")})
    for bad in (model(input_text={"index": 3, "text": "x"}), model(send_keys={"keys": "Enter"}),
                model(go_to_url={"url": EVIL})):
        ctl, dispatched, *_ = controller(monkeypatch, real_guard(5))
        with pytest.raises(ActionRefused):
            act(ctl, ses, bad)
        assert dispatched == []
    ctl, dispatched, *_ = controller(monkeypatch, real_guard(5))
    act(ctl, ses, model(send_keys={"keys": "Tab"}))
    assert len(dispatched) == 1


# -- _drive: sticky refusal and SDK max_steps exhaustion ---------------------------------------

def drive(monkeypatch: pytest.MonkeyPatch, history: Any, refuse: bool = False) -> Any:
    import browser_use

    class FakeAgent:
        id = "a1"

        def __init__(self, **kw: Any) -> None:
            self.kw = kw

        def stop(self) -> None:
            pass

        async def run(self, max_steps: int) -> Any:
            if refuse:  # the SDK swallows the step error; only the sticky record survives
                with pytest.raises(ActionRefused):
                    await self.kw["controller"].act(model(go_to_url={"url": EVIL}), session())
            return history

    monkeypatch.setattr(browser_use, "BrowserSession", lambda **kw: object())
    monkeypatch.setattr(browser_use, "Agent", FakeAgent)
    backend = BrowserUseBackend(MockProvider(), "http://127.0.0.1:9333", str)
    backend_guard = FakeGuard()
    return asyncio.run(backend._drive("t", backend_guard, 3, 5.0))


def hist(steps: int, done: bool) -> Any:
    return SimpleNamespace(number_of_steps=lambda: steps, is_done=lambda: done,
                           is_successful=lambda: done, final_result=lambda: "r" if done else None)


def test_sticky_refusal_is_raised_even_if_the_sdk_swallows_it(
        monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ActionRefused, match="destination"):
        drive(monkeypatch, hist(1, False), refuse=True)


def test_sdk_max_steps_exhaustion_is_a_named_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(BoundExhausted, match="max_steps=3"):
        drive(monkeypatch, hist(3, False))
    assert drive(monkeypatch, hist(2, True))["resolved"] is True


# -- AF6: the vendor SDK is imported only inside the backend -----------------------------------

IMPORT = re.compile(r"^\s*(?:import|from)\s+browser_use\b", re.M)


def test_af6_browser_use_is_imported_only_in_the_backend() -> None:
    offenders = [str(p.relative_to(ROOT)) for p in SRC.rglob("*.py")
                 if p.name != "browser_use_backend.py"
                 and IMPORT.search(p.read_text(encoding="utf-8"))]
    assert offenders == []
    backend = (SRC / "stages" / "browser_use_backend.py").read_text(encoding="utf-8")
    top = [ln for ln in backend.splitlines() if re.match(r"(?:import|from)\s+browser_use\b", ln)]
    assert top == []  # every browser_use import in the backend is lazy (inside a function)


def test_af6_importing_the_product_does_not_load_the_sdk() -> None:
    code = ("import sys; import autotester.stages.agent_actuator, "
            "autotester.stages.run_case_pipeline, autotester.stages.browser_use_backend; "
            "bad=[m for m in sys.modules if m.split('.')[0]=='browser_use']; "
            "sys.exit(1 if bad else 0)")
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          timeout=120, cwd=ROOT)
    assert done.returncode == 0, done.stderr[-1500:]
