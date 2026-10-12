"""Contract: qa/contracts/report-export.md RE1-RE5."""

from __future__ import annotations

import base64
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from openpyxl import load_workbook
from symlink_support import link_dir, link_file

from autotester.schema.case import Case
from autotester.schema.enums import (
    Action,
    CaseClass,
    CaseKind,
    EvidenceKind,
    Outcome,
    Result,
)
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import Evidence, RawResult, Run
from autotester.schema.verdict import Verdict
from autotester.stages import report_export
from autotester.store import ProjectStore

RUN_ID = "run-test123"
PNG_BYTES = base64.b64decode(  # a real, tiny, valid 1x1 PNG
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _seed(tmp_path: Path, *, outcome: Outcome, result: Result) -> ProjectStore:
    store = ProjectStore("demo", tmp_path)
    store.save_project(
        Project(slug="demo", name="Demo", base_url="https://demo.test",
                allowed_domains=["demo.test"])
    )
    case = Case(
        project="demo", flow_id="flow-login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Login works",
        steps=[Step(order=1, action=Action.NAVIGATE, target="/login")],
    )
    store.add_case(case)
    store.save_run(Run(id=RUN_ID, project="demo", case_ids=[case.id]))
    run_dir = store.paths.run_dir(RUN_ID)
    (run_dir / "01-step01-navigate.png").write_bytes(PNG_BYTES)
    raw = RawResult(
        case_id=case.id, outcome=outcome, duration_s=1.23,
        error=None if outcome is Outcome.COMPLETED else "TimeoutError: boom",
        evidence=[Evidence(kind=EvidenceKind.SCREENSHOT, path="01-step01-navigate.png",
                            step_order=1, label="step01-navigate")],
    )
    store.save_result(RUN_ID, raw)
    store.save_verdict(RUN_ID, Verdict(
        run_id=RUN_ID, case_id=case.id, result=result, criteria_met=1, criteria_total=1,
        scoreboard="Criteria 1/1 met.", grader_provider="gemini",
    ))
    return store


def test_export_excel_has_one_row_per_case(tmp_path: Path) -> None:
    _seed(tmp_path, outcome=Outcome.COMPLETED, result=Result.PASS)

    out = report_export.export_excel("demo", RUN_ID, tmp_path / "out.xlsx", tmp_path)

    wb = load_workbook(out)
    rows = list(wb.active.iter_rows(values_only=True))
    assert rows[0][0] == "Case"
    assert rows[1][0] == "Login works"
    assert rows[1][4] == "PASS"  # Result column


def test_export_excel_defaults_to_the_latest_run(tmp_path: Path) -> None:
    store = _seed(tmp_path, outcome=Outcome.COMPLETED, result=Result.PASS)
    (store.paths.runs_dir / "zzz-crawl-artifacts").mkdir()

    out = report_export.export_excel("demo", None, tmp_path / "out.xlsx", tmp_path)

    wb = load_workbook(out)
    rows = list(wb.active.iter_rows(values_only=True))
    assert rows[1][0] == "Login works"


def test_valid_runs_exclude_directories_without_a_valid_envelope(tmp_path: Path) -> None:
    store = _seed(tmp_path, outcome=Outcome.COMPLETED, result=Result.PASS)
    (store.paths.runs_dir / "crawl-latest").mkdir()
    malformed = store.paths.runs_dir / "run-malformed"
    malformed.mkdir()
    (malformed / "run.json").write_text("not json", encoding="utf-8")
    wrong = store.paths.runs_dir / "run-wrong-project"
    wrong.mkdir()
    (wrong / "run.json").write_text(
        Run(id=wrong.name, project="other").model_dump_json(), encoding="utf-8"
    )

    assert [run.id for run in report_export.valid_runs_newest_first(store)] == [RUN_ID]


def test_valid_runs_order_by_envelope_time_not_directory_name(tmp_path: Path) -> None:
    store = _seed(tmp_path, outcome=Outcome.COMPLETED, result=Result.PASS)
    first = store.load_run(RUN_ID)
    assert first is not None
    naive_newer = (first.created_at + timedelta(seconds=1)).replace(tzinfo=None)
    store.save_run(Run(id="aaa-newer", project="demo", created_at=naive_newer))

    assert [run.id for run in report_export.valid_runs_newest_first(store)] == ["aaa-newer", RUN_ID]


def test_png_embedding_refuses_paths_outside_the_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("must-not-leak", encoding="utf-8")

    assert report_export.png_base64(outside, run_dir, tmp_path) is None
    assert report_export.png_base64(run_dir / ".." / outside.name, run_dir, tmp_path) is None


def test_png_embedding_refuses_a_symlinked_allowed_directory(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.png").write_bytes(b"must-not-leak")
    allowed = tmp_path / "project" / "runs" / "run-1"
    allowed.parent.mkdir(parents=True)
    link_dir(allowed, outside)

    assert report_export.png_base64(allowed / "secret.png", allowed, tmp_path / "project") is None


def test_png_embedding_refuses_a_file_symlink(tmp_path: Path) -> None:
    allowed = tmp_path / "project" / "run"
    allowed.mkdir(parents=True)
    outside = tmp_path / "secret.png"
    outside.write_bytes(b"must-not-leak")
    link = allowed / "shot.png"
    link_file(link, outside)

    assert report_export.png_base64(link, allowed, tmp_path / "project") is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction regression")
def test_png_embedding_refuses_a_windows_junction(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.png").write_bytes(b"must-not-leak")
    allowed = tmp_path / "project" / "run"
    allowed.parent.mkdir()
    made = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(allowed), str(outside)], capture_output=True,
    )
    assert made.returncode == 0, made.stderr.decode(errors="replace")
    assert report_export.png_base64(allowed / "secret.png", allowed, tmp_path / "project") is None


def test_export_excel_raises_a_clear_error_with_no_runs(tmp_path: Path) -> None:
    ProjectStore("demo", tmp_path).save_project(
        Project(slug="demo", name="Demo", base_url="https://demo.test",
                allowed_domains=["demo.test"])
    )
    with pytest.raises(ValueError, match="no runs"):
        report_export.export_excel("demo", None, tmp_path / "out.xlsx", tmp_path)


def test_export_html_embeds_the_screenshot_and_is_self_contained(tmp_path: Path) -> None:
    _seed(tmp_path, outcome=Outcome.COMPLETED, result=Result.PASS)

    out = report_export.export_html("demo", RUN_ID, tmp_path / "out.html", tmp_path)

    html = out.read_text(encoding="utf-8")
    assert "Login works" in html
    assert "PASS" in html
    assert "data:image/png;base64," in html  # RE3: embedded, not a file reference
    assert "step01-navigate" in html


def test_export_html_shows_the_error_for_an_errored_case(tmp_path: Path) -> None:
    _seed(tmp_path, outcome=Outcome.ERRORED, result=Result.INCONCLUSIVE)

    out = report_export.export_html("demo", RUN_ID, tmp_path / "out.html", tmp_path)

    html = out.read_text(encoding="utf-8")
    assert "TimeoutError: boom" in html
    assert "INCONCLUSIVE" in html
