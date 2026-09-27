"""VIEWPORT_MOBILE / LOCALE_I18N execution-condition enactment (D-045/AT-581, E6).

qa/contracts/execute.md E6: a case whose `case_class` names an execution condition either
runs under that condition, or is reported not-run -- it never yields a PASS from a run at
the default desktop viewport/locale. Before this fix (AT-581), `browser/launch.py` hard-coded
a 1366x850 desktop viewport with no locale override, and nothing in `execute.py` or `browser/`
read `case_class` at all: a VIEWPORT_MOBILE or LOCALE_I18N case ran exactly like HAPPY and
could PASS on evidence that proves nothing about mobile layout or a non-default locale.

Fix shape: `browser/conditions.py::enact` is the enactment seam `run_case` calls before a
case's steps run. VIEWPORT_MOBILE is enactable (`page.set_viewport_size` works on an
already-launched context) and is reset after the case so a reused session (AT-577's serial
route) never leaks it into a later, unrelated case. LOCALE_I18N is NOT enactable here --
Playwright's `locale` is fixed at `launch_persistent_context()` time, and the session's
context is already running by the time a case reaches this seam -- so it is reported
`Outcome.NOT_RUN` with a reason, and `grade.py::_outcome_verdict` short-circuits it to
`Result.INCONCLUSIVE` before it could ever reach a judge and come back PASS.
"""

from __future__ import annotations

from pathlib import Path

from test_execute import LOGIN, FakePage, make_project, make_store

from autotester.browser import conditions
from autotester.browser.launch import DEFAULT_VIEWPORT
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.providers.mock import MockProvider
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.verdict import Criterion, Rubric
from autotester.stages.execute import run_case
from autotester.stages.grade import grade


class ViewportFakePage(FakePage):
    """`FakePage` plus a recorded `set_viewport_size` -- the real Playwright API
    `browser/conditions.py::enact` calls to satisfy a VIEWPORT_MOBILE case."""

    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.viewport_size: dict[str, int] | None = None
        self.viewport_calls: list[dict[str, int]] = []
        """Every `set_viewport_size` call in order -- `run_case` resets the viewport in a
        `finally` before it returns, so a test proving what happened DURING a case's own
        steps (as opposed to its state after the case finished) reads this, not the final
        `viewport_size`."""

    def set_viewport_size(self, size: dict[str, int]) -> None:
        self.viewport_size = dict(size)
        self.viewport_calls.append(dict(size))


def _session(tmp_path: Path) -> BrowserSession:
    paths = ProjectPaths("pathlynks", tmp_path)
    session = BrowserSession(make_project(), make_store(tmp_path), tmp_path / "run", paths)
    session._page = ViewportFakePage(LOGIN)
    session.state.run_dir.mkdir(parents=True, exist_ok=True)
    return session


def _case(case_class: CaseClass, steps: list[Step]) -> Case:
    return Case(project="pathlynks", flow_id="flow_login", kind=CaseKind.EDGE,
                case_class=case_class, title=f"log in — {case_class.value}", steps=steps)


def make_rubric() -> Rubric:
    return Rubric(id="rub_x", criteria=[Criterion(id="c1", text="the case completes")])


# -- capability: VIEWPORT_MOBILE is enacted, never a silent desktop run ------

def test_viewport_mobile_case_enacts_mobile_size_before_its_steps_run(tmp_path: Path) -> None:
    """Falsifying edit: if `run_case` stopped calling the enactment seam (the
    AT-581 bug -- the viewport stayed the hard-coded desktop default), the
    page would never see a `set_viewport_size` call at all and `viewport_calls`
    would be empty; the case's own step must still run under the condition."""
    session = _session(tmp_path)
    case = _case(CaseClass.VIEWPORT_MOBILE, [Step(order=1, action=Action.CLICK, target="#a")])

    result = run_case(case, session)

    assert session.page.viewport_calls[0] == conditions.MOBILE_VIEWPORT
    assert result.outcome is Outcome.COMPLETED
    assert session.page.clicks == ["#a"]


