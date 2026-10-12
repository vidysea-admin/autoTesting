"""TRACKER MAPPING: propose, confirm and age a column mapping from the sheet's header row alone.

Its one job is TB8 (and the mapping half of TB13/TB14). The mapping is proposed, never guessed:
deterministic synonym matching first, then, only if a provider is given, a model fallback whose
whole payload is the header cells (no data row, passed through `scrub`). A field with two
candidates or none stays `unmapped` with the candidates listed. Only a named user for whom
`holds_project_edit` is true may confirm; the check itself is T-204's and is injected, never
invented here. A header whose mapped column moved or was renamed makes the mapping `stale`.
`mapping_columns` is the one door to the write path and asserts `confirmed`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from autotester.providers.base import Provider, ProviderError
from autotester.schema.sheet_plan import SheetColumns
from autotester.schema.tracker_binding import (
    MAPPED_FIELDS,
    ColumnMapping,
    MappingReply,
    MappingStatus,
    TrackerBinding,
)

HoldsProjectEdit = Callable[[str, str], bool]
"""`(user, project slug) -> does this user hold `project.edit` there`. T-204 supplies it."""

PROMPT = Path(__file__).parents[1] / "prompts" / "tracker_mapping_v1.md"

SYNONYMS: dict[str, tuple[str, ...]] = {
    "title": ("title", "summary", "bug title", "bug", "issue", "issue title", "description",
              "name", "bug summary", "defect"),
    "severity": ("severity", "sev", "priority", "impact"),
    "screen": ("screen", "page", "module", "area", "feature", "screen name", "location"),
    "status": ("status", "state", "bug status", "progress"),
    "assignee": ("assignee", "assigned to", "owner", "assigned", "developer", "dev"),
    "date": ("date", "reported on", "date reported", "created", "created on", "found on",
             "reported date", "date found"),
    "screenshot_link": ("screenshot", "screenshot link", "evidence", "evidence link", "link",
                        "attachment", "screenshots", "image"),
    "bug_key": ("bug key", "bug id", "id", "key", "bug no", "bug number", "ticket", "ticket id",
                "issue id", "defect id", "ref", "reference"),
}


class NotAllowed(PermissionError):
    """The user does not hold `project.edit` on this project. Nothing changed."""


class MappingNotConfirmed(RuntimeError):
    """The mapping is proposed or stale. No write path may use it."""


def _norm(cell: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", cell.lower())).strip()


def _candidates(header: Sequence[str]) -> dict[str, list[int]]:
    normed = [_norm(h) for h in header]
    return {f: [i for i, n in enumerate(normed) if n and n in SYNONYMS[f]] for f in MAPPED_FIELDS}


def _model_fallback(fields: list[str], header: Sequence[str], provider: Provider,
                    scrub: Callable[[str], str]) -> dict[str, int]:
    """Ask the provider about `fields`. The payload is the prompt file plus `fields` and the
    header cells; a reply is used only where it names exactly one shown cell, used once."""
    cells = [scrub(h) for h in header]
    prompt = PROMPT.read_text(encoding="utf-8") + "\n" + json.dumps(
        {"fields": fields, "header": cells}, ensure_ascii=False)
    try:
        raw = provider.act(prompt, schema=MappingReply, prompt_file=PROMPT.name)
        reply = MappingReply.model_validate(raw.model_dump() if hasattr(raw, "model_dump") else raw)
    except (ValidationError, ValueError, TypeError, ProviderError):
        return {}
    chosen = {f: cells.index(c) for f, c in reply.matches.items()
              if f in fields and c is not None and cells.count(c) == 1}
    used = list(chosen.values())
    return {f: i for f, i in chosen.items() if used.count(i) == 1}


def propose_mapping(header: Sequence[str], *, provider: Provider | None = None,
                    scrub: Callable[[str], str] = lambda s: s) -> ColumnMapping:
    """A `proposed` mapping from the header row alone. Reads no data row, touches no sheet."""
    found = _candidates(header)
    claims: dict[int, list[str]] = {}
    for field, indexes in found.items():
        if len(indexes) == 1:
            claims.setdefault(indexes[0], []).append(field)
    chosen = {fs[0]: i for i, fs in claims.items() if len(fs) == 1}
    open_fields = [f for f in MAPPED_FIELDS if f not in chosen and not found[f]]
    if provider is not None and open_fields:
        taken = set(chosen.values())
        chosen |= {f: i for f, i in _model_fallback(open_fields, header, provider, scrub).items()
                   if i not in taken}
    unmapped = {f: [header[i] for i in found[f]] for f in MAPPED_FIELDS if f not in chosen}
    return ColumnMapping(columns={f: header[i] for f, i in chosen.items()},
                         positions=dict(chosen), unmapped=unmapped)


def confirm_mapping(binding: TrackerBinding, user: str, holds_project_edit: HoldsProjectEdit,
                    now: datetime) -> TrackerBinding:
    """Confirm the proposed mapping as `user`. Refused (binding unchanged) for a user without
    `project.edit`, a stale mapping, or one with no bug-key column (rows are located by it)."""
    if not holds_project_edit(user, binding.project):
        raise NotAllowed(f"{user!r} does not hold project.edit on {binding.project!r}")
    mapping = binding.mapping
    if mapping.status is MappingStatus.STALE:
        raise MappingNotConfirmed("the header changed: propose again from the current header")
    if "bug_key" not in mapping.columns:
        raise MappingNotConfirmed("the bug_key column is unmapped: rows are located by it")
    data = mapping.model_dump() | {"status": MappingStatus.CONFIRMED, "confirmed_by": user,
                                   "confirmed_at": now}
    return binding.model_copy(update={"mapping": ColumnMapping.model_validate(data)})


def _moved(mapping: ColumnMapping, header: Sequence[str]) -> bool:
    for field, name in mapping.columns.items():
        at = mapping.positions.get(field, -1)
        if not 0 <= at < len(header) or header[at] != name:
            return True
    return False


def check_header(binding: TrackerBinding, header: Sequence[str]) -> TrackerBinding:
    """Age the mapping against the sheet's current header: if any mapped column is no longer at
    its recorded position under its recorded name, the mapping is `stale`."""
    if binding.mapping.status is MappingStatus.STALE or not _moved(binding.mapping, header):
        return binding
    stale = binding.mapping.model_copy(update={"status": MappingStatus.STALE})
    return binding.model_copy(update={"mapping": stale})


def rebind(binding: TrackerBinding, *, sheet_id: str | None = None,
           tab: str | None = None) -> TrackerBinding:
    """Point the binding at another sheet or tab. The mapping goes back to `proposed` and the
    first-write confirmation is dropped: a new target is confirmed again (TB13, TB9)."""
    if sheet_id in (None, binding.sheet_id) and tab in (None, binding.tab):
        return binding
    old = binding.mapping
    fresh = ColumnMapping(columns=old.columns, positions=old.positions, unmapped=old.unmapped)
    return TrackerBinding(project=binding.project, sheet_id=sheet_id or binding.sheet_id,
                          tab=tab or binding.tab, mapping=fresh)


def mapping_columns(binding: TrackerBinding) -> SheetColumns:
    """The columns a write may use. Every write path comes through here and it asserts
    `confirmed` (TB8). `date` is written as `first_seen`; `screenshot_link` is not written."""
    if binding.mapping.status is not MappingStatus.CONFIRMED:
        raise MappingNotConfirmed(f"the mapping is {binding.mapping.status.value}, not confirmed")
    rename = {"date": "first_seen"}
    cols = {rename.get(f, f): h for f, h in binding.mapping.columns.items()
            if f != "screenshot_link"}
    return SheetColumns(sheet_id=binding.sheet_id, tab=binding.tab, columns=cols)
