"""L10 sealed-record disposition (T-196, gate answer B): coverage, invalidation, eligibility.
Synthetic git repos in `tmp_path`; the seal baseline is a real commit, never faked.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from seal_fixtures import LOG, MANIFEST, block, git, row, sha, tree, write
from seal_fixtures import blocking as blocking_of

from autotester.ledger import citations


def test_an_unchanged_eligible_sealed_manifest_is_clean_and_counted(tmp_path: Path) -> None:
    root = tree(tmp_path)
    block(root, [row(root, "qa/manifests/m.md")])
    found = citations.check_citation_subjects(root)
    assert blocking_of(root) == []
    assert [(v.rule, "1 occurrence" in v.detail) for v in found] == [
        ("decision-citation-sealed", True)]


def test_without_the_seal_the_same_occurrence_is_uncovered(tmp_path: Path) -> None:
    root = tree(tmp_path)
    block(root, [])
    assert [v.location for v in blocking_of(root)] == ["qa/manifests/m.md:3"]


@pytest.mark.parametrize("edit", ["byte", "append", "rename", "delete"])
def test_any_change_to_a_sealed_unit_invalidates_the_seal(tmp_path: Path, edit: str) -> None:
    root = tree(tmp_path)
    block(root, [row(root, "qa/manifests/m.md")])
    path = root / "qa/manifests/m.md"
    if edit == "byte":
        path.write_text(MANIFEST.replace("cycle 1", "cycle 2"), encoding="utf-8", newline="")
    elif edit == "append":
        path.write_text(MANIFEST + "\n", encoding="utf-8", newline="")
    elif edit == "rename":
        path.rename(root / "qa/manifests/n.md")
    else:
        path.unlink()
    assert any(v.rule == "decision-citation-coverage" and "m.md" in v.location + v.detail
               for v in blocking_of(root))
    if edit in {"byte", "append"}:
        assert any(v.location == "qa/manifests/m.md:3" for v in blocking_of(root))


def test_crlf_checkout_still_matches_an_lf_seal(tmp_path: Path) -> None:
    root = tree(tmp_path)
    block(root, [row(root, "qa/manifests/m.md")])
    (root / "qa/manifests/m.md").write_bytes(MANIFEST.replace("\n", "\r\n").encode("utf-8"))
    assert blocking_of(root) == []


def _commit_tree_sha(root: Path) -> str:
    return git(root, "commit-tree", "HEAD^{tree}", "-m", "orphan")


@pytest.mark.parametrize("case", [
    "wrong-hash", "not-ancestor", "baseline-content", "maker", "build", "blank-reason",
    "blank-reviewer", "no-evidence", "bad-baseline", "bad-scope"])
def test_a_bad_seal_row_is_rejected(tmp_path: Path, case: str) -> None:
    root = tree(tmp_path)
    bad = row(root, "qa/manifests/m.md")
    if case == "wrong-hash":
        bad["sha256"] = "0" * 64
    elif case == "not-ancestor":
        bad["baseline"] = _commit_tree_sha(root)
    elif case == "baseline-content":
        write(root, "qa/manifests/m.md", MANIFEST + "later\n")
        bad = row(root, "qa/manifests/m.md")
    elif case == "maker":
        bad["reviewer"] = "/maker"
    elif case == "build":
        bad["reviewer"] = "/root/build_t196_citation_checks"
    elif case == "blank-reason":
        bad["reason"] = "  "
    elif case == "blank-reviewer":
        bad["reviewer"] = ""
    elif case == "no-evidence":
        bad["review_ref"] = "qa/missing.md"
    elif case == "bad-baseline":
        bad["baseline"] = "not-a-sha"
    else:
        bad["scope"] = "directory"
    block(root, [bad])
    assert any(v.location == "qa/manifests/m.md:3" for v in blocking_of(root))
    assert any(v.rule == "decision-citation-coverage" and v.location != "qa/manifests/m.md:3"
               for v in blocking_of(root))


@pytest.mark.parametrize("rel", ["qa/contracts/c.md", "qa/gates/g.md", "docs/SNAPSHOT.md",
                                 "qa/feedback-inbox.md"])
def test_living_records_can_never_be_sealed(tmp_path: Path, rel: str) -> None:
    root = tree(tmp_path, {rel: "Status: checked-PASS\nauthorized by D-001\n"})
    block(root, [row(root, rel)])
    problems = [v for v in blocking_of(root) if "not sealable" in v.detail]
    assert problems and problems[0].rule == "decision-citation-coverage"


def test_duplicate_and_conflicting_seals_for_one_unit_both_fail(tmp_path: Path) -> None:
    root = tree(tmp_path)
    good = row(root, "qa/manifests/m.md")
    block(root, [good, dict(good)])
    assert any("duplicate or conflicting" in v.detail for v in blocking_of(root))
    block(root, [good, dict(good, reason="another reason")])
    assert any("duplicate or conflicting" in v.detail for v in blocking_of(root))
    assert any(v.location == "qa/manifests/m.md:3" for v in blocking_of(root))


def test_a_new_citation_in_an_unsealed_file_still_fails(tmp_path: Path) -> None:
    root = tree(tmp_path, {"qa/manifests/m.md": MANIFEST,
                            "qa/manifests/n.md": "Status: checked-PASS\nsee D-001\n"})
    block(root, [row(root, "qa/manifests/m.md")])
    assert [v.location for v in blocking_of(root)] == ["qa/manifests/n.md:2"]


def test_a_non_terminal_manifest_cannot_be_sealed(tmp_path: Path) -> None:
    root = tree(tmp_path, {"qa/manifests/m.md": "Status: ready-for-check\nsee D-001\n"})
    block(root, [row(root, "qa/manifests/m.md")])
    assert any("not terminal" in v.detail for v in blocking_of(root))


@pytest.mark.parametrize("status", ["checked-PASS", "merged-no-check (docs-lane)",
                                    "merged-no-check (test-lane)", "STALLED"])
def test_each_terminal_status_is_eligible(tmp_path: Path, status: str) -> None:
    root = tree(tmp_path, {"qa/manifests/m.md": f"**Status:** {status} — done\nsee D-001\n"})
    block(root, [row(root, "qa/manifests/m.md")])
    assert blocking_of(root) == []


def test_a_verdict_is_sealable_only_when_its_same_slug_manifest_is_closed(tmp_path: Path) -> None:
    files = {"qa/manifests/m.md": "Status: checked-PASS\n", "qa/verdicts/m.md": "PASS D-001\n",
             "qa/verdicts/open.md": "PASS D-001\n", "qa/manifests/open.md": "Status: BUILDING\n"}
    root = tree(tmp_path, files)
    block(root, [row(root, "qa/verdicts/m.md"), row(root, "qa/verdicts/open.md")])
    blocking = blocking_of(root)
    assert any(v.location == "qa/verdicts/open.md:1" for v in blocking)
    assert not any(v.location == "qa/verdicts/m.md:1" for v in blocking)


def test_a_seal_beside_a_per_occurrence_row_does_not_reclassify_it(tmp_path: Path) -> None:
    root = tree(tmp_path)
    claim = dict(path="qa/manifests/m.md", line_text="authorized by D-001", id="D-001",
                 ordinal=1, multiplicity=1, kind="authorization-claim", reason="claim",
                 reviewer="Oracle Reviewer", review_ref="qa/review.md")
    write(root, "qa/review.md", "Attribution: /checker\nAttribution: Oracle Reviewer\n")
    block(root, [row(root, "qa/manifests/m.md"), claim])
    found = citations.check_citation_subjects(root)
    assert any(v.rule == "decision-citation-declaration" and v.location == "qa/manifests/m.md:3"
               for v in found)
    assert not any(v.rule == "decision-citation-sealed" for v in found)


def test_entry_scope_seal_covers_one_full_decision_entry_only(tmp_path: Path) -> None:
    log = LOG + "see D-001 again\n## D-002 | 2026-09-02 | type: decision | status: ACTIVE\n" \
                "**What:** y D-001\n"
    root = tree(tmp_path, {"docs/DECISIONS.md": log})
    block(root, [row(root, "docs/DECISIONS.md", scope="entry:D-001",
                       sha256=sha("\n".join(log.split("\n")[:3]) + "\n"))])
    assert [v.location for v in blocking_of(root)] == ["docs/DECISIONS.md:4", "docs/DECISIONS.md:5"]
    block(root, [row(root, "docs/DECISIONS.md", scope="entry:D-009", sha256="0" * 64)])
    assert any("no single full entry" in v.detail for v in blocking_of(root))


def test_a_changed_entry_invalidates_its_seal_but_not_the_neighbour(tmp_path: Path) -> None:
    log = LOG + "## D-002 | 2026-09-02 | type: decision | status: ACTIVE\n**What:** y\n"
    root = tree(tmp_path, {"docs/DECISIONS.md": log})
    rows = [row(root, "docs/DECISIONS.md", scope="entry:D-001", sha256=sha(LOG)),
            row(root, "docs/DECISIONS.md", scope="entry:D-002",
                 sha256=sha(log.split(LOG)[1]))]
    block(root, rows)
    assert blocking_of(root) == []
    write(root, "docs/DECISIONS.md", log.replace("**What:** x", "**What:** xx"))
    assert [v.location for v in blocking_of(root) if v.location.endswith(":1")] == [
        "docs/DECISIONS.md:1"]
