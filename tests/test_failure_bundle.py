"""T-178 driver: the atomic failure bundle (qa/contracts/failure-bundle.md FB1-FB3).

Fully offline: a fixture case/result/verdict, tiny fake PNG files, and a `Redactor`
holding one planted secret. FB4 (priority) and FB5 (pruning) are deferred.
"""

from __future__ import annotations

import json
from pathlib import Path

import check_no_secrets as cns
import pytest

from autotester.core.redact import Redactor
from autotester.schema.case import Case
from autotester.schema.enums import (
    Action,
    CaseClass,
    CaseKind,
    EvidenceKind,
    Outcome,
    Result,
)
from autotester.schema.failure_bundle import BundleSource
from autotester.schema.flowspec import Step
from autotester.schema.run import Evidence, RawResult
from autotester.schema.run_state import StageName
from autotester.schema.trace import StageSpan
from autotester.schema.verdict import Failure, Verdict
from autotester.stages.failure_bundle import (
    PartialBundleError,
    RunMixError,
    UnmaskedScreenshotError,
    build_failure_bundle,
    load_bundle,
    sources_from_result,
)

RUN = "run_A"
OTHER = "run_B"
SECRET = "Zq7-planted-Secret-9981"
PNG = b"\x89PNG\r\n\x1a\nfake-masked-pixels"


def _case(n_steps: int = 5, secret_in_note: bool = False) -> Case:
    steps = [
        Step(order=i, action=Action.CLICK, target=f"button {i}",
             note=f"typed {SECRET}" if secret_in_note and i == 3 else None)
        for i in range(1, n_steps + 1)
    ]
    steps[1] = Step(order=2, action=Action.FILL, target="password field",
                    value="{{SECRET:APP_PASSWORD}}")
    return Case(project="demo", flow_id="login", kind=CaseKind.WORST,
                case_class=CaseClass.AUTH_WRONG_CREDS, title="wrong password", steps=steps)


def _shots(tmp: Path, orders: list[int], masked: bool = True) -> list[Evidence]:
    out = []
    for o in orders:
        (tmp / f"s{o}.png").write_bytes(PNG)
        out.append(Evidence(kind=EvidenceKind.SCREENSHOT, path=f"s{o}.png", step_order=o,
                            masked=masked, label=f"step {o}"))
    return out


def _fixture(tmp: Path, *, n_steps: int = 5, fail_at: int = 3, error: str = "locator timed out",
             verdict_reason: str = "login did not error", secret_in_note: bool = False,
             label: str | None = None):
    case = _case(n_steps, secret_in_note)
    ev = _shots(tmp, list(range(1, fail_at + 2)))
    if label:
        ev[0] = ev[0].model_copy(update={"label": label})
    result = RawResult(case_id=case.id, outcome=Outcome.ERRORED, error=error, evidence=ev)
    verdict = Verdict(run_id=RUN, case_id=case.id, result=Result.FAIL,
                      failures=[Failure(criterion_id="c1", reason=verdict_reason)])
    span = StageSpan(trace_id=RUN, stage=StageName.EXECUTE, status="failed",
                     error=error)
    return case, result, verdict, [span]


def _build(tmp: Path, fx, **over) -> Path:
    case, result, verdict, spans = fx
    args = dict(out_dir=tmp / "bundles", run_id=RUN, case=case, result=result, verdict=verdict,
                sources=sources_from_result(RUN, tmp, result), spans=spans,
                redactor=Redactor({"APP_PASSWORD": SECRET}), failing_step=fail_step(result))
    args.update(over)
    return build_failure_bundle(**args)


def fail_step(result: RawResult) -> int:
    return 3


def _names(bundle: Path) -> set[str]:
    return {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()}


# -- FB1 ---------------------------------------------------------------------------------
def test_complete_bundle_is_self_contained_with_neighbours(tmp_path: Path) -> None:
    bundle = _build(tmp_path, _fixture(tmp_path))
    manifest = load_bundle(bundle)
    assert manifest.failing_step == 3 and manifest.steps_included == [2, 3, 4]
    names = _names(bundle)
    assert {"case.json", "verdict.json", "result.json", "error.txt", "trace.jsonl",
            "manifest.json", "steps/2.json", "steps/3.json", "steps/4.json"} <= names
    assert {n for n in names if n.startswith("screenshots/")} == {
        "screenshots/2-0.png", "screenshots/3-1.png", "screenshots/4-2.png"}
    assert not list((tmp_path / "bundles").glob("*.partial"))
    assert (bundle / "error.txt").read_text(encoding="utf-8").strip() == "locator timed out"


def test_first_and_last_steps_only_include_the_neighbours_that_exist(tmp_path: Path) -> None:
    fx = _fixture(tmp_path, fail_at=1)
    manifest = load_bundle(_build(tmp_path, fx, failing_step=1))
    assert manifest.steps_included == [1, 2]
    other = tmp_path / "last"
    other.mkdir()
    fx = _fixture(other, fail_at=4)
    manifest = load_bundle(_build(other, fx, failing_step=5))
    assert manifest.steps_included == [4, 5]


