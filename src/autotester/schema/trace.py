"""Trace-span shapes for the redacted per-run trace.jsonl (D-041 phase 1,
qa/contracts/run-trace.md).

Two spans: one per finished pipeline-stage transition (`StageSpan`, RT3) and
one per LLM call (`LLMSpan`, RT4). `core/trace.py::TraceWriter` is the only
writer of either shape (RT5); this module only defines what a line looks
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
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    cost: float = 0.0
    retries: int = 0
    fallback_hops: int = 0
    fed_id: str | None = Field(default=None, description="case or verdict id this call fed")
    recorded_at: datetime = Field(default_factory=utc_now)
