"""Id uniqueness for `qa/issues.jsonl` (AT-676, AT-645).

The file is `merge=union` in `.gitattributes`, so two branches that each appended
"the next id" both survive a merge and the same id lands on two different issues.
Two guards, because the merge can bypass any writer:

- WRITE: `append_issue` refuses a row whose id is already taken; `next_issue_id`
  hands out a free one.
- CHECK: `check_issue_id_unique` (a doctor rule) reports any id that repeats.

The ~10 duplicates that predate the guard are listed in
`qa/issues-dupes-grandfathered.json` as {id, title} pairs. A repeated id is
tolerated only while every row sharing it is in that list; the list can only
shrink (renumber a row, then delete its entry). Stale entries are harmless.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from autotester.core.file_lock import file_lock
from autotester.doctor import Violation

GRANDFATHER = Path("qa") / "issues-dupes-grandfathered.json"
_NUMERIC = re.compile(r"AT-(\d+)$")


def read_rows(path: Path) -> list[dict]:
    """Every parseable row of the ledger, in file order (blank/bad lines skipped)."""
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def duplicate_groups(rows: list[dict]) -> dict[str, list[str]]:
    """{id: [title, ...]} for every id carried by more than one row."""
    titles: dict[str, list[str]] = {}
    for row in rows:
        titles.setdefault(str(row.get("id", "")), []).append(str(row.get("title", "")))
    return {i: t for i, t in titles.items() if i and len(t) > 1}


def duplicate_lines(path: Path) -> dict[str, list[tuple[int, str]]]:
    """{id: [(1-based line number, title), ...]} for every id on more than one line."""
    found: dict[str, list[tuple[int, str]]] = {}
    text = path.read_text(encoding="utf-8", errors="replace")
    for number, line in enumerate(text.splitlines(), 1):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("id"):
            found.setdefault(str(row["id"]), []).append((number, str(row.get("title", ""))))
    return {i: v for i, v in found.items() if len(v) > 1}


def next_issue_id(rows: list[dict]) -> str:
    highest = max((int(m.group(1)) for r in rows if (m := _NUMERIC.match(str(r.get("id", ""))))),
                  default=0)
    return f"AT-{highest + 1}"


def append_issue(path: Path, row: dict) -> dict:
    """Append one row; refuse a duplicate id (call `next_issue_id` for a free one)."""
    with file_lock(path.with_name(path.name + ".lock"), what="issues ledger"):
        existing = read_rows(path) if path.exists() else []
        if any(r.get("id") == row.get("id") for r in existing):
            raise ValueError(
                f"{row.get('id')} already exists in {path}; use {next_issue_id(existing)}")
        _append_line(path, row)
    return row


def _append_line(path: Path, row: dict) -> None:
    line = json.dumps(row, ensure_ascii=False) + "\n"
    if path.exists() and path.stat().st_size and not path.read_bytes().endswith(b"\n"):
        line = "\n" + line  # never glue onto an unterminated last row
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)


def append_new_issue(path: Path, row: dict) -> dict:
    """Allocate the next free id and append, in one locked step (collision-safe).

    Allocation and append share the lock, so two local writers cannot take the same
    id. Branches merged with `merge=union` can still collide; `check_issue_id_unique`
    is the backstop for that case."""
    with file_lock(path.with_name(path.name + ".lock"), what="issues ledger"):
        existing = read_rows(path) if path.exists() else []
        new = {**row, "id": next_issue_id(existing)}
        _append_line(path, new)
    return new


def _grandfathered(root: Path) -> Counter:
    try:
        entries = json.loads((root / GRANDFATHER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Counter()
    return Counter((str(e.get("id")), str(e.get("title"))) for e in entries if isinstance(e, dict))


def check_issue_id_unique(root: Path) -> list[Violation]:
    """No id may name two issues, except the grandfathered pairs."""
    ledger = root / "qa" / "issues.jsonl"
    if not ledger.exists():
        return []
    allowed = _grandfathered(root)
    out: list[Violation] = []
    for issue, spots in sorted(duplicate_lines(ledger).items()):
        extra = Counter((issue, t) for _, t in spots) - allowed
        if extra:
            where = ", ".join(str(n) for n, _ in spots)
            out.append(Violation("issue-id-duplicate", "qa/issues.jsonl",
                                 f"{issue} appears on lines {where}; renumber the later one"))
    return out
