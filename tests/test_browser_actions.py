"""Track B1: the four new `BrowserSession` actions (go_back/hover/press_key/
scroll) and `current_url`. New file — `test_browser.py` is already near the
300-line cap. Same FakePage pattern as `test_browser.py`/`test_execute.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_parallel_run import _approval

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession, launch_options
from autotester.core.paths import ProjectPaths
from autotester.schema.enums import EvidenceKind
from autotester.schema.project import Project, SecretRef
from autotester.stages.run_budget import RunBudget, RunBudgetExceeded

LOGIN = "https://app.pathlynks.test/login"


class FakeLocator:
    def __init__(self, page: FakePage, selector: str) -> None:
        self.page, self.selector = page, selector

    def hover(self) -> None:
        self.page.hovers.append(self.selector)

    def press(self, key: str) -> None:
        self.page.presses.append((self.selector, key))

    def get_attribute(self, name, **kwargs):
        if self.page.mode == "classify_fail":
            raise RuntimeError("hunter2 classify failure")
        if name == "type":
            return "password" if self.page.mode == "password" else "text"
        return "1" if self.page.mode == "masked" else None

    def evaluate(self, script, **kwargs):
        if "setAttribute" in script:
            self.page.mode = "masked"
        return self.page.mode != "noninput"

    def input_value(self, **kwargs):
        if self.page.mode in ("password", "masked", "previous", "placeholder"):
            raise AssertionError("secret input_value must not be called")
        self.page.value_reads += 1
        if self.page.mode == "read_fail":
            raise RuntimeError("hunter2 read failure")
        return self.page.value

    def fill(self, value, **kwargs):
        if self.page.mode == "fill_fail":
            raise RuntimeError("fill failed")
        self.page.fills.append(value)
        self.page.value = value
        if self.page.mode == "new_mask":
            self.page.mode = "masked"
        if self.page.on_fill:
            self.page.on_fill()


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
        self.hovers: list[str] = []
        self.presses: list[tuple[str | None, str]] = []
        self.wheels: list[tuple[int, int]] = []
        self.back_calls = 0
        self.keyboard = FakeKeyboard(self)
        self.mouse = FakeMouse(self)
        self.mode, self.value = "plain", "old"
        self.value_reads, self.fills, self.on_fill = 0, [], None

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, selector)

    def go_back(self, wait_until: str = "") -> None:
        self.back_calls += 1
        self.url = "https://app.pathlynks.test/"


def make_project() -> Project:
    return Project(
        slug="pathlynks", name="Pathlynks", base_url=LOGIN,
        allowed_domains=["pathlynks.test"],
        secrets=[SecretRef(key="PATHLYNKS_PASSWORD", domains=["pathlynks.test"])],
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


def test_launch_options_still_importable_from_session_after_the_move(tmp_path: Path) -> None:
    """`launch_options` moved to `browser/launch.py` (B1) — must remain
    importable from `session` (existing callers/tests) with identical output."""
    from autotester.browser.launch import launch_options as moved

    paths = ProjectPaths("pathlynks", tmp_path)
    assert launch_options(make_project(), paths) == moved(make_project(), paths)


def test_current_url_reads_the_page_without_a_direct_page_touch(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    assert s.current_url() == LOGIN


def test_go_back_calls_the_page_and_records_url_evidence(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    ev = s.go_back(step_order=3)
    assert s.page.back_calls == 1
    assert ev.kind is EvidenceKind.DOM or ev.kind is EvidenceKind.URL
    assert ev.label == "back"
    assert ev.step_order == 3


def test_hover_composes_the_locator(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    ev = s.hover("a.nav-link", step_order=1)
    assert s.page.hovers == ["a.nav-link"]
    assert "hovered" in (ev.label or ev.path)


def test_press_key_with_a_locator_targets_that_element(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    s.press_key("Enter", "input[name=email]", step_order=2)
    assert s.page.presses == [("input[name=email]", "Enter")]


def test_press_key_without_a_locator_uses_the_keyboard(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    s.press_key("Escape")
    assert s.page.presses == [(None, "Escape")]


def test_scroll_uses_the_mouse_wheel_with_a_default_delta(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    s.scroll()
    assert s.page.wheels == [(0, 800)]


def test_scroll_accepts_a_custom_delta(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    s.scroll(delta_y=200)
    assert s.page.wheels == [(0, 200)]


@pytest.mark.parametrize("mode", ["plain", "placeholder", "password", "masked", "previous",
                                  "noninput", "classify_fail", "read_fail", "redact", "new_mask",
                                  "escaped"])
def test_fill_receipt_observes_values_but_never_reads_secrets(tmp_path, mode):
    session = session_with_fake_page(tmp_path)
    page = session.page
    page.mode = mode
    if mode == "previous":
        session.state.secret_locators.append("#field")
    if mode == "redact":
        page.value = "hunter2"
    if mode == "escaped":
        page.value = "synthetic'\\credential"
        session.secrets = SecretStore(make_project(), {"PATHLYNKS_PASSWORD": page.value})
    value = "{{SECRET:PATHLYNKS_PASSWORD}}" if mode == "placeholder" else "new"
    session.fill("#field", value, step_order=7)
    item = session.state.evidence[-1]
    assert item.kind is EvidenceKind.DOM and item.step_order == 7
    assert item.path.startswith("filled #field") and "hunter2" not in item.path
    assert "failure" not in item.path
    assert "synthetic" not in item.path and "credential" not in item.path
    if mode in ("placeholder", "password", "masked", "previous"):
        assert page.value_reads == 0 and "before=[secret] after=[secret]" in item.path
    elif mode in ("noninput", "classify_fail", "read_fail"):
        assert "before=unavailable after=unavailable" in item.path
        assert page.value_reads == (2 if mode == "read_fail" else 0)
    elif mode == "new_mask":
        assert page.value_reads == 1 and "before='old' after=[secret]" in item.path
    else:
        assert page.value_reads == 2 and "after='new'" in item.path
        assert "before='old'" in item.path if mode == "plain" else "REDACTED" in item.path


@pytest.mark.parametrize("phase", ["beforeprobe", "afterprobe", "beforetime", "aftertime"])
def test_fill_receipt_brakes_preserve_only_successful_action(tmp_path, monkeypatch, phase):
    from autotester.stages import run_budget

    clock = [0.0]
    monkeypatch.setattr(run_budget.time, "monotonic", lambda: clock[0])
    session = session_with_fake_page(tmp_path)
    page = session.page
    probes = 0 if phase == "beforeprobe" else 1 if phase == "afterprobe" else 10
    session.budget = RunBudget(_approval(max_probes=probes, wall_clock_s=1))
    if phase == "beforetime":
        clock[0] = 1.0
    if phase == "aftertime":
        page.on_fill = lambda: clock.__setitem__(0, 1.0)
    reason = "max_probes" if "probe" in phase else "wall_clock_s"
    with pytest.raises(RunBudgetExceeded, match=reason):
        session.fill("#field", "new", step_order=7)
    if phase.startswith("after"):
        assert page.fills == ["new"] and session.state.evidence[-1].step_order == 7
        assert "before='old' after=unavailable" in session.state.evidence[-1].path
    else:
        assert page.fills == [] and session.state.evidence == []


def test_failed_fill_never_records_a_successful_receipt(tmp_path):
    session = session_with_fake_page(tmp_path)
    session.page.mode = "fill_fail"
    with pytest.raises(RuntimeError, match="fill failed"):
        session.fill("#field", "new")
    assert session.state.evidence == []
