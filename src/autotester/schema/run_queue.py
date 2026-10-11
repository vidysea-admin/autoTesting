"""One Test press waiting for, holding, or having had a browser slot (T-203, hosting.md HO16).

`id` is the run id the press will produce, so the queue row, the run directory and the report
link share one name. `reason` is a human sentence for `refused`/`interrupted` and only the
exception CLASS for `failed` (a message may carry a secret).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.case import CasePriority


class QueueStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    REFUSED = "refused"          # a gate (credentials, consent, permission) said no at start
    INTERRUPTED = "interrupted"  # the server died mid-run; never re-executed automatically


ACTIVE = (QueueStatus.QUEUED, QueueStatus.RUNNING)


class QueueEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project: str
    status: QueueStatus = QueueStatus.QUEUED
    trigger: Literal["button", "schedule", "api"] = "button"
    requested_by: str | None = Field(None, description="who pressed it; None before login exists")
    priorities: list[CasePriority] | None = Field(
        None, description="T-178 FB4: run these priorities plus pinned p0; None runs every case")
    enqueued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    reason: str | None = None
    position: int = Field(0, description="1-based place among the queued; derived, never stored")


class RunQueueFile(BaseModel):
    """The on-disk form (`<data root>/.work/run_queue.json`)."""

    model_config = ConfigDict(extra="forbid")

    entries: list[QueueEntry] = Field(default_factory=list)
