"""T-191/AT-587 V1/V2/V7, real browser: a case run through the production
pipeline (`run_and_grade_case`) with `record_video=True` produces exactly one
video file, kept only when the verdict is FAIL or INCONCLUSIVE (never PASS).
Contract: qa/contracts/run-video.md V1, V2, V7. V3/V4 (masking) live in
`test_video_masking_live.py` -- a real interaction/frame-diff proof is a
different, heavier fixture than this file's plain kept/pruned check. V5
(retention) is `test_video_retention.py`; V6 is `test_video_ram_budget.py` +
`test_video_duration_cap.py`; V8 is `test_video_report_export.py` -- split so
none of these grows past doctor's 300-line file cap.

FAKE credentials only (the `login_site` fixture's own test password) -- never
a live account, per CLAUDE.md's Credentials boundary.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.providers.mock import MockProvider
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.verdict import Failure, Judgment, Verdict
from autotester.stages import run_case_pipeline as pipeline
from autotester.stages.run_case_pipeline import run_and_grade_case
from autotester.store.project_store import ProjectStore

SITE = Path(__file__).resolve().parent / "fixtures" / "login_site"


def _skip_if_no_chromium() -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    try:
        with sync_api.sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as exc:  # pragma: no cover - browser binary missing
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")


def _project(base_url: str) -> Project:
    return Project(slug="video-demo", name="Video Demo", base_url=base_url,
                   allowed_domains=["127.0.0.1"], headed=False)


def _case(base_url: str, flow_id: str) -> Case:
    return Case(
        project="video-demo", flow_id=flow_id, kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title=f"sign in ({flow_id})", rationale="signing in succeeds",
        steps=[
            Step(order=1, action=Action.NAVIGATE, target=f"{base_url}/login.html"),
            Step(order=2, action=Action.FILL, target="#username", value="tester"),
            Step(order=3, action=Action.FILL, target="#password", value="fixture-pass"),
            Step(order=4, action=Action.CLICK, target="#sign-in"),
        ],
    )


def _judge(result: Result) -> MockProvider:
    failures = [Failure(criterion_id="c1", reason="did not meet the claim",
                        evidence_refs=["01-step01-navigate.png"])] \
        if result is Result.FAIL else []
    return MockProvider(responses={"judge": [
        Judgment(result=result, criteria_met=0 if failures else 1, criteria_total=1,
                 scoreboard="graded by test double", failures=failures),
    ]})


def _session(tmp_path: Path, base_url: str) -> tuple[BrowserSession, ProjectStore, Project]:
    project = _project(f"{base_url}/login.html")
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    paths = ProjectPaths("video-demo", tmp_path)
    store = ProjectStore("video-demo", tmp_path)
    store.save_project(project)
    # Must match what `_finalize_video` deletes from (`store.paths.run_dir(run_id)`
    # inside `run_and_grade_case`) -- an ad hoc `tmp_path / "runs" / "run_1"` here
    # would silently miss every unlink (`missing_ok=True`), which is exactly the
    # false "PASS video survives" failure this test caught while being written.
    session = BrowserSession(project, secrets, paths.run_dir("run_1"), paths,
                             record_video=True)
    session.start()
    return session, store, project


def test_video_is_recorded_and_kept_only_for_fail_and_inconclusive_never_pass(
    tmp_path: Path, serve_dir: Callable[[Path], str], monkeypatch,
) -> None:
    """V1: exactly one video file per case. V2: PASS's video is pruned, FAIL's
    and INCONCLUSIVE's survive -- the record-then-discard-on-PASS shape gate
    answer A requires, since the verdict is not known until after the video
    is already captured."""
    # V2 exercises retention for each verdict independently of grading's privacy
    # downgrade: screenshot-bearing mock PASS is now correctly INCONCLUSIVE.
    def controlled_grade(rubric, raw, run_id, provider, **_kwargs):
        judgment = provider.judge("controlled video-retention verdict", Judgment)
        return Verdict(run_id=run_id, case_id=raw.case_id, rubric_hash=rubric.fingerprint,
                       grader_provider=provider.id, **judgment.model_dump(exclude={
                           "defect_observed", "defect_summary"}))

    monkeypatch.setattr(pipeline, "grade", controlled_grade)
    _skip_if_no_chromium()
    base = serve_dir(SITE)
    session, store, _ = _session(tmp_path, base)
    run_dir = session.state.run_dir
    cases_and_results = {}
    try:
        for flow_id, verdict_result in (
            ("flow-pass", Result.PASS),
            ("flow-fail", Result.FAIL),
            ("flow-inconclusive", Result.INCONCLUSIVE),
        ):
            case = _case(base, flow_id)
            result, verdict = run_and_grade_case(case, session, _judge(verdict_result),
                                                 "run_1", store)
            cases_and_results[flow_id] = (case, result, verdict)
    finally:
        session.close()

    videos = sorted(p.name for p in run_dir.rglob("*.webm"))

    pass_case = cases_and_results["flow-pass"][0]
    fail_case, fail_result, fail_verdict = cases_and_results["flow-fail"]
    inc_case = cases_and_results["flow-inconclusive"][0]

    assert fail_verdict.result is Result.FAIL, fail_verdict.scoreboard  # sanity: judge honored
    assert f"{pass_case.id}.webm" not in videos, "a PASS video must be pruned"
    assert f"{fail_case.id}.webm" in videos, "a FAIL video must be kept"
    assert f"{inc_case.id}.webm" in videos, "an INCONCLUSIVE video must be kept"
    assert len(videos) == 2  # V1: exactly one file per kept case, no strays

    video_evidence = [e for e in fail_result.evidence if e.kind is EvidenceKind.VIDEO]
    assert len(video_evidence) == 1
    assert video_evidence[0].path == f"{fail_case.id}.webm"
    assert (run_dir / video_evidence[0].path).stat().st_size > 0  # a real, non-empty recording


def test_video_option_and_its_prune_function_each_have_a_single_choke_point() -> None:
    """V7 (C3): the ONLY place `record_video_dir`/`record_video_size` are ever
    assigned into Playwright's own launch options is `browser/launch.py`; the
    only function anywhere that deletes a video based on a verdict is
    `stages/run_case_pipeline.py::_finalize_video`."""
    src = Path(__file__).resolve().parents[1] / "src" / "autotester"
    py_files = list(src.rglob("*.py"))

    def _files_containing(needle: str) -> list[str]:
        return sorted({p.name for p in py_files if needle in p.read_text(encoding="utf-8")})

    assert _files_containing('options["record_video_dir"] =') == ["launch.py"]
    assert _files_containing('options["record_video_size"] =') == ["launch.py"]
    assert _files_containing("def _finalize_video(") == ["run_case_pipeline.py"]
