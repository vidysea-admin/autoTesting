"""AT-787: the executor records the failing step and the failure bundle names it.

Offline. A real `run_case` against the fake page produces the `RawResult`; the bundle stage then
reads only that artifact. Pins: the recorded step beats the max-evidence heuristic, a passing
case yields no bundle, and a result with no recorded step falls back with an explicit marker.
"""

from __future__ import annotations

from pathlib import Path

from test_execute import LOGIN, make_case, session_with_fake_page
from test_run_failure_artifacts import _launch

from autotester.core.redact import Redactor
from autotester.schema.enums import Action, Outcome, Result
from autotester.schema.failure_bundle import BundleIndex
from autotester.schema.flowspec import Step
from autotester.schema.verdict import Verdict
from autotester.stages.execute import run_case
from autotester.stages.failure_bundle import build_failure_bundle, load_bundle

RUN = "run_787"


def _failing_case_result(tmp_path: Path):
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.CLICK, target="button[type=submit]",
             expected={"visible_text": ["Dashboard"]}),
        Step(order=3, action=Action.CLICK, target="button.next"),
    ]
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "Invalid credentials"
    case = make_case(steps)
    return case, run_case(case, session)


def _bundle(tmp_path: Path, case, result, **over) -> Path:
    verdict = Verdict(run_id=RUN, case_id=case.id, result=Result.FAIL)
    args = dict(out_dir=tmp_path / "bundles", run_id=RUN, case=case, result=result,
                verdict=verdict, sources=[], spans=[], redactor=Redactor({}))
    args.update(over)
    return build_failure_bundle(**args)


def test_assertion_failure_records_step_and_bundle_names_it(tmp_path: Path) -> None:
    case, result = _failing_case_result(tmp_path)
    assert result.outcome is Outcome.ASSERTION_FAILED and result.failing_step == 2
    # the heuristic (max evidence step) would say 3: the run continued past the failure
    assert max(e.step_order for e in result.evidence if e.step_order is not None) == 3
    manifest = load_bundle(_bundle(tmp_path, case, result))
    assert manifest.failing_step == 2 and manifest.failing_step_source == "recorded"
    assert 2 in manifest.steps_included
    named = next(f for f in manifest.files if f.name == "steps/2.json")
    body = (tmp_path / "bundles" / manifest.bundle_id / named.name).read_text()
    assert '"click"' in body.lower() and "button[type=submit]" in body


def test_raising_step_is_the_recorded_failing_step(tmp_path: Path) -> None:
    steps = [Step(order=1, action=Action.NAVIGATE, target=LOGIN),
             Step(order=2, action=Action.CLICK, target="button.broken")]
    session = session_with_fake_page(tmp_path)
    case = make_case(steps)
    result = run_case(case, session)
    assert result.outcome is Outcome.ERRORED and result.failing_step == 2
    assert load_bundle(_bundle(tmp_path, case, result)).failing_step == 2


def test_passing_case_records_no_step_and_makes_no_bundle(tmp_path, monkeypatch) -> None:
    session = session_with_fake_page(tmp_path)
    result = run_case(make_case([Step(order=1, action=Action.NAVIGATE, target=LOGIN)]), session)
    assert result.outcome is Outcome.COMPLETED and result.failing_step is None
    store, run, _case, _orig = _launch(tmp_path / "launch", monkeypatch,
                                       verdict_result=Result.PASS)
    index = BundleIndex.model_validate_json(
        (store.paths.bundles_dir(run.id) / "index.json").read_text())
    assert index.cases == []
    assert not [p for p in store.paths.bundles_dir(run.id).iterdir() if p.name.startswith("fb_")]


def test_missing_step_falls_back_to_heuristic_with_marker(tmp_path: Path) -> None:
    case, result = _failing_case_result(tmp_path)
    legacy = result.model_copy(update={"failing_step": None})
    manifest = load_bundle(_bundle(tmp_path, case, legacy))
    assert manifest.failing_step == 3 and manifest.failing_step_source == "heuristic_fallback"
    unknown = result.model_copy(update={"failing_step": 99})
    other = load_bundle(_bundle(tmp_path / "x", case, unknown))
    assert other.failing_step_source == "heuristic_fallback"
