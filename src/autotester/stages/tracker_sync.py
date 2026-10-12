"""TRACKER SYNC: the dry-run preview, the first-write confirmation and the outage rule.

Its one job is the layer between a project's `TrackerBinding` and `stages/sheet_write.py` (T-199c;
TB9, TB12, TB13). Nothing here can write by itself:
  - `preview_sync` reads the sheet and plans; it never calls a write method;
  - `confirm_first_write` records who confirmed which plan hash, for a holder of `project.edit`;
  - `sync_confirmed` hands a confirmed, fresh plan to `write_confirmed_plan`, which still refuses
    a live client. The only client in this repo is a test fake.
A sheet error is never a run failure (TB12): both entry points catch it, set `sync_status=error`
with a scrubbed last error and a retry time, and return; the bug store is not touched, so the
in-product tracker stays authoritative. A refusal (`WriteRefused`, `MappingNotConfirmed`) is a
decision, not an outage, and is raised.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Protocol
from urllib.parse import parse_qsl, urlsplit

from autotester.schema.sheet_plan import PlanConfirmation, SheetPlan
from autotester.schema.tracked_bug import TrackedBug
from autotester.schema.tracker_binding import ConflictNote, SyncState, TrackerBinding
from autotester.stages.sheet_plan import Scrub, plan_sync, render_plan
from autotester.stages.sheet_write import SheetClient, WriteRefused, write_confirmed_plan
from autotester.stages.tracker_mapping import (
    HoldsProjectEdit,
    MappingNotConfirmed,
    NotAllowed,
    check_header,
    mapping_columns,
)


class TrackerClient(SheetClient, Protocol):
    """A `SheetClient` that can also read the header row alone (a mapping needs no data row)."""

    def read_header(self, sheet_id: str, tab: str) -> list[str]: ...


RETRY_AFTER = timedelta(minutes=15)
_SIGNED = ("sig", "signature", "token", "expires", "x-amz-signature", "x-goog-signature",
           "access_token", "key")


def _outage(binding: TrackerBinding, exc: Exception, scrub: Scrub, now: datetime) -> TrackerBinding:
    """The binding after a sheet error. The error text is scrubbed before it is stored."""
    text = scrub(f"{type(exc).__name__}: {exc}")[:500]
    state = SyncState(sync_status="error", last_error=text, last_attempt_at=now,
                      retry_at=now + RETRY_AFTER, conflicts=binding.sync.conflicts)
    return binding.model_copy(update={"sync": state})


def _after_plan(binding: TrackerBinding, plan: SheetPlan, now: datetime, *,
                written: bool) -> TrackerBinding:
    notes = [ConflictNote(bug_key=r.bug_key, column=c.column, sheet_has=c.sheet_has)
             for r in plan.rows for c in r.conflicts]
    state = SyncState(sync_status="ok", last_attempt_at=now, plan_hash=plan.plan_hash,
                      rows_planned=len(plan.writes), conflicts=notes, written=written)
    return binding.model_copy(update={"sync": state})


def preview_sync(binding: TrackerBinding, client: TrackerClient, bugs: Iterable[TrackedBug],
                 scrub: Scrub, now: datetime) -> tuple[TrackerBinding, SheetPlan | None, str]:
    """The dry run: (binding with the outcome, the plan or None, the rendering). Reads only; a
    stale header marks the mapping stale and no plan is made. Never raises for a sheet error."""
    try:
        binding = check_header(binding, client.read_header(binding.sheet_id, binding.tab))
        cols = mapping_columns(binding)
        state = client.read(cols.sheet_id, cols.tab)
        plan = plan_sync(bugs, state, cols, binding.memory, scrub)
    except MappingNotConfirmed as exc:
        return binding, None, f"No plan: {exc}. Nothing has been written."
    except Exception as exc:  # a sheet outage is not a run failure (TB12)
        gone = "Sheet unavailable. Nothing has been written."
        return _outage(binding, exc, scrub, now), None, gone
    return _after_plan(binding, plan, now, written=False), plan, scrub(render_plan(plan))


def confirm_first_write(binding: TrackerBinding, plan: SheetPlan, user: str,
                        holds_project_edit: HoldsProjectEdit, now: datetime) -> TrackerBinding:
    """Record that `user` saw this exact plan (TB9). Bound to the plan hash, the sheet and tab:
    a changed plan or target needs a new confirmation. Writes nothing."""
    if not holds_project_edit(user, binding.project):
        raise NotAllowed(f"{user!r} does not hold project.edit on {binding.project!r}")
    if (plan.sheet_id, plan.tab) != (binding.sheet_id, binding.tab):
        raise WriteRefused("the plan is for another sheet or tab than the binding")
    confirmation = PlanConfirmation(plan_hash=plan.plan_hash, confirmed_by=user, confirmed_at=now)
    return binding.model_copy(update={"first_write": confirmation})


def sync_confirmed(binding: TrackerBinding, client: TrackerClient, bugs: Iterable[TrackedBug],
                   scrub: Scrub, now: datetime) -> TrackerBinding:
    """Write the plan the binding's confirmation covers, via `write_confirmed_plan` (which also
    refuses a live client). Needs a confirmed, fresh mapping. A refusal raises with zero writes; a
    sheet error becomes `sync_status=error` and the next call converges (TB11, TB12)."""
    try:
        binding = check_header(binding, client.read_header(binding.sheet_id, binding.tab))
        cols = mapping_columns(binding)
        plan = write_confirmed_plan(client, bugs, cols, binding.memory, scrub, binding.first_write)
    except WriteRefused:
        raise
    except MappingNotConfirmed:
        raise
    except Exception as exc:
        return _outage(binding, exc, scrub, now)
    return _after_plan(binding, plan, now, written=True)


def check_link(url: str, product_host: str) -> str:
    """A screenshot link may go into a sheet only if it is an https link on the product's own
    host with no signed-URL parameter (TB13): opening it needs a sign-in. Returns the url."""
    parts = urlsplit(url)
    if parts.scheme != "https" or (parts.hostname or "") != product_host.lower():
        raise ValueError("a link must be https on the product's own host")
    if any(k.lower() in _SIGNED for k, _ in parse_qsl(parts.query)):
        raise ValueError("a signed URL works without sign-in and may not be written")
    return url