def test_viewport_resets_to_default_after_the_case_for_a_reused_session(tmp_path: Path) -> None:
    """AT-577's session-reuse shape: the serial route runs many cases on one
    session. A mobile case must resize for its own steps, then hand the
    session back at the default -- a later, unrelated HAPPY case must see no
    further resize at all."""
    session = _session(tmp_path)
    mobile_case = _case(
        CaseClass.VIEWPORT_MOBILE, [Step(order=1, action=Action.CLICK, target="#a")]
    )
    happy_case = _case(CaseClass.HAPPY, [Step(order=1, action=Action.CLICK, target="#b")])

    run_case(mobile_case, session)
    assert session.page.viewport_calls == [conditions.MOBILE_VIEWPORT, DEFAULT_VIEWPORT]
    run_case(happy_case, session)

    assert session.page.viewport_calls == [conditions.MOBILE_VIEWPORT, DEFAULT_VIEWPORT], (
        "HAPPY must never touch the viewport, including on a session a prior case resized"
    )
    assert session.page.viewport_size == DEFAULT_VIEWPORT


# -- capability: LOCALE_I18N cannot be enacted on an already-launched context;
#    it is reported not-run and never touches a step or reaches the judge ----

def test_locale_i18n_case_is_reported_not_run_and_no_step_executes(tmp_path: Path) -> None:
    session = _session(tmp_path)
    case = _case(CaseClass.LOCALE_I18N, [Step(order=1, action=Action.CLICK, target="#a")])

    result = run_case(case, session)

    assert result.outcome is Outcome.NOT_RUN
    assert result.not_run_reason
    assert "locale" in result.not_run_reason.lower()
    assert session.page.clicks == [], "a NOT_RUN case must never run its steps"
    assert result.evidence == []


def test_locale_i18n_never_reaches_the_judge_and_is_never_pass(tmp_path: Path) -> None:
    """Falsifying edit: if `grade.py::_outcome_verdict` stopped short-circuiting
    NOT_RUN, this reddens two ways at once -- `judge.prompts` becomes non-empty
    (the mock has no queued response and would raise), and a judge that could
    say PASS is exactly what E6 forbids ever reaching."""
    session = _session(tmp_path)
    case = _case(CaseClass.LOCALE_I18N, [Step(order=1, action=Action.CLICK, target="#a")])
    result = run_case(case, session)
    judge = MockProvider()  # no queued response -- calling it would raise ProviderError

    verdict = grade(make_rubric(), result, "run_1", judge)

    assert verdict.result is Result.INCONCLUSIVE
    assert verdict.result is not Result.PASS
    assert judge.prompts == []
    assert verdict.note == result.not_run_reason


# -- capability: an unrelated class is unaffected -----------------------------

def test_happy_case_is_unaffected_by_the_condition_seam(tmp_path: Path) -> None:
    session = _session(tmp_path)
    case = _case(CaseClass.HAPPY, [Step(order=1, action=Action.CLICK, target="#a")])

    result = run_case(case, session)

    assert result.outcome is Outcome.COMPLETED
    assert session.page.viewport_size is None, "HAPPY must never touch the viewport"


# -- unit: browser/conditions.py's own contract -------------------------------

def test_enact_returns_none_and_resizes_for_viewport_mobile(tmp_path: Path) -> None:
    session = _session(tmp_path)

    reason = conditions.enact(session, CaseClass.VIEWPORT_MOBILE)

    assert reason is None
    assert session.page.viewport_size == conditions.MOBILE_VIEWPORT


def test_enact_returns_a_reason_for_locale_i18n_and_touches_nothing(tmp_path: Path) -> None:
    session = _session(tmp_path)

    reason = conditions.enact(session, CaseClass.LOCALE_I18N)

    assert reason == conditions.LOCALE_NOT_ENACTABLE_REASON
    assert session.page.viewport_size is None


def test_enact_is_a_no_op_for_a_class_with_no_condition() -> None:
    class ExplodingPage:
        def set_viewport_size(self, *_a: object, **_k: object) -> None:
            raise AssertionError("must not be called for a class with no execution condition")

    class FakeSession:
        page = ExplodingPage()

    assert conditions.enact(FakeSession(), CaseClass.HAPPY) is None
