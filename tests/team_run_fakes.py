"""Shared fakes for the Test-button tests (T-201b, qa/contracts/team-test-button.md TT1-TT6).

Everything a press could touch is counted, so "no trace" is an assertion and not a hope:
`Counters.sessions` (a browser was built), `Counters.graded` (a case reached the grader, the
only thing in a run that talks to a model), the data-root file listing (no run directory, no
queue file, no approval row), and a fake queue that records every entry it was handed.
No real browser, no real model, no mail and no network is reachable from here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

import pytest
from run_approval_fixture import grant_live_case_approval

from autotester.browser.session import BrowserSession
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef
from autotester.schema.run import RawResult
from autotester.schema.run_queue import ACTIVE, QueueEntry, QueueStatus
from autotester.schema.team_enums import RunVia
from autotester.schema.verdict import Verdict
from autotester.store.project_store import ProjectStore


class Counters:
    sessions = 0
    graded = 0


class _Judge:
    trace = None

    def __init__(self, project: Project) -> None:
        self.project = project

    def available(self) -> bool:
        return True


def patch_run_world(monkeypatch: pytest.MonkeyPatch) -> type[Counters]:
    """A run reaches a fake browser and a fake grader that count themselves."""
    import autotester.ui.routes_runs as routes_runs
    import autotester.ui.run_execution as run_execution

    Counters.sessions = Counters.graded = 0
    original_init = BrowserSession.__init__

    def counting_init(self, *args, **kwargs):
        Counters.sessions += 1
        original_init(self, *args, **kwargs)

    def graded(case_, session, judge, run_id, store_):
        Counters.graded += 1
        return (RawResult(case_id=case_.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                        grader_provider="mock"))

    monkeypatch.setattr(BrowserSession, "__init__", counting_init)
    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)
    monkeypatch.setattr(run_execution, "run_and_grade_case_resilient", graded)
    monkeypatch.setattr(routes_runs, "for_role", lambda project, role: _Judge(project))
    return Counters


def runnable_project(root: Path, slug: str, *, credential: str | None = None,
                     value: str | None = None, approved: bool = False) -> ProjectStore:
    """A project with one case. `credential` declares that key (and the case types it);
    `value` provisions it in the root `.env`; `approved` adds a human live-case approval."""
    refs = [SecretRef(key=credential, domains=[f"{slug}.test"])] if credential else []
    store = ProjectStore(slug, root)
    store.save_project(Project(slug=slug, name=slug.title(), base_url=f"https://{slug}.test",
                               allowed_domains=[f"{slug}.test"], secrets=refs))
    steps = [Step(order=1, action=Action.NAVIGATE, target=f"https://{slug}.test/")]
    if credential:
        steps.append(Step(order=2, action=Action.FILL, target="#user",
                          value="{{SECRET:" + credential + "}}"))
    store.add_case(Case(project=slug, flow_id="flow-home", kind=CaseKind.BEST,
                        case_class=CaseClass.HAPPY, title="Home loads", steps=steps))
    if value is not None:
        env = root / ".env"
        old = env.read_text(encoding="utf-8") if env.exists() else ""
        env.write_text(f"{old}{credential}={value}\n", encoding="utf-8")
    if approved:
        grant_live_case_approval(store, project=slug, target=f"https://{slug}.test")
    return store


def listing(root: Path) -> dict[str, bytes]:
    """Every file under the data root except the login store and the audit trail, which a
    signed-in refusal is SUPPOSED to append to (AU22). Anything else changing is a trace."""
    skip = {".auth", "audit.jsonl"}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file() and not skip & set(p.relative_to(root).parts)}


class Submitted(NamedTuple):
    project: str
    requested_by: str | None
    via: RunVia | None
    trigger: str


class FakeQueue:
    """The queue interface the button uses (HO16): `submit`, `snapshot`, `get`, the six
    statuses. It never runs anything by itself: a test calls `start_next` / `finish`. `cap` and
    the per-project single flight are modelled so a test can observe concurrency."""

    def __init__(self, cap: int = 2) -> None:
        self.cap = cap
        self.entries: list[QueueEntry] = []
        self.submitted: list[Submitted] = []
        self.max_running = 0

    def submit(self, project: str, *, requested_by: str | None = None, trigger: str = "button",
               run_id: str | None = None, priorities=None, via: RunVia | None = None,
               slot_key: str | None = None, requested_by_id: int | None = None) -> QueueEntry:
        self.submitted.append(Submitted(project, requested_by, via, trigger))
        entry = QueueEntry(id=run_id or f"run-fake{len(self.entries)}", project=project,
                           requested_by=requested_by, requested_by_id=requested_by_id,
                           trigger=trigger, via=via, enqueued_at=datetime.now(UTC))
        self.entries.append(entry)
        return self.get(entry.id)

    def snapshot(self, project: str | None = None) -> list[QueueEntry]:
        queued = [e for e in self.entries if e.status is QueueStatus.QUEUED]
        return [e.model_copy(update={"position": queued.index(e) + 1 if e in queued else 0})
                for e in self.entries if project in (None, e.project)]

    def get(self, entry_id: str) -> QueueEntry:
        return next(e for e in self.snapshot() if e.id == entry_id)

    def start_next(self) -> QueueEntry | None:
        running = [e for e in self.entries if e.status is QueueStatus.RUNNING]
        busy = {e.project for e in running}
        nxt = next((e for e in self.entries if e.status is QueueStatus.QUEUED
                    and e.project not in busy), None)
        if nxt is None or len(running) >= self.cap:
            return None
        nxt.status = QueueStatus.RUNNING
        self.max_running = max(self.max_running, len(running) + 1)
        return nxt

    def finish(self, entry_id: str, status: QueueStatus = QueueStatus.DONE,
               reason: str | None = None) -> None:
        entry = next(e for e in self.entries if e.id == entry_id)
        entry.status, entry.reason = status, reason

    def active(self) -> list[QueueEntry]:
        return [e for e in self.entries if e.status in ACTIVE]
