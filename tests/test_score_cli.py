"""The scorer's exit code and its coverage report — T-136.

Separate from `test_score.py` because it answers a different question. That file
asks *is the matching right*; this one asks *can this command fail*, which is the
question T-136's `done_check` rests on.

A scorer that compares an empty issue list to seven truth rows, prints
`recall: 0.0` and exits 0 is AT-100's class — a check that cannot fail — pointed
at the north star's own metric. Today there are no derived issues (no vision
provider is configured), so that is not a hypothetical: it is what the command
does right now, and the exit code is the only thing separating "measured zero"
from "did not measure".

Contract: qa/contracts/video-learning.md (T-136 acceptance).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

from autotester.schema.analysis import VideoAnalysis
from autotester.schema.enums import IssueCategory, Severity, SourceKind
from autotester.schema.issue import Issue
from autotester.schema.project import Project, Source
from autotester.store.project_store import ProjectStore

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "score_video_issues.py"
CLIP = "erp1.mp4 (Divya Kamboj, trainer pipeline)"


def a_truth_sheet(path: Path, rows: int = 2) -> Path:
    book = Workbook()
    sheet = book.active
    sheet.title = "Trainer module"
    sheet.append(["ID", "Severity", "Type", "Title", "What is wrong", "How we know",
                  "Confirm first", "Said verbatim", "Clip", "At", "Screenshot shows", "Evidence"])
    for n in range(rows):
        sheet.append([f"E-{n:02d}", "High", "Blocker", f"Fault number {n}",
                      f"what is wrong with fault {n}", "spoken", None, None,
                      CLIP, f"00:{29 + n:02d}", None, None])
    book.save(path)
    return path


def a_project(root: Path, *, issues: int = 0, used: int = 4, expected: int = 4) -> ProjectStore:
    store = ProjectStore("erp", root)
    store.save_project(Project(slug="erp", name="ERP", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    source = store.add_source(Source(project="erp", kind=SourceKind.VIDEO,
                                     path=str(root / "erp1.mp4"), sha256="d", label=CLIP))
    for n in range(issues):
        # Deliberately NOT byte-identical to the truth row: a few seconds late and
        # worded differently, which is what a model actually produces. My first
        # fixture matched the sheet exactly, so tightening --window or --threshold
        # changed nothing and the C9 test below failed against a perfect fixture
        # rather than against the code.
        store.add_issue(Issue(project="erp", source_id=source.id, recording_label=CLIP,
                              at_s=32.0 + n, screen="Trainers",
                              title=f"Fault number {n} on the trainer drawer",
                              what_is_wrong=f"the thing that is wrong with fault {n}, roughly",
                              severity=Severity.S1, category=IssueCategory.FEATURE_GAP))
    store.save_analysis(VideoAnalysis(source_id=source.id, observations_used=used,
                                      observations_expected=expected))
    return store


def run(truth: Path, root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project", "erp", "--truth", str(truth),
         "--sheet", "Trainer module", "--root", str(root), *extra],
        capture_output=True, text=True, timeout=180)


def run_json(truth: Path, root: Path, *extra: str) -> dict:
    """AT-580: a child that crashed or was starved used to surface as a bare
    JSONDecodeError on empty stdout. Assert the exit code first and carry stderr
    into the failure, so the real cause is on screen."""
    result = run(truth, root, *extra)
    assert result.returncode == 0, (
        f"score CLI exited {result.returncode}; "
        f"stderr: {result.stderr!r}; stdout: {result.stdout!r}")
    return json.loads(result.stdout)


# -- the exit code is the whole point ----------------------------------------

def test_nothing_to_score_exits_NONZERO_and_names_the_command_that_fixes_it(
    tmp_path: Path,
) -> None:
    """The state this repo is in today: no vision provider, so no analysis, so no
    issues. Exiting 0 here with `recall: 0.0` would make T-136's done_check a
    check that cannot fail — and would report "we found none of the 7" when the
    truth is "we never looked"."""
    truth = a_truth_sheet(tmp_path / "truth.xlsx")
    a_project(tmp_path, issues=0)

    result = run(truth, tmp_path)

    assert result.returncode == 2, result.stdout
    assert "nothing to score" in result.stderr
    assert "issues derive" in result.stderr, "the refusal must name the command that fixes it"


def test_a_real_comparison_exits_zero_and_prints_json(tmp_path: Path) -> None:
    """The other half — a guard that always refuses guards nothing."""
    truth = a_truth_sheet(tmp_path / "truth.xlsx", rows=2)
    a_project(tmp_path, issues=2)

    result = run(truth, tmp_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["truth_rows"] == 2
    assert report["found"] == 2
    assert report["recall"] == 1.0


def test_an_unreadable_sheet_exits_nonzero_rather_than_scoring_zero(tmp_path: Path) -> None:
    a_project(tmp_path, issues=1)

    result = run(tmp_path / "does-not-exist.xlsx", tmp_path)

    assert result.returncode == 2
    assert "truth sheet" in result.stderr


# -- AT-207: the coverage numbers finally reach a reader ----------------------

def test_a_partial_analysis_is_reported_beside_the_recall(tmp_path: Path) -> None:
    """AT-207. `observations_used`/`observations_expected` have travelled with
    every analysis since T-133 and were read by nothing. A recall computed from
    1 of 12 model calls is not a measurement of this pipeline, and it looks
    identical to one computed from 12 of 12."""
    truth = a_truth_sheet(tmp_path / "truth.xlsx", rows=2)
    a_project(tmp_path, issues=2, used=1, expected=12)

    report = run_json(truth, tmp_path)

    assert report["coverage"]["complete"] is False
    assert report["coverage"]["observations_used"] == 1
    assert report["coverage"]["observations_expected"] == 12
    assert report["coverage"]["partial_sources"], "the partial source must be named"


def test_a_complete_analysis_says_so(tmp_path: Path) -> None:
    truth = a_truth_sheet(tmp_path / "truth.xlsx", rows=2)
    a_project(tmp_path, issues=2, used=12, expected=12)

    report = run_json(truth, tmp_path)

    assert report["coverage"]["complete"] is True
    assert report["coverage"]["partial_sources"] == []


def test_the_SHIPPED_command_resolves_the_repo_root_not_the_drive(tmp_path: Path) -> None:
    r"""AT-219. The default root read `ProjectPaths(...).root.parent.parent`, but
    `.root` IS the repo root -- so the shipped command looked in the drive root and
    refused for the wrong reason, while every test passed `--root` and never
    executed that branch. T-136's done_check passes no `--root`, so the task was
    structurally incapable of closing even once a credential arrived.

    Driven WITHOUT `--root`, under AUTOTESTER_ROOT, which is how the shipped
    command resolves a project."""
    truth = a_truth_sheet(tmp_path / "truth.xlsx", rows=2)
    a_project(tmp_path, issues=2)
    env = {**os.environ, "AUTOTESTER_ROOT": str(tmp_path), "PYTHONUTF8": "1"}

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--project", "erp", "--truth", str(truth),
         "--sheet", "Trainer module"], capture_output=True, text=True, env=env)

    assert result.returncode == 0, f"the shipped path did not find the project: {result.stderr}"
    assert json.loads(result.stdout)["found"] == 2


def test_a_source_with_no_analysis_is_not_reported_as_complete(tmp_path: Path) -> None:
    """AT-222. `if analysis is None: continue` made `complete: true` reachable
    while one contributing source had no analysis at all -- the same flattering
    default AT-208 removed, reintroduced one layer up."""
    truth = a_truth_sheet(tmp_path / "truth.xlsx", rows=2)
    store = a_project(tmp_path, issues=2, used=4, expected=4)
    orphan = store.add_source(Source(project="erp", kind=SourceKind.VIDEO,
                                     path=str(tmp_path / "erp2.mp4"), sha256="d2",
                                     label="erp2.mp4"))
    store.add_issue(Issue(project="erp", source_id=orphan.id, recording_label="erp2.mp4",
                          at_s=5.0, screen="Other", title="unanalysed finding",
                          what_is_wrong="from a source with no analysis",
                          severity=Severity.S2, category=IssueCategory.FEATURE_GAP))

    report = run_json(truth, tmp_path)

    assert report["coverage"]["complete"] is False
    assert orphan.id in report["coverage"]["sources_with_no_analysis"]


@pytest.mark.parametrize("flag,value", [("--window", "0.5"), ("--threshold", "0.99")])
def test_the_declared_bounds_are_honoured_not_ignored(tmp_path: Path, flag, value) -> None:
    """C9: a declared control value is honoured or rejected, never silently
    ignored. Both knobs are tightened past what the fixture can satisfy, so a
    match surviving means the flag was dropped on the floor."""
    truth = a_truth_sheet(tmp_path / "truth.xlsx", rows=2)
    a_project(tmp_path, issues=2)

    loose = run_json(truth, tmp_path)
    tight = run_json(truth, tmp_path, flag, value)

    assert loose["found"] == 2, "the fixture must match under the defaults"
    assert tight["found"] < loose["found"], f"{flag}={value} changed nothing"


def test_a_failing_child_is_reported_with_its_stderr_not_as_a_json_error(tmp_path: Path) -> None:
    """AT-580: run_json must name the child's exit code and stderr, never hide a
    crash behind `json.loads('')`."""
    truth = tmp_path / "truth.xlsx"
    with pytest.raises(AssertionError, match=r"score CLI exited [1-9]"):
        run_json(truth, tmp_path, "--no-such-flag")