def test_a_write_that_dies_mid_bundle_leaves_only_the_partial_and_the_loader_refuses(
        tmp_path: Path) -> None:
    fx = _fixture(tmp_path)
    (tmp_path / "s4.png").unlink()  # the writer dies copying the step-4 screenshot
    with pytest.raises(FileNotFoundError):
        _build(tmp_path, fx)
    out = tmp_path / "bundles"
    complete = [p for p in out.iterdir() if not p.name.endswith(".partial")]
    partials = [p for p in out.iterdir() if p.name.endswith(".partial")]
    assert complete == [], "a complete-looking bundle exists after a crash"
    assert len(partials) == 1
    with pytest.raises(PartialBundleError):
        load_bundle(partials[0])
    with pytest.raises(PartialBundleError):
        load_bundle(out / partials[0].name.removesuffix(".partial"))


def test_loader_refuses_a_tampered_or_incomplete_bundle(tmp_path: Path) -> None:
    bundle = _build(tmp_path, _fixture(tmp_path))
    (bundle / "steps" / "3.json").write_text("{}", encoding="utf-8")
    with pytest.raises(PartialBundleError):
        load_bundle(bundle)
    again = _build(tmp_path, _fixture(tmp_path))  # a corrupt bundle is rebuilt, not trusted
    assert load_bundle(again).steps_included == [2, 3, 4]
    (again / "manifest.json").unlink()
    with pytest.raises(PartialBundleError):
        load_bundle(again)


def test_a_repeat_build_returns_the_same_bundle(tmp_path: Path) -> None:
    fx = _fixture(tmp_path)
    assert _build(tmp_path, fx) == _build(tmp_path, fx)


# -- FB2 ---------------------------------------------------------------------------------
def test_a_screenshot_from_another_run_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    fx = _fixture(tmp_path)
    sources = sources_from_result(RUN, tmp_path, fx[1])
    sources[1] = sources[1].model_copy(update={"run_id": OTHER})
    with pytest.raises(RunMixError):
        _build(tmp_path, fx, sources=sources)
    assert not (tmp_path / "bundles").exists()


def test_a_planted_screenshot_outside_the_window_still_refuses(tmp_path: Path) -> None:
    fx = _fixture(tmp_path)
    sources = sources_from_result(RUN, tmp_path, fx[1])
    sources.append(BundleSource(run_id=OTHER, path=tmp_path / "s1.png", step_order=1,
                                masked=True))
    with pytest.raises(RunMixError):
        _build(tmp_path, fx, sources=sources)


def test_a_verdict_or_trace_span_from_another_run_is_refused(tmp_path: Path) -> None:
    case, result, verdict, spans = _fixture(tmp_path)
    with pytest.raises(RunMixError):
        _build(tmp_path, (case, result, verdict.model_copy(update={"run_id": OTHER}), spans))
    with pytest.raises(RunMixError):
        _build(tmp_path, (case, result, verdict,
                          [spans[0].model_copy(update={"trace_id": OTHER})]))
    assert not (tmp_path / "bundles").exists()


def test_the_loader_refuses_a_file_stamped_with_another_run(tmp_path: Path) -> None:
    bundle = _build(tmp_path, _fixture(tmp_path))
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][0]["run_id"] = OTHER
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RunMixError):
        load_bundle(bundle)


# -- FB3 ---------------------------------------------------------------------------------
def test_no_planted_secret_reaches_any_part_of_the_bundle(tmp_path: Path) -> None:
    fx = _fixture(tmp_path, error=f"timed out filling password field with {SECRET}",
                  verdict_reason=f"page echoed {SECRET}", secret_in_note=True,
                  label=f"label {SECRET}")
    case, result, verdict, spans = fx
    span = spans[0].model_copy(update={"error": f"fill {SECRET} failed"})
    bundle = _build(tmp_path, (case, result, verdict, [span]))
    files = [p for p in bundle.rglob("*") if p.is_file()]
    assert len(files) >= 9
    for path in files:
        assert SECRET.encode() not in path.read_bytes(), path.name
        assert SECRET not in path.name
    assert all(cns.scan(files, [SECRET]).values())
    assert "[REDACTED]" in (bundle / "error.txt").read_text(encoding="utf-8")


def test_an_unmasked_screenshot_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    case, result, verdict, spans = _fixture(tmp_path)
    result.evidence[2] = result.evidence[2].model_copy(update={"masked": False})
    with pytest.raises(UnmaskedScreenshotError):
        _build(tmp_path, (case, result, verdict, spans))
    assert not (tmp_path / "bundles").exists()


def test_a_residual_secret_the_scrub_cannot_remove_aborts_the_write(tmp_path: Path) -> None:
    class LeakyRedactor(Redactor):
        def scrub(self, text: str) -> str:
            return text  # a broken scrub: the assert_clean gate must still stop the write

    fx = _fixture(tmp_path, error=f"leak {SECRET}")
    with pytest.raises(ValueError, match="raw secret"):
        _build(tmp_path, fx, redactor=LeakyRedactor({"APP_PASSWORD": SECRET}))
    out = tmp_path / "bundles"
    assert [p for p in out.iterdir() if not p.name.endswith(".partial")] == []
