"""AT-712: close-out back-reference -- open rows and qa/gates files that name a changed path."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester.cli import app
from autotester.ledger import store

FIX = ["src/autotester/stages/run_budget.py", "src/autotester/stages/parallel_run.py"]


def issue(id_: str, status: str, title: str = "t", evidence: str = "e") -> dict:
    return {"id": id_, "status": status, "title": title, "evidence": evidence}


def stale_rows() -> list[dict]:
    """AT-660/CN10 shape: a verified fix, then three open rows resting on the old reading."""
    return [
        issue("AT-660", "verified", evidence="stages/run_budget.py::try_consume returns False"),
        issue("AT-675", "open", title="UI grant cannot bound probes",
              evidence="parallel_run.py:164 holds the falsy guard so 0 means unbounded"),
        issue("AT-683", "open", evidence="`stages/run_budget.py::try_consume` treats 0 as no cap"),
        issue("AT-661", "open", title="0 is unlimited in src/autotester/stages/run_budget.py"),
        issue("AT-701", "wontfix", evidence="stages/run_budget.py (retired design)"),
        issue("AT-700", "open", evidence="core/consent.py::_shortfalls compares plainly"),
    ]


def joined(lines: list[str]) -> str:
    return "\n".join(lines)


def test_a_run_budget_fix_lists_the_three_stale_rows_and_the_gate_that_cites_them() -> None:
    gates = {
        "qa/gates/at674-approval-key.md": "# gate\n\nno UI grant can BOUND probes:\n"
        "see stages/run_budget.py::try_consume\n",
        "qa/gates/unrelated.md": "# gate\n\ncore/consent.py only\n",
    }
    out = joined(store.backref_candidates(FIX, stale_rows(), gates, exclude="AT-660"))
    for stale in ("AT-675", "AT-683", "AT-661"):
        assert stale in out
    assert "qa/gates/at674-approval-key.md:4" in out
    for quiet in ("AT-660", "AT-700", "AT-701", "unrelated.md"):
        assert quiet not in out


def test_a_basename_only_citation_is_listed_but_marked_weak() -> None:
    out = store.backref_candidates(FIX, stale_rows(), {}, exclude="AT-660")
    weak = next(line for line in out if line.startswith("AT-675"))
    strong = next(line for line in out if line.startswith("AT-683"))
    assert "basename only" in weak
    assert "basename only" not in strong


def test_only_open_rows_are_candidates_and_the_closing_row_is_excluded() -> None:
    rows = [issue("AT-1", "fixed", title="stages/run_budget.py"),
            issue("AT-2", "open", title="stages/run_budget.py"),
            issue("AT-3", "open", title="stages/run_budget.py")]
    out = joined(store.backref_candidates(FIX, rows, {}, exclude="AT-3"))
    assert "AT-2" in out and "AT-1" not in out and "AT-3" not in out


def test_a_name_that_merely_ends_like_the_path_is_not_a_hit() -> None:
    rows = [issue("AT-1", "open", evidence="filestore.py and not_run_budget.py.bak")]
    assert store.backref_candidates(["src/autotester/store/store.py"], rows, {}) == []
    assert store.backref_candidates(FIX, rows, {}) == []


def test_ledger_bookkeeping_paths_in_the_fix_do_not_flood_the_report() -> None:
    rows = [issue("AT-1", "open", evidence="qa/issues.jsonl row 40 and qa/manifests/x.md")]
    changed = ["qa/issues.jsonl", "qa/manifests/x.md", "qa/verdicts/x.md", "docs/FEATURES.jsonl"]
    assert store.backref_candidates(changed, rows, {}) == []


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                          text=True).stdout


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.invalid")
    git(tmp_path, "config", "user.name", "t")
    budget = tmp_path / "src" / "autotester" / "stages"
    budget.mkdir(parents=True)
    (budget / "run_budget.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "qa" / "gates").mkdir(parents=True)
    (tmp_path / "qa" / "issues.jsonl").write_text(
        "\n".join(json.dumps(r) for r in stale_rows()) + "\nnot json\n", encoding="utf-8")
    (tmp_path / "qa" / "gates" / "g.md").write_text("see stages/run_budget.py\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    (budget / "run_budget.py").write_text("x = 2\n", encoding="utf-8")
    git(tmp_path, "commit", "-q", "-am", "fix")
    return tmp_path


def test_changed_paths_reads_the_files_the_closing_commit_touched(repo: Path) -> None:
    assert store.changed_paths(repo, "HEAD") == ["src/autotester/stages/run_budget.py"]


def test_the_report_never_edits_the_ledger_or_the_gates(repo: Path) -> None:
    watched = [repo / "qa" / "issues.jsonl", repo / "qa" / "gates" / "g.md"]
    before = [p.read_bytes() for p in watched]
    out = joined(store.backref_report(repo, "HEAD", exclude="AT-660"))
    assert "AT-683" in out and "qa/gates/g.md:1" in out
    assert "qa/issues.jsonl:7 unreadable" in out
    assert [p.read_bytes() for p in watched] == before


def test_the_command_prints_candidates_and_exits_zero(repo: Path) -> None:
    result = CliRunner().invoke(app, ["ledger-backref", "HEAD", "--exclude", "AT-660"])
    assert result.exit_code == 0, result.output
    assert "AT-661" in result.output and "qa/gates/g.md:1" in result.output


def test_the_command_says_so_when_nothing_cites_the_fix(repo: Path) -> None:
    (repo / "qa" / "issues.jsonl").write_text("", encoding="utf-8")
    (repo / "qa" / "gates" / "g.md").write_text("nothing\n", encoding="utf-8")
    result = CliRunner().invoke(app, ["ledger-backref", "HEAD"])
    assert result.exit_code == 0 and "no open row or gate" in result.output
