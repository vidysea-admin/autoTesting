"""E4.3 (qa/contracts/e2e-fixes.md, AT-1415): every executed case keeps its `.webm` or says why not.

The two silent `None` paths of `VideoMixin.end_case_video` now record `video-lost`, and the run
page tells each case's video story: kept (linked), PASS pruned by design (run-video V2), lost
(with the recorded reason), over the duration cap, or recording off. Fakes only, no browser.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_video_lost_artifact import FakeVideo, _labels, _session

from autotester.browser.video import MAX_VIDEO_DURATION_S, video_fate
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import Evidence, RawResult, Run
from autotester.schema.verdict import Verdict
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

# --- the two silent paths are loud ----------------------------------------------------------

def test_a_page_with_no_video_object_records_video_lost(tmp_path: Path) -> None:
    session = _session(tmp_path, None)  # page.video is None while recording is on
    assert session.end_case_video() is None
    events = session.take_session_events()
    assert [e.label for e in events] == ["video-lost"]
    assert "case-1" in events[0].path and "no video" in events[0].path


def test_a_recording_file_that_never_appeared_records_video_lost(tmp_path: Path) -> None:
    session = _session(tmp_path, FakeVideo(tmp_path / "never-written.webm"))
    assert session.end_case_video() is None
    events = session.take_session_events()
    assert [e.label for e in events] == ["video-lost"]
    assert "never-written" not in events[0].path  # a reason, not a filesystem path
    assert "was not written" in events[0].path


def test_a_move_that_produced_no_final_file_records_video_lost(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = tmp_path / "scratch.webm"
    raw.write_bytes(b"webm")
    session = _session(tmp_path, FakeVideo(raw))
    monkeypatch.setattr(Path, "replace", lambda self, target: target)  # "moved", nothing there
    assert session.end_case_video() is None
    assert _labels(session) == ["video-lost"]


def test_recording_off_stays_silent_and_a_good_recording_is_unchanged(tmp_path: Path) -> None:
    off = _session(tmp_path, None)
    off.record_video = False
    assert off.end_case_video() is None and _labels(off) == []
    raw = tmp_path / "scratch.webm"
    raw.write_bytes(b"webm")
    good = _session(tmp_path, FakeVideo(raw))
    assert good.end_case_video() == "case-1.webm" and _labels(good) == []


# --- video_fate: one sentence per fate ------------------------------------------------------

KEPT = [Evidence(kind=EvidenceKind.VIDEO, path="c.webm")]
LOST = [Evidence(kind=EvidenceKind.DOM, path="video for case c was lost: x (OSError: y)",
                 label="video-lost")]


def test_a_kept_video_needs_no_explanation() -> None:
    assert video_fate(KEPT, passed=False, duration_s=1.0) == ""


def test_a_passed_case_says_the_video_was_pruned_by_design() -> None:
    text = video_fate([], passed=True, duration_s=1.0)
    assert text == "no video kept: the case passed (run-video V2: a PASS keeps no video)"


def test_a_lost_video_carries_the_recorded_reason_even_on_a_pass() -> None:
    for passed in (False, True):
        assert "was lost: x (OSError: y)" in video_fate(LOST, passed=passed, duration_s=1.0)


def test_a_case_over_the_duration_cap_says_so() -> None:
    text = video_fate([], passed=False, duration_s=MAX_VIDEO_DURATION_S + 1)
    assert "longer than 20 minutes" in text


def test_nothing_recorded_on_a_non_pass_says_recording_was_off_or_never_reached() -> None:
    text = video_fate([], passed=False, duration_s=1.0)
    assert "recording was off" in text and "never reached execution" in text


# --- the run page ---------------------------------------------------------------------------

def _seed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, result: Result,
          evidence: list[Evidence], duration_s: float = 1.0) -> str:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    case = Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="Login", steps=[Step(order=1, action=Action.NAVIGATE, target="/login")])
    store.add_case(case)
    store.save_run(Run(id="run-e4-video", project="demo", case_ids=[case.id]))
    store.save_result("run-e4-video", RawResult(
        case_id=case.id, outcome=Outcome.COMPLETED, duration_s=duration_s, evidence=evidence))
    store.save_verdict("run-e4-video", Verdict(
        run_id="run-e4-video", case_id=case.id, result=result, grader_provider="mock"))
    response = TestClient(app).get("/projects/demo/runs/run-e4-video")
    assert response.status_code == 200
    return response.text


def test_a_pass_case_section_reads_no_video_kept_the_case_passed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _seed(tmp_path, monkeypatch, Result.PASS, [])
    assert "no video kept: the case passed (run-video V2" in text


def test_a_failed_case_with_a_lost_video_shows_the_recorded_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _seed(tmp_path, monkeypatch, Result.FAIL, LOST)
    assert "was lost: x (OSError: y)" in text and "no video kept" not in text


def test_a_failed_case_with_a_kept_video_still_links_it_and_adds_no_excuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _seed(tmp_path, monkeypatch, Result.FAIL, KEPT)
    assert "/runs/run-e4-video/videos/c.webm" in text
    assert "no video" not in text


def test_a_failed_case_with_nothing_recorded_is_never_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _seed(tmp_path, monkeypatch, Result.FAIL, [])
    assert "recording was off for this session" in text
