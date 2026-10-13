"""EXECUTE stage. Contract: qa/contracts/execute.md E1-E5.

A fake page exercises run_case without a real browser -- same pattern as
test_browser.py, extended with the actions execute.py composes.
"""

from __future__ import annotations

from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind, Outcome
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef
from autotester.schema.run import RawResult, Run
from autotester.stages.execute import run_case
from autotester.store.project_store import ProjectStore

LOGIN = "https://app.pathlynks.test/login"


class FakeLocator:
    def __init__(self, page: FakePage, selector: str) -> None:
        self.page, self.selector = page, selector

    def evaluate(self, script: str) -> None:
        self.page.attrs.setdefault(self.selector, []).append(script)

    def fill(self, value: str) -> None:
        self.page.filled[self.selector] = value

    def click(self) -> None:
        if self.selector == "button.broken":
            raise RuntimeError("element not attached to the DOM")
        if self.selector == "button.leaks-a-secret":
            # Simulates a third-party exception (e.g. Playwright's own error
            # text sometimes echoes nearby DOM/page state) embedding a value
            # that was typed into the page moments earlier.
            raise RuntimeError("timeout waiting for element near text 'hunter2'")
        self.page.clicks.append(self.selector)

    def select_option(self, value: str | None) -> None:
        self.page.selected[self.selector] = value

    def set_input_files(self, path: str) -> None:
        self.page.uploaded[self.selector] = path

    def wait_for(self, timeout: int = 0) -> None:
        self.page.waited.append((self.selector, timeout))

    def inner_text(self) -> str:
        return self.page.body_text
    def count(self) -> int:
        return 0 if self.selector in self.page.missing_selectors else 1


class FakePage:
    def __init__(self, url: str) -> None:
        self.url = url
        self.filled: dict[str, str] = {}
        self.attrs: dict[str, list[str]] = {}
        self.clicks: list[str] = []
        self.selected: dict[str, str | None] = {}
        self.uploaded: dict[str, str] = {}
        self.waited: list[tuple[str, int]] = []
        self.timeouts: list[int] = []
        self.styles: list[str] = []
        self.shots: list[str] = []
        self.settled: list[tuple[str, int]] = []
        self.body_text = ""
        self.missing_selectors: set[str] = set()  # AT-548/AT-551: locator().count()==0

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, selector)

    def add_style_tag(self, content: str) -> None:
        self.styles.append(content)

    def screenshot(self, path: str, full_page: bool = False) -> None:
        self.shots.append(path)
        Path(path).write_bytes(b"png")

    def goto(self, url: str, wait_until: str = "") -> None:
        self.url = url

    def wait_for_timeout(self, timeout: int) -> None:
        self.timeouts.append(timeout)

    def wait_for_load_state(self, state: str = "load", timeout: int = 0) -> None:
        self.settled.append((state, timeout))


def make_project(*, secret_present: bool = True) -> Project:
    return Project(
        slug="pathlynks", name="Pathlynks", base_url=LOGIN,
        allowed_domains=["pathlynks.test"],
        secrets=[SecretRef(key="PATHLYNKS_PASSWORD", domains=["app.pathlynks.test"])],
    )


def make_store(tmp_path: Path, *, secret_present: bool = True) -> SecretStore:
    env = tmp_path / ".env"
    env.write_text("PATHLYNKS_PASSWORD=hunter2\n" if secret_present else "", encoding="utf-8")
    return SecretStore.load(make_project(), env, strict=secret_present)


def session_with_fake_page(tmp_path: Path, *, secret_present: bool = True) -> BrowserSession:
    paths = ProjectPaths("pathlynks", tmp_path)
    s = BrowserSession(make_project(), make_store(tmp_path, secret_present=secret_present),
                        tmp_path / "run", paths)
    s._page = FakePage(LOGIN)
    s.state.run_dir.mkdir(parents=True, exist_ok=True)
    return s


def make_case(steps: list[Step]) -> Case:
    return Case(project="pathlynks", flow_id="flow_login", kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY, title="log in", steps=steps)


# -- E1/E2 completes on a normal run ----------------------------------------

def test_completed_run_composes_session_methods_and_screenshots_every_step(
    tmp_path: Path,
) -> None:
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.FILL, target="input[name=email]", value="a@b.com"),
        Step(order=3, action=Action.FILL, target="input[name=password]",
             value="{{SECRET:PATHLYNKS_PASSWORD}}"),
        Step(order=4, action=Action.CLICK, target="button[type=submit]"),
        Step(order=5, action=Action.ASSERT, target="", expected={"visible_text": ["Welcome"]}),
    ]
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "Welcome back, user"  # the assertion's declared signal
    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.COMPLETED
    assert result.error is None and result.hitl_prompt is None
    assert session.page.filled["input[name=email]"] == "a@b.com"
    assert session.page.filled["input[name=password]"] == "hunter2"
    assert session.page.clicks == ["button[type=submit]"]
    shots = [e for e in result.evidence if e.kind is EvidenceKind.SCREENSHOT]
    assert len(shots) == 5  # one per step, including the judgement-free ASSERT
    assert [e.step_order for e in shots] == [1, 2, 3, 4, 5]
    # D-032: the ASSERT step recorded its deterministic result as DOM evidence
    asserts = [e for e in result.evidence
               if e.kind is EvidenceKind.DOM and e.path.startswith("assert ")]
    assert asserts, "an ASSERT step recorded no assertion evidence"
    assert all("met" in e.path and "unmet" not in e.path for e in asserts), asserts


