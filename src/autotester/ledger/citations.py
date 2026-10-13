"""Does every `D-NNN` cited in a gate, contract, manifest, verdict or doc resolve to an
appended decision entry? (`qa/contracts/living-ledger.md` L9, AT-710.)

`scripts/append_decision.ps1` validates ids on WRITE, so the log cannot hold a gap; nothing
validated them on READ, so a phantom `D-056` written into a gate was trusted by every later
reader and the question it was meant to close reached the human a third time. This module is
that read-side check. It is a sibling of `checks.py` (288/300) and `evidence_specs.py` under
the AT-506 split precedent: a new check family gets its own module (D-058 point 1).

Two exemptions exist and both are DECLARED, never inferred from prose (L9): a foreign id space
is out of scope at ENTRY granularity inside `docs/DECISIONS.md`, and a non-claiming occurrence
is a `NON_CLAIMING` row carrying its reason. Neither is ever a whole-file exemption.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path

from autotester.doctor import Violation
from autotester.ledger import seals
from autotester.ledger.review_block import current_reviews, strict_object
from autotester.schema.ledger import CitationReview, DecisionClaim

CITING_GLOBS = ("qa/gates/*.md", "qa/contracts/*.md", "qa/manifests/*.md",
                "qa/verdicts/*.md", "docs/*.md")
_CITATION = re.compile(r"\bD-\d+\b")
_LOG_HEADER = re.compile(r"^##\s+(D-\d+)\b", re.MULTILINE)
_ARCHIVE_LINE = re.compile(r"^(?:##\s+)?(D-\d+)\s*\|", re.MULTILINE)
_FOREIGN_LOG = re.compile(r"decisions[/\\]log\.md", re.IGNORECASE)
_CLAIM_COMMENT = re.compile(r"<!--\s*decision-claim:.*?(?:-->|$)", re.DOTALL)
_CANONICAL = re.compile(r'Decision claim (D-\d+): ("(?:[^"\\]|\\.)*") '
                        r'<!-- decision-claim: (\{.*\}) -->')

NON_CLAIMING: dict[tuple[str, str, str], str] = {
    ("qa/contracts/living-ledger.md", "already cites `D-088` twice", "D-088"):
        "L9 quotes the foreign-id-space example (the id lives in the AIOS log, not this one)",
    ("qa/contracts/living-ledger.md", "and `:638` cite `D-088`", "D-088"):
        "Amendment-log entry describing the same foreign-id-space example",
    ("qa/manifests/at710-decision-citation-resolver.md", "citing `D-088`, exempted", "D-088"):
        "the resolver's own manifest reporting which lines its entry-scoped rule exempted",
}
"""(file, distinctive text on the line, cited id) -> why the occurrence claims no
authorization. Keyed by line TEXT rather than number so an appended amendment above it
does not silently un-declare it; per occurrence, never per file."""


def appended_ids(root: Path) -> set[str]:
    """Ids with an entry in `docs/DECISIONS.md` or `docs/archive/` (archiving is not deletion)."""
    found: set[str] = set()
    log = root / "docs" / "DECISIONS.md"
    if log.exists():
        found |= set(_LOG_HEADER.findall(log.read_text(encoding="utf-8", errors="replace")))
    for path in sorted((root / "docs" / "archive").glob("*.md")):
        found |= set(_ARCHIVE_LINE.findall(path.read_text(encoding="utf-8", errors="replace")))
    return found


def foreign_ids_by_line(text: str) -> set[tuple[int, str]]:
    """(1-indexed line, id) pairs in `docs/DECISIONS.md` an entry qualifies by another log.

    Scope is the ENTRY, not the line: an id on a line with a path to a decisions log
    exempts that id everywhere in the same `## D-NNN` entry.
    """
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if _LOG_HEADER.match(ln)] + [len(lines)]
    exempt: set[tuple[int, str]] = set()
    for begin, end in pairwise(starts):
        entry = lines[begin:end]
        foreign = {cid for ln in entry if _FOREIGN_LOG.search(ln)
                   for cid in _CITATION.findall(ln)}
        exempt |= {(begin + off + 1, cid) for off, ln in enumerate(entry)
                   for cid in _CITATION.findall(ln) if cid in foreign}
    return exempt


def _declared(rel: str, line: str, cid: str) -> bool:
    return any(rel == f and cid == i and snippet in line for f, snippet, i in NON_CLAIMING)


def _scan(path: Path, root: Path, appended: set[str]) -> list[Violation]:
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    foreign = foreign_ids_by_line(text) if rel == "docs/DECISIONS.md" else set()
    out = []
    pairs = zip(text.splitlines(), _visible_lines(text), strict=False)
    for line_no, (line, visible) in enumerate(pairs, start=1):
        for cid in dict.fromkeys(_CITATION.findall(visible)):
            if cid in appended or (line_no, cid) in foreign or _declared(rel, line, cid):
                continue
            out.append(Violation(
                "decision-citation-dangling", f"{rel}:{line_no}",
                f"cites {cid}, which has no `## {cid}` entry in docs/DECISIONS.md "
                "or docs/archive/"))
    return out


def check_decision_citations(root: Path) -> list[Violation]:
    """L9: every cited `D-NNN` resolves to a header, or is a declared exemption."""
    appended = appended_ids(root)
    out: list[Violation] = []
    for glob in CITING_GLOBS:
        for path in sorted(root.glob(glob)):
            out.extend(_scan(path, root, appended))
    return out


def _quote_text(value: str) -> str:
    return " ".join(value.split())


def _visible_lines(text: str) -> list[str]:
    return _CLAIM_COMMENT.sub(lambda match: "\n" * match[0].count("\n"), text).split("\n")


def _decision_subjects(root: Path) -> dict[str, list[str | None]]:
    subjects = defaultdict(list)
    paths = [root / "docs/DECISIONS.md", *sorted((root / "docs/archive").glob("*.md"))]
    for path in paths:
        if not path.is_file() or path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        headers = list(_LOG_HEADER.finditer(text))
        for index, header in enumerate(headers):
            body = text[header.end():headers[index + 1].start() if index + 1 < len(headers)
                        else len(text)]
            fields = list(re.finditer(r"^\*\*([^*\n]+):\*\*(.*)$", body, re.MULTILINE))
            what = [i for i, field in enumerate(fields) if field[1] == "What"]
            content = None
            if len(what) == 1:
                field_index = what[0]
                start = fields[field_index].start(2)
                end = (fields[field_index + 1].start() if field_index + 1 < len(fields)
                       else len(body))
                content = _quote_text(body[start:end]) or None
            subjects[header[1]].append(content)
    return dict(subjects)


def _canonical_claim(line: str) -> DecisionClaim:
    match = _CANONICAL.fullmatch(line.strip())
    if match is None:
        raise ValueError("requires one complete visible canonical Decision claim line")
    claim = DecisionClaim.model_validate(json.loads(match[3], object_pairs_hook=strict_object))
    if match[1] != claim.id or _quote_text(json.loads(match[2])) != _quote_text(claim.what):
        raise ValueError("visible id/quotation disagrees with decision-claim JSON")
    return claim


def _compare_quote(cid: str, quote: str | None, subjects: dict, location: str,
                   out: list[Violation]) -> None:
    if quote is None:
        out.append(Violation("decision-citation-declaration", location,
                             f"{cid} mutable authorization requires canonical visible claim"))
        return
    bodies = subjects.get(cid, [])
    rule = "subject-unavailable" if len(bodies) != 1 or bodies[0] is None else None
    if rule is None and _quote_text(quote) not in bodies[0]:
        rule = "subject-mismatch"
    if rule:
        out.append(Violation("decision-citation-" + rule, location,
                             f"{cid} quotation does not match one available What subject"))


def _kind_checks(review: CitationReview, cid: str, line: str, number: int, where: str,
                 foreign: set, out: list[Violation]) -> None:
    if review.kind == "foreign-entry" and (number, cid) not in foreign:
        out.append(Violation("decision-citation-coverage", where, f"{cid} not a foreign entry"))
    if review.kind == "structural-header" and not re.match(rf"^##\s+{re.escape(cid)}\b", line):
        out.append(Violation("decision-citation-coverage", where,
                             f"{cid} not a structural header"))


def _judge(active: list, claim: DecisionClaim | None, line: str, location: str,
           subjects: dict, out: list[Violation]) -> None:
    rel = location.rpartition(":")[0]
    for cid, review in active:
        if review is None or (review.kind != "authorization-claim" and claim is None):
            continue
        if claim is not None and (cid != claim.id or review.ordinal != 1):
            if review.kind == "authorization-claim":
                _compare_quote(cid, None, subjects, location, out)
            continue
        quote = claim.what if claim is not None else review.what
        label = seals.disputed_label(rel, line, cid, review.ordinal) if quote is None else None
        if label:
            out.append(Violation(
                "decision-citation-known-disputed", location,
                f"{cid} {label}: recorded known-disputed historical claim (D-069), non-blocking"))
            continue
        _compare_quote(cid, quote, subjects, location, out)


def _citation_line(ids: list[str], rel: str, number: int, line: str, rows: dict,
                   subjects: dict, multiplicity: int, foreign: set, out: list[Violation],
                   sealed: bool = False) -> int:
    """Judge one source line; returns how many occurrences a valid seal alone covered."""
    seen, covered = Counter(), 0
    location = f"{rel}:{number}"
    active = []
    for cid in ids:
        seen[cid] += 1
        matches = rows.get((rel, line, cid, seen[cid]), [])
        review = (matches[0] if len(matches) == 1 and matches[0].multiplicity == multiplicity
                  else None)
        if review is None and sealed:
            covered += 1
            continue
        if review is None:
            out.append(Violation("decision-citation-coverage", location,
                                 f"{cid} occurrence {seen[cid]} needs one current review"))
        else:
            _kind_checks(review, cid, line, number, location, foreign, out)
        if not ((number, cid) in foreign or _declared(rel, line, cid) or
                (review is not None and review.kind == "nonclaiming")):
            active.append((cid, review))
    if not active and ids:
        return covered
    claim = None
    if "decision-claim:" in line or "Decision claim" in line:
        try:
            claim = _canonical_claim(line)
        except ValueError as error:
            out.append(Violation("decision-citation-declaration", location, f"{ids}: {error}"))
    _judge(active, claim, line, location, subjects, out)
    return covered


def _scan_file(path: Path, root: Path, ctx: dict, out: list[Violation]) -> int:
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    foreign = foreign_ids_by_line(text) if rel == "docs/DECISIONS.md" else set()
    lines = text.splitlines()
    counts, sealed_total = Counter(lines), 0
    for number, (line, visible) in enumerate(zip(lines, _visible_lines(text), strict=False), 1):
        ordinals, ids = Counter(), _CITATION.findall(visible)
        for cid in ids:
            ordinals[cid] += 1
            ctx["seen"].add((rel, line, cid, ordinals[cid]))
        sealed_total += _citation_line(
            ids, rel, number, line, ctx["rows"], ctx["subjects"], counts[line], foreign, out,
            seals.is_sealed(ctx["sealed"], rel, number))
    return sealed_total


def check_citation_subjects(root: Path) -> list[Violation]:
    """L10: strict visible claims plus current reviewed coverage, distinct from L9 existence."""
    out: list[Violation] = []
    reviews, seal_rows = current_reviews(root, out)
    rows = defaultdict(list)
    for row in reviews:
        rows[(row.path, row.line_text, row.id, row.ordinal)].append(row)
    ctx = {"rows": rows, "subjects": _decision_subjects(root), "seen": set(),
           "sealed": seals.valid_seals(root, seal_rows, out)}
    sealed_total = 0
    for glob in CITING_GLOBS:
        for path in sorted(root.glob(glob)):
            sealed_total += _scan_file(path, root, ctx, out)
    for key, values in rows.items():
        if key not in ctx["seen"] or len(values) != 1:
            out.append(Violation("decision-citation-coverage", key[0],
                                 f"{key[2]} stale, duplicate or conflicting current review"))
    if sealed_total:
        out.append(Violation(
            "decision-citation-sealed", "qa/feedback-inbox.md",
            f"{sealed_total} occurrence(s) covered by {len(ctx['sealed'])} path(s) of valid "
            "sealed records (covered, not classified clean)"))
    return out
