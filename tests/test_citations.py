"""L9 (AT-710): a cited `D-NNN` must resolve to an appended decision entry.
Every fixture is a shape that has occurred in this repo. Synthetic trees are built in
`tmp_path`; the last tests read the real tree so the check is judged against what exists.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from autotester import doctor
from autotester.core.paths import repo_root
from autotester.ledger import citations
from autotester.ledger.citations import appended_ids, check_decision_citations


def _repo(root: Path, log: str, files: dict[str, str] | None = None,
          archive: str = "") -> Path:
    (root / "docs" / "archive").mkdir(parents=True)
    (root / "docs" / "DECISIONS.md").write_text(log, encoding="utf-8")
    (root / "docs" / "archive" / "INDEX.md").write_text(archive, encoding="utf-8")
    for rel, body in (files or {}).items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    return root

LOG = "## D-001 | 2026-09-01 | type: decision | status: ACTIVE\n**What:** x\n"

def test_a_dangling_id_fires_naming_file_line_and_id(tmp_path: Path) -> None:
    _repo(tmp_path, LOG, {"qa/gates/g.md": "ok D-001\nauthorized by D-056 here\n"})
    found = check_decision_citations(tmp_path)
    assert [(v.location, "D-056" in v.detail) for v in found] == [("qa/gates/g.md:2", True)]

def test_a_resolving_id_is_clean(tmp_path: Path) -> None:
    _repo(tmp_path, LOG, {"qa/manifests/m.md": "Links: D-001\n"})
    assert check_decision_citations(tmp_path) == []

def test_an_archived_entry_resolves(tmp_path: Path) -> None:
    """Archiving is not deletion: an id living only in docs/archive/ still resolves."""
    _repo(tmp_path, LOG, {"qa/gates/g.md": "see D-014\n"},
          archive="D-014 | 2026-07-10 | experiment | REJECTED | x | DECISIONS-2026-Q3.md\n")
    assert "D-014" in appended_ids(tmp_path)
    assert check_decision_citations(tmp_path) == []

def test_matching_is_by_header_not_by_substring(tmp_path: Path) -> None:
    """A mention of `D-056` inside another entry's body is not a `## D-056` header."""
    _repo(tmp_path, LOG + "Body says D-056 did not exist.\n",
          {"qa/gates/g.md": "cites D-056\n"})
    assert "D-056" not in appended_ids(tmp_path)
    found = [v.location for v in check_decision_citations(tmp_path)]
    assert found.count("qa/gates/g.md:1") == 1

def test_the_citation_pattern_is_word_bounded(tmp_path: Path) -> None:
    """SD-3, MD-3 and ID-040 are real strings in this repo and are not citations."""
    _repo(tmp_path, LOG, {"docs/x.md": "SD-3 MD-3 ID-040\nD-001/D-002/D-003\n"})
    assert sorted(v.detail.split()[1].rstrip(",") for v in check_decision_citations(tmp_path)) == [
        "D-002", "D-003"]

def test_only_the_five_named_globs_are_citation_sources(tmp_path: Path) -> None:
    _repo(tmp_path, LOG, {"qa/feedback-inbox.md": "D-777\n", "docs/research/r.md": "D-777\n"})
    assert check_decision_citations(tmp_path) == []

def test_a_foreign_id_is_exempt_across_its_whole_entry_only(tmp_path: Path) -> None:
    """The real shape: D-088 in prose on one line, qualified by a log path on another."""
    log = (LOG + "## D-002 | 2026-09-02 | type: decision | status: ACTIVE\n"
           "prose about D-088 failure\n**Links:** D-088, `D:/ai_os/umesh/decisions/log.md`\n"
           "## D-003 | 2026-09-03 | type: decision | status: ACTIVE\nunqualified D-088\n")
    found = check_decision_citations(_repo(tmp_path, log))
    assert [v.location for v in found] == ["docs/DECISIONS.md:7"]

