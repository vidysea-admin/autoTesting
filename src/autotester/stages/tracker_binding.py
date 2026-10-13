"""TRACKER BINDING: propose a project's column mapping from a header row, and keep it per project.

Its one job is TB14: the same code serves any sheet layout. Matching is by normalised header text
against a generic synonym table (no project's own column names live here); a field with two
candidates or none is `unmapped` and the project still works in-product. The binding is one file
under `projects/<slug>/`, so project A's binding is never read for project B.
"""

from __future__ import annotations

import re
from pathlib import Path

from autotester.core.paths import ProjectPaths
from autotester.schema.sheet_plan import OWNED_FIELDS
from autotester.schema.tracker_binding import TrackerBinding
from autotester.store.filestore import read_json, write_json

SYNONYMS: dict[str, tuple[str, ...]] = {
    "bug_key": ("bugid", "bugkey", "id", "key", "issueid", "ticket"),
    "title": ("title", "summary", "bugtitle", "description", "name"),
    "severity": ("severity", "priority", "sev"),
    "screen": ("screen", "page", "module", "area", "screenname"),
    "status": ("status", "state"),
    "assignee": ("assignee", "assignedto", "owner", "assigned"),
    "first_seen": ("firstseen", "reported", "reportedon", "date", "created", "datereported"),
    "last_seen": ("lastseen", "updated", "lastupdated"),
    "count": ("count", "occurrences", "times", "seen"),
}
BINDING_FILE = "tracker_binding.json"


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def propose_binding(sheet_id: str, tab: str, header: list[str]) -> TrackerBinding:
    """Map header cells to owned bug fields. Uses the header row only, never a data row."""
    taken: dict[str, str] = {}
    unmapped: dict[str, list[str]] = {}
    for field in OWNED_FIELDS:
        found = [h for h in header if h.strip() and _norm(h) in SYNONYMS[field]]
        if len(found) == 1 and found[0] not in taken.values():
            taken[field] = found[0]
        else:
            unmapped[field] = found
    return TrackerBinding(sheet_id=sheet_id, tab=tab, columns=taken, unmapped=unmapped)


def binding_path(slug: str, root: Path | None = None) -> Path:
    return ProjectPaths(slug, root).dir / BINDING_FILE


def save_binding(slug: str, binding: TrackerBinding, root: Path | None = None) -> None:
    write_json(binding_path(slug, root), binding)


def load_binding(slug: str, root: Path | None = None) -> TrackerBinding | None:
    return read_json(binding_path(slug, root), TrackerBinding)
