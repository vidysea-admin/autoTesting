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


def next_issue_id(rows: list[dict]) -> str:
    highest = max((int(m.group(1)) for r in rows if (m := _NUMERIC.match(str(r.get("id", ""))))),
                  default=0)
    return f"AT-{highest + 1}"


def append_issue(path: Path, row: dict) -> dict:
    """Append one row; refuse a duplicate id (call `next_issue_id` for a free one)."""
    existing = read_rows(path) if path.exists() else []
    if any(r.get("id") == row.get("id") for r in existing):
        raise ValueError(f"{row.get('id')} already exists in {path}; use {next_issue_id(existing)}")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


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
    for issue, titles in sorted(duplicate_groups(read_rows(ledger)).items()):
        extra = Counter((issue, t) for t in titles) - allowed
        if extra:
            out.append(Violation("issue-id-duplicate", "qa/issues.jsonl",
                                 f"{issue} appears on {len(titles)} rows; renumber the later one"))
    return out
