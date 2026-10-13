"""D-014/Track B1: the guard for an `Action` with no handler yet, and the four
new actions (BACK/HOVER/PRESS_KEY/SCROLL) actually running through
`run_case`. Split from `test_execute.py` at doctor's 300-line cap.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind, Outcome
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef
from autotester.stages.execute import run_case

LOGIN = "https://app.pathlynks.test/login"


class FakeLocator:
    def __init__(self, page: FakePage, selector: str) -> None:
        self.page, self.selector = page, selector

    def hover(self) -> None:
        self.page.hovers.append(self.selector)

    def press(self, key: str) -> None:
        self.page.presses.append((self.selector, key))


class FakeKeyboard:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    def press(self, key: str) -> None:
        self.page.presses.append((None, key))


class FakeMouse:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    def wheel(self, dx: int, dy: int) -> None:
        self.page.wheels.append((dx, dy))


class FakePage:
    def __init__(self, url: str) -> None:
        self.url = url
        self.filled: dict[str, str] = {}
        self.attrs: dict[str, list[str]] = {}
        self.clicks: list[str] = []
        self.hovers: list[str] = []
        self.presses: list[tuple[str | None, str]] = []
        self.wheels: list[tuple[int, int]] = []
        self.back_calls = 0
        self.styles: list[str] = []
        self.shots: list[str] = []
        self.settled: list[tuple[str, int]] = []
        self.body_text = ""
        self.keyboard = FakeKeyboard(self)
        self.mouse = FakeMouse(self)

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, selector)

    def add_style_tag(self, content: str) -> None:
        self.styles.append(content)

    def screenshot(self, path: str, full_page: bool = False) -> None:
        self.shots.append(path)
        Path(path).write_bytes(b"png")

    def goto(self, url: str, wait_until: str = "") -> None:
        self.url = url

    def go_back(self, wait_until: str = "") -> None:
        self.back_calls += 1

    def wait_for_timeout(self, timeout: int) -> None:
        pass

    def wait_for_load_state(self, state: str = "load", timeout: int = 0) -> None:
        self.settled.append((state, timeout))


def make_project() -> Project:
    return Project(
        slug="pathlynks", name="Pathlynks", base_url=LOGIN,
        allowed_domains=["pathlynks.test"],
        secrets=[SecretRef(key="PATHLYNKS_PASSWORD", domains=["app.pathlynks.test"])],
    )


def make_store(tmp_path: Path) -> SecretStore:
    env = tmp_path / ".env"
    env.write_text("PATHLYNKS_PASSWORD=hunter2\n", encoding="utf-8")
    return SecretStore.load(make_project(), env)


def session_with_fake_page(tmp_path: Path) -> BrowserSession:
    paths = ProjectPaths("pathlynks", tmp_path)
    s = BrowserSession(make_project(), make_store(tmp_path), tmp_path / "run", paths)
    s._page = FakePage(LOGIN)
    s.state.run_dir.mkdir(parents=True, exist_ok=True)
    return s


def make_case(steps: list[Step]) -> Case:
    return Case(project="pathlynks", flow_id="flow_login", kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY, title="log in", steps=steps)


# -- D-014: an Action with no handler reports, never crashes -----------------

def test_an_action_with_no_handler_errors_instead_of_raising_keyerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`_ACTIONS.get(...)` + `StepNotExecutable` (D-014) guards against a future
    `Action` member landing on the enum before its `BrowserSession` handler
    does — exercised here by removing a real entry, since every current
    member (including BACK/HOVER/PRESS_KEY/SCROLL, wired at Track B1) now
    has one."""
    from autotester.stages import execute as execute_module

    patched = dict(execute_module._ACTIONS)
    del patched[Action.SCROLL]
    monkeypatch.setattr(execute_module, "_ACTIONS", patched)

    steps = [Step(order=1, action=Action.SCROLL, target="")]
    session = session_with_fake_page(tmp_path)

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.ERRORED
    assert "scroll" in (result.error or "")
    assert "no browser handler yet" in (result.error or "")


def test_back_hover_press_key_scroll_run_completed_and_record_evidence(
    tmp_path: Path,
) -> None:
    """The real Track B1 handlers: each new Action composes a `BrowserSession`
    method and records evidence, same discipline as every existing action."""
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.SCROLL, target="", value="400"),
        Step(order=3, action=Action.HOVER, target="a.nav-link"),
        Step(order=4, action=Action.PRESS_KEY, target="input[name=email]", value="Tab"),
        Step(order=5, action=Action.BACK, target=""),
    ]
    session = session_with_fake_page(tmp_path)

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.COMPLETED
    dom_labels = [e.label or e.path for e in result.evidence if e.kind == EvidenceKind.DOM]
    assert any("scrolled" in label for label in dom_labels)
    assert any("hovered" in label for label in dom_labels)
    assert any("pressed Tab" in label for label in dom_labels)
