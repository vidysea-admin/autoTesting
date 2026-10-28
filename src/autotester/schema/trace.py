"""Trace-span shapes for the redacted per-run trace.jsonl (D-041 phase 1,
qa/contracts/run-trace.md).

Spans: one per finished pipeline-stage transition (`StageSpan`, RT3), one per
LLM call (`LLMSpan`, RT4) and one per timed run phase (`PhaseSpan`, the
teardown-stall diagnosis). `core/trace.py::TraceWriter` is the only
writer of any shape (RT5); this module only defines what a line looks
like, so a reader (the UI panel, RT7) and a writer always agree on the shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.base import utc_now
from autotester.schema.run_state import StageName, StageStatus


class StageSpan(BaseModel):
    """One finished `StageCheckpoint` (RT3) — `trace_id` is always the run's
    own `RunState.run_id` (RT2), never a freshly minted id."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["stage"] = "stage"
    trace_id: str
    stage: StageName
    status: StageStatus
    error: str | None = None
    started: datetime | None = None
    finished: datetime | None = None
    duration_s: float | None = None
    recorded_at: datetime = Field(default_factory=utc_now)


class LLMSpan(BaseModel):
    """One call through `Provider.see_video`/`act`/`judge` (RT4), recorded at
    the single choke point `Provider.record()` (RT5)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["llm_call"] = "llm_call"
    trace_id: str
    provider: str = Field(description="Provider.label -- 'id:model'")
    role: str
    prompt_file: str | None = None
    input_tokens: int | None = 0
    output_tokens: int | None = 0
    latency_s: float = 0.0
    failed: bool = False
    cost: float | None = 0.0
    retries: int = 0
    fallback_hops: int = 0
    fed_id: str | None = Field(default=None, description="case or verdict id this call fed")
    recorded_at: datetime = Field(default_factory=utc_now)


class ToolSpan(BaseModel):
    """One agent-layer step (T-179 AL5): a lead planning step, a tool call, or a delegation to a
    subagent. Same file, same `trace_id` (the run's own id, RT2/RT5); a tool or delegation points
    at the planning step that asked for it through `parent_seq`."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool"] = "tool"
    trace_id: str
    seq: int = Field(ge=0, description="order of this span within the lead loop")
    op: Literal["plan", "tool", "delegate"]
    name: str = Field(description="tool name, subagent name, or 'lead' for a planning step")
    ok: bool = True
    refusal: str | None = None
    parent_seq: int | None = None
    duration_s: float = 0.0
    recorded_at: datetime = Field(default_factory=utc_now)


class PhaseSpan(BaseModel):
    """One timed phase of a run (entry-profile wipe, session start/close, OCR, video finalise,
    save, a failed judge tier). Records WHERE wall time went so a silent multi-minute gap is a
    number, not a mystery. `nested=True` marks a phase that happens INSIDE another recorded
    phase (so `unaccounted_s` never counts its time twice)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["phase"] = "phase"
    trace_id: str
    case_id: str | None = None
    phase: str
    started: datetime
    finished: datetime
    duration_s: float = Field(ge=0.0)
    ok: bool = True
    nested: bool = False
    note: str | None = None
    recorded_at: datetime = Field(default_factory=utc_now)
