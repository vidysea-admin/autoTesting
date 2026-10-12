"""Fakes for the scheduler tests: a file-backed run queue standing in for T-203's.

File-backed so two OS processes (spawn context, same on Windows) can share it. The queue is
NOT the unit under test: `idempotent=False` makes it a worst case (every enqueue adds an
entry), so a test that counts one entry proves the scheduler's own claim did the work.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from autotester.schema.schedule import ScheduleConfig
from autotester.stages.scheduler import QueueSnapshot, Slot, TickDeps


class FakeQueue:
    def __init__(self, root: Path, *, idempotent: bool = False) -> None:
        self.root = root
        self.idempotent = idempotent
        root.mkdir(parents=True, exist_ok=True)

    def entries(self) -> list[dict]:
        return [json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(self.root.glob("*.json"))]

    def __len__(self) -> int:
        return len(self.entries())

    def enqueue(self, project: str) -> Callable[[Slot], str]:
        def _enqueue(slot: Slot) -> str:
            if self.idempotent:
                for e in self.entries():
                    if e["slot_key"] == slot.key:
                        return str(e["id"])
            entry = {"id": uuid.uuid4().hex[:8], "project": project, "slot_key": slot.key,
                     "active": True}
            fd = os.open(self.root / f"{entry['id']}.json",
                         os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(entry))
            return str(entry["id"])
        return _enqueue

    def add_running(self, project: str, entry_id: str = "busy1") -> None:
        (self.root / f"{entry_id}.json").write_text(json.dumps(
            {"id": entry_id, "project": project, "slot_key": None, "active": True}),
            encoding="utf-8")

    def finish(self, entry_id: str) -> None:
        p = self.root / f"{entry_id}.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["active"] = False
        p.write_text(json.dumps(data), encoding="utf-8")

    def snapshots(self) -> list[QueueSnapshot]:
        return [QueueSnapshot(id=e["id"], project=e["project"], active=e["active"],
                              slot_key=e["slot_key"]) for e in self.entries()]


def make_deps(base: Path, project: str, *, idempotent: bool = False,
              scrub: Callable[[str], str] | None = None,
              gate: Callable[[Slot], str | None] | None = None) -> tuple[TickDeps, FakeQueue]:
    q = FakeQueue(base / "queue", idempotent=idempotent)
    deps = TickDeps(
        claim_dir=base / "claims", records_path=base / "records.jsonl",
        enqueue=q.enqueue(project), queue=q.snapshots,
        gate=gate or (lambda slot: None), scrub=scrub or (lambda text: text))
    return deps, q


def utc(*a: int) -> datetime:
    return datetime(*a, tzinfo=UTC)


def daily(at: str = "09:00", tz: str = "UTC") -> ScheduleConfig:
    return ScheduleConfig.model_validate(
        {"mode": "fixed", "fixed_at": at, "timezone": tz, "owner": "u1"})


def one_offs(*stamps: str) -> ScheduleConfig:
    return ScheduleConfig.model_validate(
        {"mode": "custom", "owner": "u1", "one_offs": list(stamps)})