def test_a_non_claiming_row_is_per_occurrence_never_per_file(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(citations.NON_CLAIMING,
                        ("qa/contracts/c.md", "did not exist", "D-056"), "self-reference")
    _repo(tmp_path, LOG, {"qa/contracts/c.md": "D-056 did not exist\nreal claim D-056\n"
                          "D-057 did not exist\n", "qa/gates/g.md": "D-056 did not exist\n"})
    assert sorted(v.location for v in check_decision_citations(tmp_path)) == [
        "qa/contracts/c.md:2", "qa/contracts/c.md:3", "qa/gates/g.md:1"]

@pytest.mark.parametrize("resolving", [False, True])
def test_seven_citations_of_an_unwritten_entry_all_fire(tmp_path: Path, resolving: bool) -> None:
    """Fixture (c): the precondition (the id is unwritten) is asserted, not assumed."""
    gate = "\n".join(f"line {n} authorized by D-0{57 + 900}" for n in range(7)) + "\n"
    _repo(tmp_path, LOG, {"qa/gates/at654.md": gate})
    assert "D-957" not in appended_ids(tmp_path)
    assert len(check_decision_citations(tmp_path)) == 7
    if resolving:
        line = _claim("wrong")
        (tmp_path / "qa/gates/at654.md").write_text((line + "\n") * 7, encoding="utf-8")
        assert "D-001" in appended_ids(tmp_path)
        assert check_decision_citations(tmp_path) == []
        _reviews(tmp_path, {line: "authorization-claim"})
        found = citations.check_citation_subjects(tmp_path)
        assert not any(v.rule == "decision-citation-coverage" for v in found)
        assert [(v.rule, v.location, "D-001" in v.detail) for v in found] == [
            ("decision-citation-subject-mismatch", f"qa/gates/at654.md:{n}", True)
            for n in range(1, 8)]

def test_doctor_run_includes_the_citation_check(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = doctor.Violation("decision-citation-dangling", "x:1", "wired")
    monkeypatch.setattr(citations, "check_decision_citations", lambda _root: [marker])
    assert marker in doctor.run(tmp_path)

def test_the_real_tree_has_no_dangling_citation() -> None:
    """The live tree: every declared exemption still matches a real line, and nothing else fires."""
    root = repo_root()
    assert check_decision_citations(root) == []
    assert {"D-055", "D-056", "D-057", "D-058"} <= appended_ids(root)

def test_empty_log_still_reports_dangling_citations(tmp_path: Path) -> None:
    _repo(tmp_path, "", {"qa/gates/g.md": "authorized by D-056\n"})
    assert [v.location for v in check_decision_citations(tmp_path)] == ["qa/gates/g.md:1"]

def test_l10_missing_inventory_cannot_green_a_resolving_claim(tmp_path: Path) -> None:
    _repo(tmp_path, LOG, {"qa/gates/g.md": "authorized by D-001\n"})
    found = citations.check_citation_subjects(tmp_path)
    assert any(v.rule == "decision-citation-coverage" and v.location == "qa/gates/g.md:1"
               and "D-001" in v.detail for v in found)
    line = _claim()
    (tmp_path / "qa/gates/g.md").write_text(line + "\n", encoding="utf-8")
    _reviews(tmp_path, {line: "authorization-claim"})
    assert citations.check_citation_subjects(tmp_path) == []
    (tmp_path / "qa/gates/g.md").write_text(line + "\nauthorized by D-001\n", encoding="utf-8")
    assert check_decision_citations(tmp_path) == []
    assert any(v.rule == "decision-citation-coverage" and v.location == "qa/gates/g.md:2"
               and "D-001" in v.detail for v in citations.check_citation_subjects(tmp_path))

def _claim(quote: str = "x", cid: str = "D-001") -> str:
    return (f"Decision claim {cid}: {json.dumps(quote)} <!-- decision-claim: "
            + json.dumps({"id": cid, "what": quote}) + " -->")

def _reviews(root: Path, kinds: dict[str, str] | None = None) -> list[dict]:
    rows = []
    for glob in citations.CITING_GLOBS:
        for path in root.glob(glob):
            lines = path.read_text(encoding="utf-8").splitlines()
            for line in dict.fromkeys(lines):
                visible = re.sub(r"<!--.*?(?:-->|$)", "", line)
                counts = {}
                for cid in re.findall(r"\bD-\d+\b", visible):
                    counts[cid] = counts.get(cid, 0) + 1
                    kind = (kinds or {}).get((line, cid),
                                            (kinds or {}).get(line, "ordinary-reference"))
                    if line.startswith("## D-"):
                        kind = "structural-header"
                    rows.append(dict(path=path.relative_to(root).as_posix(), line_text=line,
                                     id=cid, ordinal=counts[cid], multiplicity=lines.count(line),
                                     kind=kind, reason="Fixture independently specified",
                                     reviewer="Oracle Reviewer", review_ref="qa/review.md"))
    (root / "qa").mkdir(exist_ok=True)
    (root / "qa/review.md").write_text("Attribution: Oracle Reviewer\n", encoding="utf-8")
    _write_reviews(root, rows)
    return rows
def _write_reviews(root: Path, rows: list[dict], suffix: str = "") -> None:
    body = "<!-- BEGIN T196 CURRENT CITATION REVIEWS -->\n"
    body += "\n".join("<!-- citation-review: " + json.dumps(row) + " -->" for row in rows)
    body += "\n<!-- END T196 CURRENT CITATION REVIEWS -->\n" + suffix
    (root / "qa/feedback-inbox.md").write_text(body, encoding="utf-8")

@pytest.mark.parametrize(("log", "quote", "expected"), [
    (LOG, "x", None), (LOG.replace("x", "x  y"), "x\n y", None),
    (LOG, "X", "subject-mismatch"), (LOG, "x.", "subject-mismatch"),
    (LOG, "other", "subject-mismatch"),
    (LOG.replace("**What:** x", "**Why:** x"), "x", "subject-unavailable"),
    (LOG + "**Why:** wrong", "wrong", "subject-mismatch"),
    (LOG + "**What:** x", "x", "subject-unavailable"),
    (LOG + LOG, "x", "subject-unavailable"),
    (LOG.replace("x", "x D-002") + "## D-002 | other\n**What:** other", "x D-002", None),
    (LOG.replace("x", "first\n- **Why:** nested\ncontinued\n**Why:** outside"),
     "nested continued", None),
])
def test_l10_quote_uses_only_full_unambiguous_what(tmp_path, log, quote, expected):
    line = _claim(quote)
    _repo(tmp_path, log, {"qa/gates/g.md": line})
    _reviews(tmp_path, {line: "authorization-claim", (line, "D-002"): "ordinary-reference"})
    found = citations.check_citation_subjects(tmp_path)
    if expected is None:
        assert found == []
    else:
        assert any(v.rule == "decision-citation-" + expected
                   and v.location == "qa/gates/g.md:1" and "D-001" in v.detail for v in found)

@pytest.mark.parametrize("body", [
    _claim() + " extra permission", _claim() + _claim(),
    _claim() + '<!-- decision-claim: {"id":"D-002","what":"other"} -->',
    '<!-- decision-claim: {"id":"D-001","what":"x"} -->',
    _claim().replace('"what": "x"', '"what": "other"'),
    _claim().replace('"id": "D-001"', '"id": "D-002"'),
    _claim().replace('"what": "x"', '"what": "x", "what":"x"'),
    _claim().replace('"what": "x"', '"what": "x", "extra":true'),
    _claim().replace('"what": "x"', '"what": 1'),
    _claim(" "), 'Decision claim D-001: "x"', '<!-- decision-claim: garbage',
])
def test_l10_bad_declarations_fail_even_without_visible_ids(tmp_path, body):
    _repo(tmp_path, LOG, {"qa/gates/g.md": body})
    _reviews(tmp_path, {body: "authorization-claim"})
    assert any(v.rule == "decision-citation-declaration" and v.location == "qa/gates/g.md:1"
               for v in citations.check_citation_subjects(tmp_path))
    visible_ids = re.findall(r"\bD-\d+\b", re.sub(r"<!--.*?(?:-->|$)", "", body))
    assert all(any(v.rule == "decision-citation-declaration" and cid in v.detail
                   for v in citations.check_citation_subjects(tmp_path)) for cid in visible_ids)
    assert all(cid in next(v.detail for v in citations.check_citation_subjects(tmp_path)
                           if v.rule == "decision-citation-declaration") for cid in visible_ids)
@pytest.mark.parametrize("full", [True, False])
def test_l10_archive_body_required_not_index_summary(tmp_path, full):
    line = _claim("archived", "D-014")
    _repo(tmp_path, "", {"qa/gates/g.md": line}, archive="D-014 | archived\n")
    if full:
        (tmp_path / "docs/archive/old.md").write_text(
            "## D-014 | old\n**What:** archived\n", encoding="utf-8")
    _reviews(tmp_path, {line: "authorization-claim"})
    found = citations.check_citation_subjects(tmp_path)
    assert found == [] if full else any(v.rule == "decision-citation-subject-unavailable"
                                      and "D-014" in v.detail for v in found)
@pytest.mark.parametrize("change", ["missing", "text", "multiplicity", "duplicate", "kind",
                                   "ordinal", "extra", "type", "ref", "reviewer", "block",
                                   "negative", "blank", "path", "historical", "structural", "keys"])
def test_l10_inventory_is_current_strict_and_attributable(tmp_path, change):
    line = _claim()
    _repo(tmp_path, LOG, {"qa/gates/g.md": line})
    rows = _reviews(tmp_path, {line: "authorization-claim"})
    row = next(row for row in rows if row["path"] == "qa/gates/g.md")
    if change == "missing":
        rows.remove(row)
    elif change == "text":
        row["line_text"] += " changed"
    elif change == "multiplicity":
        (tmp_path / "qa/gates/g.md").write_text(line + "\n" + line, encoding="utf-8")
    elif change == "duplicate":
        rows.append(dict(row, kind="ordinary-reference"))
    elif change == "block":
        _write_reviews(tmp_path, rows, "<!-- BEGIN T196 CURRENT CITATION REVIEWS -->\n"
                       "<!-- END T196 CURRENT CITATION REVIEWS -->")
    else:
        key, value = {"kind": ("kind", "unknown"), "ordinal": ("ordinal", 2),
                      "extra": ("extra", 1), "type": ("multiplicity", True),
                      "ref": ("review_ref", "../outside.md"),
                      "reviewer": ("reviewer", "Unknown Reviewer"), "negative": ("ordinal", 0),
                      "blank": ("reason", " "), "path": ("path", "docs/nested/x.md"),
                      "historical": ("what", "x"),
                      "structural": ("kind", "structural-header"), "keys": ("id", "D-001")}[change]
        row[key] = value
    if change != "block":
        _write_reviews(tmp_path, rows)
    if change == "keys":
        p = tmp_path / "qa/feedback-inbox.md"
        p.write_text(p.read_text().replace('"ordinal": 1', '"ordinal": 1,"ordinal": 1', 1))
    assert any(v.rule == "decision-citation-coverage"
               for v in citations.check_citation_subjects(tmp_path))
def test_l10_exemptions_do_not_exempt_adjacent_claims_or_coverage(tmp_path, monkeypatch):
    foreign = "**Links:** foreign D-001 and D:/ai_os/decisions/log.md"
    foreign_claim = _claim("unrelated", "D-001")
    example = "example " + _claim("unrelated")
    bad = _claim("wrong")
    log = LOG + foreign + "\n" + foreign_claim + "\n"
    _repo(tmp_path, log, {"qa/gates/g.md": example + "\n" + bad})
    monkeypatch.setitem(citations.NON_CLAIMING,
                        ("qa/gates/g.md", example, "D-001"), "example")
    _reviews(tmp_path, {foreign: "foreign-entry", foreign_claim: "foreign-entry",
                        example: "nonclaiming", bad: "authorization-claim"})
    found = citations.check_citation_subjects(tmp_path)
    assert [v.location for v in found] == ["qa/gates/g.md:2"]
    (tmp_path / "qa/feedback-inbox.md").unlink()
    assert any(v.rule == "decision-citation-coverage"
               for v in citations.check_citation_subjects(tmp_path))
def test_l10_doctor_wiring_and_real_tree_pending_coverage(tmp_path, monkeypatch):
    marker = doctor.Violation("decision-citation-coverage", "x:1", "wired")
    monkeypatch.setattr(citations, "check_citation_subjects", lambda _root: [marker])
    assert marker in doctor.run(tmp_path)
    monkeypatch.undo()
    _repo(tmp_path, LOG, {"qa/gates/g.md": _claim()})
    assert check_decision_citations(tmp_path) == []
    found = [v for v in doctor.run(tmp_path) if v.rule == "decision-citation-coverage"]
    assert [(v.location, "D-001" in v.detail) for v in found] == [
        ("qa/gates/g.md:1", True), ("docs/DECISIONS.md:1", True)]
@pytest.mark.parametrize("quote", ["x", "wrong"])
def test_l10_immutable_history_uses_reviewed_quote_and_occurrence_ordinals(tmp_path, quote):
    line = "D-001 authorizes x; D-001 reference"
    _repo(tmp_path, LOG + line + "\n" + line)
    rows = _reviews(tmp_path)
    row = next(row for row in rows if row["line_text"] == line and row["ordinal"] == 1)
    row.update(kind="authorization-claim", what=quote)
    _write_reviews(tmp_path, rows)
    found = citations.check_citation_subjects(tmp_path)
    assert found == [] if quote == "x" else any(v.rule == "decision-citation-subject-mismatch"
                                              and v.location == "docs/DECISIONS.md:3"
                                              for v in found)
    expected = [] if quote == "x" else [
        ("decision-citation-subject-mismatch", f"docs/DECISIONS.md:{n}", True) for n in (3, 4)]
    assert [(v.rule, v.location, "D-001" in v.detail) for v in found] == expected
def test_l10_markers_cannot_manufacture_multiline_citations(tmp_path):
    _repo(tmp_path, "", {"qa/gates/g.md": '<!-- decision-claim:\n{"id":"D-999"}\n-->'})
    assert check_decision_citations(tmp_path) == []
    found = citations.check_citation_subjects(tmp_path)
    assert any(v.rule == "decision-citation-declaration" for v in found)
    assert not any(v.rule == "decision-citation-coverage" for v in found)
