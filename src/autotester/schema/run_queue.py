"""One Test press waiting for, holding, or having had a browser slot (T-203, hosting.md HO16).

`id` is the run id the press will produce, so the queue row, the run directory and the report
link share one name. `reason` is a human sentence for `refused`/`interrupted` and only the
exception CLASS for `failed` (a message may carry a secret).
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.team_enums import QueueStatus, RunVia

ACTIVE = (QueueStatus.QUEUED, QueueStatus.RUNNING)
__all__ = ["ACTIVE", "QueueEntry", "QueueStatus", "RunQueueFile"]


class QueueEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project: str
    status: QueueStatus = QueueStatus.QUEUED
    trigger: RunVia = RunVia.BUTTON
    slot_key: str | None = None
    via: RunVia | None = None
    requested_by: str | None = Field(None, description="who pressed it; None before login exists")
    enqueued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    reason: str | None = None
    position: int = Field(0, description="1-based place among the queued; derived, never stored")


class RunQueueFile(BaseModel):
    """The on-disk form (`<data root>/.work/run_queue.json`)."""

    model_config = ConfigDict(extra="forbid")

    entries: list[QueueEntry] = Field(default_factory=list)
