"""The preflight probe floor equals what the executor really spends (ISS-d063-grant-budget-3).

`execute.probe_request` must never undercount: a human row granting `probe_request(cases)` probes
has to carry a run whose expectations are all met at once (the minimum), and a row granting one
fewer has to stop. The fake session below runs the REAL `execute._run_steps` and the REAL
`browser/assertions.py`; only the browser calls are stubbed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from run_approval_fixture import grant_live_case_approval

from autotester.browser import assertions
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind
from autotester.schema.flowspec import ExpectedState, Step
from autotester.stages import execute
from autotester.stages.execute import probe_request
from autotester.stages.run_budget import RunBudget
from autotester.store.project_store import ProjectStore

URL = "https://demo.test/home"
PATHLYNKS = Path(__file__).resolve().parents[1] / "projects" / "pathlynks" / "cases.jsonl"


class _Loc:
    def inner_text(self, **_: object) -> str:
        return "Welcome home"


class _Page:
    url = URL

    def locator(self, _: str) -> _Loc:
        return _Loc()

    def wait_for_timeout(self, _: float) -> None:
        pass

    def wait_for_load_state(self, *_: object, **__: object) -> None:
        pass


class _State:
    def __init__(self) -> None:
        self.evidence: list = []
        self.evidence_start = 0


class _Secrets:
    def scrub_optional(self, text: str | None) -> str | None:
        return text


class FakeSession:
    """Stubs the browser; probes are charged by the real assertion code and the real fill shape."""

    observer = None
    recorder = None
    secrets = _Secrets()

    def __init__(self, budget: RunBudget) -> None:
        self.budget, self.page, self.state = budget, _Page(), _State()

    def _timeout(self, ms: int | None = None) -> dict:
        return {"timeout": ms} if ms is not None else {}

    def _record(self, kind: EvidenceKind, path: str, step_order: int | None = None):
        from autotester.schema.run import Evidence
        item = Evidence(kind=kind, path=path)
        self.state.evidence.append(item)
        return item

    def fill(self, *_a: object, **_k: object) -> None:      # session.fill: before + after sample
        assertions._probe(self)
        assertions._probe(self)

    def settle(self, expected: ExpectedState | None = None) -> None:
        assertions.settle(self, expected)

    def assert_expected(self, expected: ExpectedState, *, step_order: int | None = None):
        return assertions.assert_expected(self, expected, step_order=step_order)

    def __getattr__(self, name: str):                        # goto/click/select/...: no probes
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: None


def _step(order: int, action: Action, **expected: object) -> Step:
    value = "v" if action in (Action.FILL, Action.SELECT) else None
    return Step(order=order, action=action, target="#x", value=value,
                expected=ExpectedState(**expected))


def _case(*steps: Step) -> Case:
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="t", steps=list(steps))


KINDS = {
    "click-plain": _step(0, Action.CLICK),
    "click-url": _step(0, Action.CLICK, url="/home"),
    "click-text": _step(0, Action.CLICK, visible_text=["Welcome"]),
    "navigate-plain": _step(0, Action.NAVIGATE),
    "navigate-url": _step(0, Action.NAVIGATE, url="/home"),
    "back-url": _step(0, Action.BACK, url="/home"),
    "fill-plain": _step(0, Action.FILL),
    "fill-text": _step(0, Action.FILL, visible_text=["Welcome"]),
    "assert-empty": _step(0, Action.ASSERT),
    "assert-url": _step(0, Action.ASSERT, url="/home"),
    "select-text": _step(0, Action.SELECT, visible_text=["Welcome"]),
    "hover-plain": _step(0, Action.HOVER),
    "wait-plain": _step(0, Action.WAIT),
}


def _spend(cases: list[Case], tmp_path: Path, max_probes: int) -> int:
    row = grant_live_case_approval(ProjectStore("demo", tmp_path), target="https://x",
                                   max_probes=max_probes, max_actions=10**6)
    budget = RunBudget(row)
    session = FakeSession(budget)
    for case in cases:
        execute._run_steps(case, session, 0.0, 0)   # type: ignore[arg-type]
    return budget.probes_used


@pytest.fixture(autouse=True)
def _root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_preflight_floor_equals_runtime_spend_per_step_kind(kind: str, tmp_path: Path) -> None:
    case = _case(KINDS[kind])
    assert _spend([case], tmp_path, 1000) == probe_request([case])


def test_preflight_floor_equals_runtime_spend_for_every_kind_together(tmp_path: Path) -> None:
    steps = [step.model_copy(update={"order": i}) for i, step in enumerate(KINDS.values())]
    case = _case(*steps)
    assert probe_request([case]) > 0 and _spend([case], tmp_path, 1000) == probe_request([case])


def test_one_probe_below_the_floor_stops_the_run(tmp_path: Path) -> None:
    case = _case(KINDS["navigate-url"])
    floor = probe_request([case])
    assert floor == 3
    assert _spend([case], tmp_path, floor) == floor
    result = _spend([case], tmp_path, floor - 1)    # _run_steps records a budget stop, no raise
    assert result < floor


@pytest.mark.skipif(not PATHLYNKS.is_file(), reason="pathlynks cases not present")
def test_pathlynks_shaped_cases_floor_equals_runtime_spend(tmp_path: Path) -> None:
    cases = [Case.model_validate_json(line) for line in PATHLYNKS.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    steps = [s for c in cases for s in c.steps]
    assert any(s.action not in (Action.FILL, Action.ASSERT)
               and (s.expected.url or s.expected.visible_text) for s in steps)
    assert probe_request(cases) > 20      # the cycle-0 undercount was 20 on these cases
    # these expectations are not met by the stub page, so the run polls: spend >= the floor
    assert _spend(cases, tmp_path, 10**6) >= probe_request(cases)


def test_a_zero_probe_row_is_refused_for_a_navigate_with_an_expected_url(tmp_path: Path) -> None:
    from autotester.schema.project import Project
    from autotester.stages.run_launcher import LaunchRefused, require_live_case_approval
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test/app",
                               allowed_domains=["demo.test"]))
    grant_live_case_approval(store, target="https://demo.test/app", max_probes=0)
    with pytest.raises(LaunchRefused, match="probes 3 > approved 0"):
        require_live_case_approval(store.load_project(), store, [_case(KINDS["navigate-url"])])
