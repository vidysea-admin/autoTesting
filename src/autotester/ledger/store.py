"""Read and append `docs/FEATURES.jsonl`. The only write path to the ledger.

Built on `store.filestore`'s generic JSONL primitives (C3: one concept, one
place for "how a file gets read or written") plus the one rule specific to
this collection: rows are history, so a repeated id is a defect, not a merge.

Also holds the read-only close-out back-reference (AT-712): which open
`qa/issues.jsonl` rows and `qa/gates/` files name a path a fixing commit changed.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

from autotester.schema.enums import FeatureEventKind, UserValue
from autotester.schema.ledger import AUTO_REASON, FeatureEvent
from autotester.store.filestore import append_jsonl as _append_jsonl
from autotester.store.filestore import read_jsonl as _read_jsonl


def load_events(path: Path) -> list[FeatureEvent]:
    """Every row, in file order. A malformed row raises with its line number;
    so does a repeated id — this collection is history, never a merge target."""
    events = _read_jsonl(path, FeatureEvent)
    seen: set[str] = set()
    for number, event in enumerate(events, start=1):
        if event.id in seen:
            raise ValueError(f"{path}:{number}: duplicate id {event.id} (rows are append-only)")
        seen.add(event.id)
    return events


def next_id(events: list[FeatureEvent]) -> str:
    highest = max((int(e.id.split("-")[1]) for e in events), default=0)
    return f"F-{highest + 1:03d}"


def append_event(path: Path, event: FeatureEvent) -> FeatureEvent:
    """Append one validated row. Never rewrites existing lines."""
    existing = load_events(path)
    if any(e.id == event.id for e in existing):
        raise ValueError(f"{event.id} already exists in {path}")
    _append_jsonl(path, event)
    return event


def latest_by_feature(events: list[FeatureEvent]) -> dict[str, FeatureEvent]:
    """The most recent row per feature — descriptions drift, so read the latest."""
    latest: dict[str, FeatureEvent] = {}
    for event in events:
        latest[event.feature] = event
    return latest


def retired(events: list[FeatureEvent]) -> list[FeatureEvent]:
    return [e for e in latest_by_feature(events).values() if e.event is FeatureEventKind.RETIRED]


def live(events: list[FeatureEvent]) -> list[FeatureEvent]:
    return [
        e for e in latest_by_feature(events).values()
        if e.event in (FeatureEventKind.LIVE, FeatureEventKind.UPDATED)
    ]


def new_event(
    events: list[FeatureEvent],
    *,
    feature: str,
    title: str,
    event: FeatureEventKind,
    description: str,
    user_value: UserValue = UserValue.NORMAL,
    reason: str | None = None,
    unit: str | None = None,
    verdict_ref: str | None = None,
    supersedes: str | None = None,
    on: date | None = None,
) -> FeatureEvent:
    """Build a row with the next id. `reason` defaults to the auto-stamp for non-retirements."""
    return FeatureEvent(
        id=next_id(events),
        feature=feature,
        title=title,
        event=event,
        date=on or date.today(),
        unit=unit,
        verdict_ref=verdict_ref,
        reason=(reason or AUTO_REASON).strip(),
        user_value=user_value,
        description=description,
        supersedes=supersedes,
    )


def raise_weight(path: Path, feature: str, value: UserValue) -> FeatureEvent:
    """Re-weight a feature after shipping (S2 amendment). Raising to high asks once."""
    events = load_events(path)
    current = latest_by_feature(events).get(feature)
    if current is None:
        raise ValueError(f"unknown feature '{feature}'")
    row = new_event(
        events,
        feature=feature,
        title=current.title,
        event=FeatureEventKind.UPDATED,
        description=current.description,
        user_value=value,
        reason=AUTO_REASON,
        unit=current.unit,
    )
    return append_event(path, row)


def check_rows_on_pass(events: list[FeatureEvent], goal_tasks: list[dict]) -> list[str]:
    """L3: every closed goal task with user_value high must have a live/updated row."""
    shipped = (FeatureEventKind.LIVE, FeatureEventKind.UPDATED)
    covered = {e.unit for e in events if e.event in shipped}
    missing = []
    for task in goal_tasks:
        closed_high = task.get("status") == "done" and task.get("user_value") == "high"
        if closed_high and task["id"] not in covered:
            missing.append(task["id"])
    return missing


def load_goal_tasks(goal_path: Path) -> list[dict]:
    if not goal_path.exists():
        return []
    return json.loads(goal_path.read_text(encoding="utf-8")).get("tasks", [])


# --- AT-712: close-out back-reference (report only; never edits a row or a gate) ---------------

_BACKREF_SKIP = ("qa/", ".goal/", ".work/", "docs/FEATURES.jsonl", "docs/DECISIONS.md")
_BACKREF_GENERIC = frozenset({"__init__.py"})


def changed_paths(root: Path, rev: str) -> list[str]:
    """Files the commit `rev` touched (read-only git, argv list, no shell)."""
    out = subprocess.run(
        ["git", "-C", str(root), "diff-tree", "--no-commit-id", "--name-only", "-r", "-m",
         "--root", rev],
        check=True, capture_output=True, text=True, encoding="utf-8").stdout
    return sorted({line.strip() for line in out.splitlines() if line.strip()})


def _backref_needles(changed: list[str]) -> list[tuple[re.Pattern[str], str, str]]:
    """(pattern, changed path, needle) for every trailing path suffix, longest first. A suffix
    must start at a path-component boundary and end at a non-word char, so `filestore.py`
    never matches `store.py` and `run_budget.py.bak` never matches `run_budget.py`."""
    found: list[tuple[re.Pattern[str], str, str]] = []
    for path in changed:
        if path.startswith(_BACKREF_SKIP):
            continue
        parts = path.split("/")
        for i in range(len(parts)):
            needle = "/".join(parts[i:])
            if i == len(parts) - 1 and parts[-1] in _BACKREF_GENERIC:
                continue
            pattern = re.compile(r"(?<![\w./\-])" + re.escape(needle) + r"(?!\w)")
            found.append((pattern, path, needle))
    return sorted(found, key=lambda f: -len(f[2]))


def _backref_hit(text: str, needles: list[tuple[re.Pattern[str], str, str]]) -> str | None:
    """The longest changed-path suffix `text` names, as 'path (basename only)'; else None."""
    text = text.replace("\\", "/")
    for pattern, path, needle in needles:
        if pattern.search(text):
            return path if "/" in needle else f"{path} (basename only)"
    return None


def backref_candidates(
    changed: list[str], issue_rows: list[dict], gates: dict[str, str],
    *, exclude: str | None = None,
) -> list[str]:
    """Open rows (title/evidence) and gate-file lines that name a changed path. A shortlist for a
    human to judge, not a verdict; the fixing row (`exclude`) and non-open rows are left out."""
    needles = _backref_needles(changed)
    lines: list[str] = []
    for row in issue_rows:
        if row.get("status") != "open" or row.get("id") == exclude:
            continue
        for field in ("title", "evidence"):
            hit = _backref_hit(str(row.get(field, "")), needles)
            if hit:
                title = str(row.get("title", ""))[:70]
                lines.append(f"{row.get('id')} [open] names {hit} in {field}: {title}")
                break
    for name, text in sorted(gates.items()):
        for number, line in enumerate(text.splitlines(), start=1):
            hit = _backref_hit(line, needles)
            if hit:
                lines.append(f"{name}:{number} names {hit}")
                break
    return lines


def _read_issue_rows(path: Path) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    notes: list[str] = []
    if not path.exists():
        return rows, notes
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            row = None
        if isinstance(row, dict):
            rows.append(row)
        else:
            notes.append(f"{path.parent.name}/{path.name}:{number} unreadable row (skipped)")
    return rows, notes


def backref_report(root: Path, rev: str, *, exclude: str | None = None) -> list[str]:
    """Candidates for commit `rev` against `<root>/qa/issues.jsonl` and `<root>/qa/gates/*.md`."""
    rows, notes = _read_issue_rows(root / "qa" / "issues.jsonl")
    gates = {f"qa/gates/{p.name}": p.read_text(encoding="utf-8", errors="replace")
             for p in sorted((root / "qa" / "gates").glob("*.md"))}
    return notes + backref_candidates(changed_paths(root, rev), rows, gates, exclude=exclude)
