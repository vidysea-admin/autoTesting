"""L10 known-disputed historical claims K1/K2 (D-069) and the informational doctor rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from seal_fixtures import block, row, sha, tree, write
from seal_fixtures import blocking as blocking_of

from autotester import doctor
from autotester.ledger import citations, seals

K_LOG_K1 = ("**What:** so D-005 stays as written; authorized by D-000 `Changes-authorized`: "
            "`scripts/append_decision.ps1`\n")


def _known(monkeypatch: pytest.MonkeyPatch, text: str, cid: str, label: str) -> None:
    key = ("docs/DECISIONS.md", cid, 1)
    monkeypatch.setattr(seals, "KNOWN_DISPUTED", {key: (label, sha(text.rstrip("\n")))})


def _claim_row(text: str, cid: str) -> dict:
    return dict(path="docs/DECISIONS.md", line_text=text.rstrip("\n"), id=cid, ordinal=1,
                multiplicity=1, kind="authorization-claim", reason="historical claim",
                reviewer="Oracle Reviewer", review_ref="qa/review.md")


def test_known_disputed_claims_are_listed_counted_and_non_blocking(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tree(tmp_path, {"docs/DECISIONS.md": K_LOG_K1})
    write(root, "qa/review.md", "Attribution: Oracle Reviewer\n")
    _known(monkeypatch, K_LOG_K1, "D-000", "K1")
    rows = [_claim_row(K_LOG_K1, "D-000"),
            dict(_claim_row(K_LOG_K1, "D-005"), kind="ordinary-reference")]
    block(root, rows)
    found = citations.check_citation_subjects(root)
    assert doctor.blocking(found) == []
    assert [(v.rule, v.location, "K1" in v.detail) for v in found] == [
        ("decision-citation-known-disputed", "docs/DECISIONS.md:1", True)]


def test_editing_a_known_disputed_line_turns_doctor_red(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tree(tmp_path, {"docs/DECISIONS.md": K_LOG_K1})
    write(root, "qa/review.md", "Attribution: Oracle Reviewer\n")
    _known(monkeypatch, K_LOG_K1, "D-000", "K1")
    edited = K_LOG_K1.replace("stays", "stayed")
    write(root, "docs/DECISIONS.md", edited)
    block(root, [_claim_row(edited, "D-000"), dict(_claim_row(edited, "D-005"),
                                                    kind="ordinary-reference")])
    assert [v.rule for v in blocking_of(root)] == ["decision-citation-declaration"]


def test_a_third_disputed_occurrence_is_blocking(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    other = "D-007 authorizes more\n"
    root = tree(tmp_path, {"docs/DECISIONS.md": K_LOG_K1 + other})
    write(root, "qa/review.md", "Attribution: Oracle Reviewer\n")
    _known(monkeypatch, K_LOG_K1, "D-000", "K1")
    rows = [_claim_row(K_LOG_K1, "D-000"), dict(_claim_row(K_LOG_K1, "D-005"),
                                                kind="ordinary-reference"),
            _claim_row(other, "D-007")]
    block(root, rows)
    assert [(v.rule, v.location) for v in blocking_of(root)] == [
        ("decision-citation-declaration", "docs/DECISIONS.md:2")]


def test_a_seal_naming_a_known_disputed_line_is_rejected(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log = "## D-006 | 2026-09-01 | type: fix | status: ACTIVE\n" + K_LOG_K1
    root = tree(tmp_path, {"docs/DECISIONS.md": log})
    monkeypatch.setattr(seals, "KNOWN_DISPUTED", {
        ("docs/DECISIONS.md", "D-000", 1): ("K1", sha(K_LOG_K1.rstrip("\n")))})
    block(root, [row(root, "docs/DECISIONS.md", scope="entry:D-006", sha256=sha(log))])
    assert any("known-disputed" in v.detail and v.rule == "decision-citation-coverage"
               for v in blocking_of(root))


def test_the_real_known_disputed_table_matches_the_two_recorded_lines() -> None:
    from autotester.core.paths import repo_root
    lines = (repo_root() / "docs/DECISIONS.md").read_text(encoding="utf-8").split("\n")
    found = {key: label for key, (label, digest) in seals.KNOWN_DISPUTED.items()
             if any(sha(line) == digest for line in lines)}
    assert found == {("docs/DECISIONS.md", "D-000", 1): "K1",
                     ("docs/DECISIONS.md", "D-005", 1): "K2"}


def test_cli_doctor_exits_zero_when_only_informational_rows_remain(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from autotester import cli
    soft = [doctor.Violation("decision-citation-sealed", "x", "3 occurrences")]
    monkeypatch.setattr(doctor, "run", lambda *_a: soft)
    done = CliRunner().invoke(cli.app, ["doctor"])
    assert done.exit_code == 0 and "decision-citation-sealed" in done.output
    monkeypatch.setattr(doctor, "run", lambda *_a: [*soft, doctor.Violation("r", "y", "d")])
    assert CliRunner().invoke(cli.app, ["doctor"]).exit_code == 1


def test_doctor_blocking_ignores_only_the_informational_and_advisory_rules() -> None:
    soft = [doctor.Violation("decision-citation-sealed", "x", "n"),
            doctor.Violation("decision-citation-known-disputed", "x", "n")]
    hard = doctor.Violation("decision-citation-subject-mismatch", "x", "n")
    assert doctor.blocking([*soft, hard]) == [hard]
    assert doctor.blocking(soft) == []
