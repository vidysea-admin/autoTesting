"""AT-927 / T-155: behavioural captures and verdicts persist under projects/<slug>/ai/ and the
workbook reads them back (ai-target.md AI6, AI9, AI11, AI14; Umesh 2026-10-17: ai/ + Excel only)."""
from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from openpyxl import load_workbook
from run_approval_fixture import project_of

from autotester.core.paths import ProjectPaths
from autotester.core.redact import Redactor
from autotester.core.safe_names import UnsafeName
from autotester.providers.mock import MockProvider
from autotester.schema.ai_check import AiCapture, AiCheckKind, AiExchange, AiReply
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind, Result
from autotester.schema.verdict import Failure, Judgment, Verdict
from autotester.stages.ai_capture import CaptureWithheld, capture_id, capture_run, store_capture
from autotester.stages.ai_judge import judge_capture
from autotester.stages.ai_report import export_ai_report
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore

URL = "https://llm.test/chat"
SECRET = "sk-live-1234567890abcdef"
NOW = datetime(2026, 10, 7, tzinfo=UTC)


def _approval() -> RunApproval:
    return RunApproval(
        project="demo", run_kind=ApprovalKind.LIVE_CASE, target=URL, scope="capture",
        max_actions=10, max_probes=1, wall_clock_s=60.0, granted_by="umesh",
        granted_at="2026-10-01", expires_at="2026-12-01").sign()


def _redactor() -> Redactor:
    return Redactor({"KEY": SECRET})


def _by_hand(response: str = "ok", check: AiCheckKind = AiCheckKind.RESPONSE_SHAPE) -> AiCapture:
    return AiCapture(project="demo", endpoint=URL, check=check, expected_keys=["answer"],
                     exchanges=[AiExchange(prompt="hi", response=response, latency_s=0.1)])


def _folder(paths: ProjectPaths, cap: AiCapture) -> Path:
    return paths.dir / "ai" / "behavioural" / capture_id(cap)


def test_the_capture_folder_comes_from_project_paths_and_is_one_safe_segment(
        tmp_path: Path) -> None:
    paths = ProjectPaths("demo", tmp_path)
    assert paths.ai_dir == tmp_path / "projects" / "demo" / "ai"
    assert paths.ai_capture_dir("aic_abc") == paths.ai_dir / "behavioural" / "aic_abc"
    with pytest.raises(UnsafeName):
        paths.ai_capture_dir("../escape")


def test_capture_id_is_stable_for_the_same_check_endpoint_and_prompts() -> None:
    assert capture_id(_by_hand("a")) == capture_id(_by_hand("b"))
    assert capture_id(_by_hand()) != capture_id(_by_hand(check=AiCheckKind.LATENCY_BUDGET))


def test_store_capture_writes_a_readable_capture_json(tmp_path: Path) -> None:
    paths = ProjectPaths("demo", tmp_path)
    cap = _by_hand()
    folder = store_capture(paths, cap, _redactor())
    assert folder == _folder(paths, cap)
    assert read_json(folder / "capture.json", AiCapture) == cap
    assert [p.name for p in folder.iterdir()] == ["capture.json"]  # no temp file left


def test_a_planted_secret_never_reaches_capture_json(tmp_path: Path) -> None:
    paths = ProjectPaths("demo", tmp_path)
    folder = store_capture(paths, _by_hand(f"my key is {SECRET}"), _redactor())
    text = (folder / "capture.json").read_text(encoding="utf-8")
    assert SECRET not in text and "[REDACTED]:KEY" in text


def test_an_encoded_secret_withholds_the_capture_and_writes_nothing(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = ProjectPaths("demo", tmp_path)
    redactor = _redactor()
    monkeypatch.setattr(redactor, "scrub_obj", lambda obj: obj)  # a spelling scrub misses
    with pytest.raises(CaptureWithheld):
        store_capture(paths, _by_hand(f"key {SECRET}"), redactor)
    assert not paths.ai_dir.exists()


def test_a_capture_for_another_project_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="project"):
        store_capture(ProjectPaths("other", tmp_path), _by_hand(), _redactor())


def test_a_failed_write_leaves_no_partial_file(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = ProjectPaths("demo", tmp_path)

    def boom(src: object, dst: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        store_capture(paths, _by_hand(), _redactor())
    assert [p for p in paths.ai_dir.rglob("*") if p.is_file()] == []


def test_judge_capture_with_paths_persists_the_capture_and_the_verdict(tmp_path: Path) -> None:
    paths = ProjectPaths("demo", tmp_path)
    cap = _by_hand('{"answer": "x"}')
    verdict = judge_capture(cap, run_id="r1", judge=MockProvider(), redactor=_redactor(),
                            paths=paths)
    folder = _folder(paths, cap)
    assert read_json(folder / "verdict.json", Verdict) == verdict
    assert read_json(folder / "capture.json", AiCapture) is not None


def test_judge_capture_without_paths_writes_nothing(tmp_path: Path) -> None:
    judge_capture(_by_hand(), run_id="r1", judge=MockProvider(), redactor=_redactor())
    assert list(tmp_path.iterdir()) == []


def test_a_secret_in_a_judge_reason_never_reaches_verdict_json(tmp_path: Path) -> None:
    paths = ProjectPaths("demo", tmp_path)
    cap = _by_hand("Lyon", AiCheckKind.GROUND_TRUTH_ANSWER)
    bad = Judgment(result=Result.FAIL, criteria_met=1, criteria_total=2, failures=[Failure(
        criterion_id="AI-GT1", reason=f"wrong; leaked {SECRET}",
        evidence_refs=["[network] response[0]"])])
    judge_capture(cap, run_id="r1", judge=MockProvider(responses={"judge": [bad]}),
                  redactor=_redactor(), reference="Paris", paths=paths)
    for name in ("capture.json", "verdict.json"):
        assert SECRET not in (_folder(paths, cap) / name).read_text(encoding="utf-8")


def test_capture_judge_store_report_round_trip(tmp_path: Path) -> None:
    store = ProjectStore("demo", tmp_path)
    cap = capture_run(
        project=project_of("demo"), endpoint=URL, check=AiCheckKind.RESPONSE_SHAPE,
        prompts=["hi"], send=lambda u, p: AiReply(status=200, text='{"answer": "Paris"}'),
        approvals=[_approval()], redactor=_redactor(), expected_keys=["answer"], now=NOW)
    judge_capture(cap, run_id="r1", judge=MockProvider(), redactor=_redactor(), paths=store.paths)
    out = export_ai_report(store, checks=[], redactor=_redactor())
    assert out == store.paths.ai_dir / "ai-report.xlsx"
    ws = load_workbook(out)["static"]
    statuses = [row[3] for row in ws.iter_rows(values_only=True)]
    assert "PASS" in statuses and "CAPTURED, NOT JUDGED" not in statuses


