"""Reads the one current citation-review block in `qa/feedback-inbox.md` (L10).

Rows are single-line `<!-- citation-review: {...} -->` comments between a BEGIN and an END
marker. A row is either a per-occurrence `CitationReview` or, when its `kind` is
`sealed-record`, a `SealedRecord`. This module only parses and checks that a row's
`review_ref` points at a real attribution line; deciding what a row covers is not its job.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from autotester.doctor import Violation
from autotester.schema.ledger import CitationReview, SealedRecord

_REVIEW = re.compile(r"<!-- citation-review: (\{.*\}) -->")
_BEGIN = "<!-- BEGIN T196 CURRENT CITATION REVIEWS -->"
_END = "<!-- END T196 CURRENT CITATION REVIEWS -->"


def strict_object(pairs: list[tuple[str, object]]) -> dict:
    """`object_pairs_hook` that rejects duplicate JSON keys."""
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate JSON keys")
    return dict(pairs)


def review_evidence(root: Path, row: CitationReview | SealedRecord) -> bool:
    """True when `row.review_ref` names a real in-repo line carrying the reviewer attribution."""
    target, separator, line_no = row.review_ref.rpartition(":")
    target = target if separator else row.review_ref
    if separator and (not line_no.isdigit() or int(line_no) < 1):
        return False
    relative = Path(target)
    if (relative.is_absolute() or "\\" in target or ":" in target or
            ".." in relative.parts or relative.as_posix() != target):
        return False
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        return False
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if separator:
        lines = lines[int(line_no) - 1:int(line_no)]
    return any(row.reviewer in line and re.search(r"(?:Attribution|Reviewer):", line)
               for line in lines)


def _parse_row(line: str) -> CitationReview | SealedRecord:
    match = _REVIEW.fullmatch(line.strip())
    if match is None:
        raise ValueError("malformed citation-review comment")
    data = json.loads(match[1], object_pairs_hook=strict_object)
    if not isinstance(data, dict):
        raise ValueError("citation-review comment must hold one JSON object")
    model = SealedRecord if data.get("kind") == "sealed-record" else CitationReview
    return model.model_validate(data)


def current_reviews(root: Path, out: list[Violation]
                    ) -> tuple[list[CitationReview], list[SealedRecord]]:
    """Valid per-occurrence rows and seal rows; every invalid row is reported into `out`."""
    path = root / "qa/feedback-inbox.md"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    begin, end = [i for i, line in enumerate(lines) if line == _BEGIN], [
        i for i, line in enumerate(lines) if line == _END]
    if not begin and not end:
        return [], []
    if len(begin) != 1 or len(end) != 1 or begin[0] >= end[0]:
        out.append(Violation("decision-citation-coverage", "qa/feedback-inbox.md",
                             "current review block must have one ordered BEGIN/END pair"))
        return [], []
    reviews: list[CitationReview] = []
    seals: list[SealedRecord] = []
    for index in range(begin[0] + 1, end[0]):
        if not lines[index].strip():
            continue
        try:
            row = _parse_row(lines[index])
            if not review_evidence(root, row):
                raise ValueError("review reference is unavailable or lacks reviewer attribution")
            (seals if isinstance(row, SealedRecord) else reviews).append(row)
        except (ValueError, OSError) as error:
            out.append(Violation("decision-citation-coverage", f"qa/feedback-inbox.md:{index + 1}",
                                 f"invalid current review: {error}"))
    return reviews, seals
