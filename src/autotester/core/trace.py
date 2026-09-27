"""The redacted per-run trace: `TraceWriter` appends one JSON line per stage
transition and per LLM call to `trace.jsonl` (D-041 phase 1,
qa/contracts/run-trace.md RT1-RT6); `read_spans` reads it back for the
run-view UI panel (RT7) -- a VIEW over the file, never a second store
(core-invariants C6).
"""

from __future__ import annotations

import json
from pathlib import Path

from autotester.core.pricing import estimate_cost
from autotester.core.redact import Redactor
from autotester.schema.run_state import StageCheckpoint
from autotester.schema.trace import LLMSpan, StageSpan


class TraceWriter:
    """One writer per run. `trace_id` is always the run's own
    `RunState.run_id` (RT2) -- construct with it once, never re-mint it."""

    def __init__(self, path: Path, trace_id: str, redactor: Redactor | None = None) -> None:
        self.path = path
        self.trace_id = trace_id
        self._redactor = redactor or Redactor({})

    def _append(self, line: str) -> None:
        """RT6: every span passes through `scrub` then the `assert_clean`
        hard gate before it touches disk -- in that order, on every line."""
        clean = self._redactor.scrub(line)
        self._redactor.assert_clean(clean)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(clean + "\n")

    def record_stage(self, checkpoint: StageCheckpoint) -> None:
        """RT3: one span for a finished `StageCheckpoint`."""
        duration = None
        if checkpoint.started is not None and checkpoint.finished is not None:
            duration = (checkpoint.finished - checkpoint.started).total_seconds()
        span = StageSpan(
            trace_id=self.trace_id, stage=checkpoint.stage, status=checkpoint.status,
            started=checkpoint.started, finished=checkpoint.finished, duration_s=duration,
        )
        self._append(span.model_dump_json())

    def record_llm(
        self, *, provider: str, role: str, prompt_file: str | None,
        input_tokens: int, output_tokens: int, latency_s: float,
        retries: int, fallback_hops: int, fed_id: str | None,
    ) -> None:
        """RT4/RT5: the only site an LLM-call span is appended -- called
        exclusively from `Provider.record()`, never by a stage directly."""
        span = LLMSpan(
            trace_id=self.trace_id, provider=provider, role=role, prompt_file=prompt_file,
            input_tokens=input_tokens, output_tokens=output_tokens, latency_s=latency_s,
            cost=estimate_cost(provider, input_tokens, output_tokens),
            retries=retries, fallback_hops=fallback_hops, fed_id=fed_id,
        )
        self._append(span.model_dump_json())


def read_spans(path: Path) -> list[StageSpan | LLMSpan]:
    """RT7: parse `trace.jsonl` back into spans for the run-view panel -- a
    VIEW over the file. A run with no trace yet returns an empty list, never
    an error."""
    if not path.exists():
        return []
    spans: list[StageSpan | LLMSpan] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if raw.get("kind") == "llm_call":
            spans.append(LLMSpan.model_validate(raw))
        else:
            spans.append(StageSpan.model_validate(raw))
    return spans
