"""Give fresh ids to the LATER row of every duplicated id in qa/issues.jsonl.

Rows are matched by (id, title) and keep their position; the first occurrence of
an id keeps it. Fresh ids continue after the highest AT-<n> in the file.
  --dry-run   print the plan, write nothing
  --path P    ledger to rewrite (default qa/issues.jsonl); --grandfather P2 also
              drops renumbered entries from that list (it may only shrink).
Run by the maker after the checker passes, never by a builder.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from autotester.ledger.issue_ids import next_issue_id


def plan(lines: list[str]) -> list[tuple[int, str, str, str]]:
    """[(line_index, old_id, title, new_id)] for each non-first occurrence."""
    rows = [(i, json.loads(x)) for i, x in enumerate(lines) if x.strip()]
    seen: set[str] = set()
    later: list[tuple[int, str, str]] = []
    for i, row in rows:
        if row["id"] in seen:
            later.append((i, row["id"], str(row.get("title", ""))))
        seen.add(row["id"])
    taken = [{"id": r["id"]} for _, r in rows]
    out = []
    for i, old, title in later:
        new = next_issue_id(taken)
        taken.append({"id": new})
        out.append((i, old, title, new))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--path", default="qa/issues.jsonl")
    ap.add_argument("--grandfather", default=None)
    args = ap.parse_args(argv)
    path = Path(args.path)
    lines = path.read_text(encoding="utf-8").splitlines()
    steps = plan(lines)
    for i, old, title, new in steps:
        print(f"line {i + 1}: {old} -> {new}  ({title[:60]})")
    print(f"{len(steps)} row(s) to renumber")
    if args.dry_run or not steps:
        return 0
    for i, old, title, new in steps:
        row = json.loads(lines[i])
        assert row["id"] == old and row.get("title", "") == title
        row["id"] = new
        lines[i] = json.dumps(row, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    if args.grandfather:
        gf = Path(args.grandfather)
        keep = {(s[1], s[2]) for s in steps}
        entries = json.loads(gf.read_text(encoding="utf-8"))
        left = [e for e in entries if (e["id"], e["title"]) not in keep]
        gf.write_text(json.dumps(left, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