def test_click_and_navigate_settle_before_the_screenshot_but_other_actions_do_not(
    tmp_path: Path,
) -> None:
    """AT-045/AT-053: a click or a fresh navigation both trigger an async
    transition (a form-submit redirect, or the target page itself still
    rendering) -- the evidence screenshot must reflect the settled page, not
    the instant of the action itself. Other actions (fill) don't need this --
    they don't trigger the same async-transition problem and settling after
    every action would just slow every run down. AT-053: a real live run
    against a brand-new production URL captured a blank NAVIGATE screenshot
    and false-FAILed on it because only CLICK settled before this fix."""
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.FILL, target="input[name=email]", value="a@b.com"),
        Step(order=3, action=Action.CLICK, target="button[type=submit]"),
    ]
    session = session_with_fake_page(tmp_path)
    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.COMPLETED
    assert session.page.settled == [("networkidle", 8000), ("networkidle", 8000)]


def test_click_settles_against_the_steps_own_declared_expected_text(
    tmp_path: Path,
) -> None:
    """AT-046: a step that declares what it expects (schema/flowspec.py's
    ExpectedState, already part of every Step) gets a real, specific poll
    instead of the generic networkidle guess -- e.g. a rejected-login
    case's own "Invalid credentials" text, which needs no network activity
    to appear and would never reliably show up via network-idle alone."""
    from autotester.schema.flowspec import ExpectedState

    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.CLICK, target="button[type=submit]",
             expected=ExpectedState(visible_text=["Invalid credentials"])),
    ]
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "Invalid credentials"

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.COMPLETED
    # the NAVIGATE step (no declared expected) takes the generic networkidle
    # path; only the CLICK step's own declared expected text is specific
    # enough to skip it (AT-046) -- see the settle-vs-not test above for the
    # case where neither step declares an expected text.
    assert session.page.settled == [("networkidle", 8000)]


def test_select_upload_and_wait_actions(tmp_path: Path) -> None:
    steps = [
        Step(order=1, action=Action.SELECT, target="select#role", value="counsellor"),
        Step(order=2, action=Action.UPLOAD, target="input[type=file]", value="/tmp/doc.pdf"),
        Step(order=3, action=Action.WAIT, target="div.loaded"),
        Step(order=4, action=Action.WAIT, target="", value="250"),
    ]
    session = session_with_fake_page(tmp_path)
    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.COMPLETED
    assert session.page.selected["select#role"] == "counsellor"
    assert session.page.uploaded["input[type=file]"] == "/tmp/doc.pdf"
    assert session.page.waited == [("div.loaded", 5000)]
    assert session.page.timeouts == [250]


def test_step_exception_is_errored_not_a_crash(tmp_path: Path) -> None:
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.CLICK, target="button.broken"),
        Step(order=3, action=Action.CLICK, target="button.never-reached"),
    ]
    session = session_with_fake_page(tmp_path)
    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.ERRORED
    assert "RuntimeError" in result.error and "not attached" in result.error
    assert "button.never-reached" not in session.page.clicks
    # step 1's screenshot exists; step 2 never got one (it raised first)
    shots = [e for e in result.evidence if e.kind is EvidenceKind.SCREENSHOT]
    assert len(shots) == 1


def test_missing_secret_blocks_for_a_human_instead_of_erroring(tmp_path: Path) -> None:
    steps = [
        Step(order=1, action=Action.FILL, target="input[name=password]",
             value="{{SECRET:PATHLYNKS_PASSWORD}}"),
    ]
    session = session_with_fake_page(tmp_path, secret_present=False)
    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.BLOCKED_HITL
    assert result.error is None
    assert "PATHLYNKS_PASSWORD" in result.hitl_prompt


def test_a_secret_value_inside_an_exception_message_is_scrubbed_before_persisting(
    tmp_path: Path,
) -> None:
    """AT-341: an exception's own message can embed a raw secret value (not
    only the named NavigationRefused case AT-076 introduced) — `_result`
    scrubs `error`/`hitl_prompt` through the session's own redactor before
    they ever reach a RawResult, the same boundary `_record` already holds
    for evidence paths."""
    steps = [
        Step(order=1, action=Action.FILL, target="input[name=password]",
             value="{{SECRET:PATHLYNKS_PASSWORD}}"),
        Step(order=2, action=Action.CLICK, target="button.leaks-a-secret"),
    ]
    session = session_with_fake_page(tmp_path)
    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.ERRORED
    assert "hunter2" not in result.error
    assert "REDACTED" in result.error


# -- E4 persistence round-trips through ProjectStore -------------------------

def test_run_and_result_round_trip_through_project_store(tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path)
    run = Run(project="pathlynks", case_ids=["case_abc123"])
    store.save_run(run)
    result = RawResult(case_id="case_abc123", outcome=Outcome.COMPLETED, duration_s=1.2)
    store.save_result(run.id, result)

    loaded_run = store.load_run(run.id)
    assert loaded_run is not None and loaded_run.id == run.id

    loaded_results = store.load_results(run.id)
    assert len(loaded_results) == 1
    assert loaded_results[0].case_id == "case_abc123"
    assert loaded_results[0].outcome is Outcome.COMPLETED


def test_load_results_for_an_unknown_run_is_empty_not_an_error(tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path)
    assert store.load_results("run_does_not_exist") == []


# D-014/Track B1 tests (an Action with no handler, and the new BACK/HOVER/
# PRESS_KEY/SCROLL actions) moved to test_execute_new_actions.py at the
# 300-line cap.
