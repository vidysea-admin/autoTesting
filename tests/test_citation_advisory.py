"""D-087 item 3: coverage and declaration findings are advisory, wrong subjects still block."""

from __future__ import annotations

import pytest
from seal_fixtures import tree
from typer.testing import CliRunner

from autotester import cli, doctor

LOG = ("## D-001 | 2026-09-01 | type: decision | status: ACTIVE\n"
       "**What:** real subject text\n")


def _fake(monkeypatch: pytest.MonkeyPatch, rules: list[str], count: int = 1) -> None:
    rows = [doctor.Violation(rule, f"f.md:{n}", "x") for rule in rules for n in range(count)]
    monkeypatch.setattr(doctor, "run", lambda *_a: rows)


def test_coverage_and_declaration_findings_do_not_fail_doctor(
        monkeypatch: pytest.MonkeyPatch) -> None:
    _fake(monkeypatch, ["decision-citation-coverage", "decision-citation-declaration"])
    done = CliRunner().invoke(cli.app, ["doctor"])
    assert done.exit_code == 0 and "doctor: clean" in done.output


@pytest.mark.parametrize("rule", ["decision-citation-subject-mismatch",
                                  "decision-citation-subject-unavailable"])
def test_a_wrong_subject_or_dangling_citation_fails_doctor(
        monkeypatch: pytest.MonkeyPatch, rule: str) -> None:
    _fake(monkeypatch, ["decision-citation-coverage", rule])
    done = CliRunner().invoke(cli.app, ["doctor"])
    assert done.exit_code == 1 and rule in done.output


def test_the_warning_summary_shows_counts_and_only_the_first_items(
        monkeypatch: pytest.MonkeyPatch) -> None:
    _fake(monkeypatch, ["decision-citation-coverage"], count=40)
    out = CliRunner().invoke(cli.app, ["doctor"]).output
    assert "decision-citation-coverage: 40 advisory finding(s) (D-087" in out
    assert "... and 35 more" in out and out.count("f.md:") == 5


def test_real_scan_reports_missing_review_coverage_as_a_non_blocking_warning(
        tmp_path) -> None:
    root = tree(tmp_path, {"qa/manifests/m.md": "# M\nauthorized by D-001\n"})
    (root / "docs" / "DECISIONS.md").write_text(LOG, encoding="utf-8")
    found = doctor.run(root)
    assert any(v.rule == "decision-citation-coverage" for v in found)
    assert not any(v.rule == "decision-citation-coverage" for v in doctor.blocking(found))
    assert doctor.warning_summary(found)
