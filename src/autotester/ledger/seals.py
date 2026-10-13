"""L10 immutable-history dispositions: sealed records and the known-disputed claims.

One reviewed, hash-bound `sealed-record` row covers the citation occurrences of one CLOSED
historical unit (a terminal manifest, its verdict, or one full decision entry) so a closed
record needs one review instead of one per occurrence. Doctor re-derives everything from the
working tree and git and never trusts the row: any changed byte, a deleted or renamed unit, a
baseline that is not an ancestor of HEAD, a non-independent reviewer or an ineligible path
invalidates the seal. A seal fills coverage only; it never classifies a claim or proves one.
The two known-disputed historical claims (K1, K2) can never be sealed.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from collections import Counter
from itertools import pairwise
from pathlib import Path, PurePosixPath

from autotester.doctor import Violation
from autotester.schema.ledger import SealedRecord

KNOWN_DISPUTED: dict[tuple[str, str, int], tuple[str, str]] = {
    ("docs/DECISIONS.md", "D-000", 1):
        ("K1", "07b0051afd93a9f8b3916d0ed78f4751110482e074a13446ecf4bfa89802a915"),
    ("docs/DECISIONS.md", "D-005", 1):
        ("K2", "01370a7ef0a4ffc0471c5475054c1ef47d88c3386ff78f7ae3d3542215639f69"),
}
"""(path, cited id, ordinal on the line) -> (label, sha256 of the exact line text, LF only).
Recorded by the owner (D-069); a changed line no longer matches and is blocking again."""

_TERMINAL = re.compile(r"(?:checked-PASS|STALLED|merged-no-check \((?:docs|test)-lane\))"
                       r"(?![\w-])")
_STATUS = re.compile(r"^\s*(?:#{1,6}\s*)?(?:\*\*)?Status(?::\*\*|\*\*:|:)\s*(?:\*\*)?(.*)$")
_ENTRY_HEADER = re.compile(r"^## D-", re.MULTILINE)
_INDEPENDENT = re.compile(r"^(?:/checker\b.*|Umesh\b.*)$")
_NOT_INDEPENDENT = re.compile(r"maker|build", re.IGNORECASE)

Ranges = dict[str, list[tuple[int, int]]]


def line_digest(line: str) -> str:
    """sha256 of one line's text, the key shape `KNOWN_DISPUTED` uses."""
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def disputed_label(rel: str, line: str, cid: str, ordinal: int) -> str | None:
    """K1/K2 label when this exact occurrence is a recorded known-disputed claim."""
    known = KNOWN_DISPUTED.get((rel, cid, ordinal))
    return known[0] if known and known[1] == line_digest(line) else None


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n")


def _unit(text: str, scope: str) -> tuple[str, int, int] | None:
    """(unit text, first line, last line), 1-indexed, or None when not one full unit."""
    text = _lf(text)
    if scope == "file":
        return text, 1, text.count("\n") + (0 if text.endswith("\n") else 1)
    starts = [m.start() for m in _ENTRY_HEADER.finditer(text)] + [len(text)]
    spans = [(a, b) for a, b in pairwise(starts)
             if re.match(rf"## {re.escape(scope[6:])}\b", text[a:b])]
    if len(spans) != 1:
        return None
    a, b = spans[0]
    first = text.count("\n", 0, a) + 1
    return text[a:b], first, first + text[a:b].rstrip("\n").count("\n")


def _digest(unit: str) -> str:
    return hashlib.sha256(unit.encode("utf-8")).hexdigest()


def _git(root: Path, *args: str) -> bytes | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=60,
                              check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _terminal(path: Path) -> bool:
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        found = _STATUS.match(line)
        if found:
            return _TERMINAL.match(found[1].strip().lstrip("*").strip()) is not None
    return False


def _ineligible(root: Path, seal: SealedRecord) -> str | None:
    parts = PurePosixPath(seal.path).parts
    if seal.path == "docs/DECISIONS.md" or (len(parts) == 3 and parts[:2] == ("docs", "archive")
                                            and parts[2] != "INDEX.md"):
        return None if seal.scope != "file" else "a decision log seals one full entry, not a file"
    if len(parts) == 3 and parts[:2] in {("qa", "manifests"), ("qa", "verdicts")}:
        if seal.scope != "file":
            return "a manifest or verdict seals the whole file"
        manifest = root / "qa" / "manifests" / parts[2]
        return None if _terminal(manifest) else "manifest Status is not terminal"
    return "path is a living or appended-to record and is not sealable"


def _reason(root: Path, seal: SealedRecord, ancestors: dict[str, bool]) -> str | None:
    """Why this seal is invalid, or None. Never trusts any field it can re-derive."""
    if not _INDEPENDENT.match(seal.reviewer) or _NOT_INDEPENDENT.search(seal.reviewer):
        return "reviewer is not the independent /checker or Umesh"
    if (reason := _ineligible(root, seal)) is not None:
        return reason
    path = root / seal.path
    if not path.is_file():
        return "unit is deleted or renamed"
    unit = _unit(path.read_text(encoding="utf-8", errors="replace"), seal.scope)
    if unit is None:
        return "no single full entry for that id"
    if _digest(unit[0]) != seal.sha256.lower():
        return "unit hash differs from the seal (any change invalidates it)"
    if ancestors.setdefault(seal.baseline, _git(root, "merge-base", "--is-ancestor",
                                                seal.baseline, "HEAD") is not None) is False:
        return "baseline is not an ancestor of HEAD"
    old = _git(root, "show", f"{seal.baseline}:{seal.path}")
    old_unit = _unit(old.decode("utf-8", errors="replace"), seal.scope) if old else None
    if old_unit is None or _digest(old_unit[0]) != seal.sha256.lower():
        return "baseline content does not hash to the sealed value"
    if any(line_digest(line) == digest for (rel, _, _), (_, digest) in KNOWN_DISPUTED.items()
           if rel == seal.path for line in unit[0].split("\n")):
        return "unit contains a known-disputed claim, which a seal can never cover"
    return None


def valid_seals(root: Path, seals: list[SealedRecord], out: list[Violation]) -> Ranges:
    """Line ranges each valid seal covers, per path; every invalid seal is reported."""
    keys = Counter((s.path, s.scope) for s in seals)
    covered: Ranges = {}
    ancestors: dict[str, bool] = {}
    for seal in seals:
        why = ("duplicate or conflicting seals for one unit" if keys[(seal.path, seal.scope)] > 1
               else _reason(root, seal, ancestors))
        if why is not None:
            out.append(Violation("decision-citation-coverage", seal.path,
                                 f"seal {seal.scope} rejected: {why}"))
            continue
        unit = _unit((root / seal.path).read_text(encoding="utf-8", errors="replace"), seal.scope)
        covered.setdefault(seal.path, []).append((unit[1], unit[2]) if unit else (0, 0))
    return covered


def is_sealed(covered: Ranges, rel: str, number: int) -> bool:
    """True when a valid seal covers line `number` of `rel`."""
    return any(a <= number <= b for a, b in covered.get(rel, []))
