"""The redacted per-run trace: `TraceWriter` appends one JSON line per stage
transition and per LLM call to `trace.jsonl` (D-041 phase 1,
qa/contracts/run-trace.md RT1-RT6); `read_spans` reads it back for the
run-view UI panel (RT7) -- a VIEW over the file, never a second store
(core-invariants C6).
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter

from autotester.core.pricing import estimate_cost
from autotester.core.redact import Redactor
from autotester.schema.base import utc_now
from autotester.schema.run_state import StageCheckpoint
from autotester.schema.trace import LLMSpan, PhaseSpan, StageSpan, ToolSpan
from autotester.store.filestore import append_path
from autotester.store.filestore_paths import read_text_path

SLOW_PHASE_S = 30.0
"""A phase longer than this prints one stderr line, so a stall is visible while it happens."""

_LINE = TypeAdapter(dict[str, Any])  # encodes datetimes/enums exactly as model_dump_json


class TraceParseError(ValueError):
    """A `trace.jsonl` line that is not JSON; the message names the file and 1-based line,
    never the line's content (AT-1304 C3)."""


class TraceWriter:
    """One writer per run. `trace_id` is always the run's own
    `RunState.run_id` (RT2) -- construct with it once, never re-mint it."""

    def __init__(self, path: Path, trace_id: str, redactor: Redactor | None = None) -> None:
        self.path = path
        self.trace_id = trace_id
        self._redactor = redactor or Redactor({})

    def _scrub_value(self, value: Any) -> Any:
        """Mask secrets in the STRING values only. Numbers and timestamps are never text, so
        a short numeric secret (SMTP port 587) cannot edit a latency of 0.587 (AT-1304).
        Enum members are the fixed stage/status vocabulary, not free text."""
        if isinstance(value, Enum):
            return value
        if isinstance(value, str):
            clean = self._redactor.scrub(value)
            self._redactor.assert_clean(clean)
            return clean
        if isinstance(value, dict):
            return {k: self._scrub_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._scrub_value(v) for v in value]
        return value

    def _append(self, span: BaseModel) -> None:
        """RT6: every string in a span passes through `scrub` then the `assert_clean`
        hard gate BEFORE JSON encoding -- structurally, so the encoded line is always valid
        JSON and a JSON escape (quote, backslash) cannot hide a secret from the scrub."""
        clean = _LINE.dump_json(self._scrub_value(span.model_dump(mode="python"))).decode("utf-8")
        append_path(self.path, clean + "\n")

    def record_stage(self, checkpoint: StageCheckpoint) -> None:
        """RT3: one span for a finished `StageCheckpoint`."""
        duration = None
        if checkpoint.started is not None and checkpoint.finished is not None:
            duration = (checkpoint.finished - checkpoint.started).total_seconds()
        span = StageSpan(
            trace_id=self.trace_id, stage=checkpoint.stage, status=checkpoint.status,
            error=checkpoint.error,
            started=checkpoint.started, finished=checkpoint.finished, duration_s=duration,
        )
        self._append(span)

    def record_llm(
        self, *, provider: str, role: str, prompt_file: str | None,
        input_tokens: int | None, output_tokens: int | None, latency_s: float,
        retries: int, fallback_hops: int, fed_id: str | None, failed: bool = False,
    ) -> None:
        """RT4/RT5: the only site an LLM-call span is appended -- called
        exclusively from `Provider.record()`, never by a stage directly."""
        span = LLMSpan(
            trace_id=self.trace_id, provider=provider, role=role, prompt_file=prompt_file,
            input_tokens=input_tokens, output_tokens=output_tokens, latency_s=latency_s,
            cost=(None if input_tokens is None or output_tokens is None
                  else estimate_cost(provider, input_tokens, output_tokens)),
            retries=retries, fallback_hops=fallback_hops, fed_id=fed_id, failed=failed,
        )
        self._append(span)

    def record_tool(self, *, seq: int, op: str, name: str, ok: bool = True,
                    refusal: str | None = None, parent_seq: int | None = None,
                    duration_s: float = 0.0) -> None:
        """AL5: one span per lead planning step, tool call and delegation -- on this same
        writer and file, never a second trace (RT5)."""
        span = ToolSpan(trace_id=self.trace_id, seq=seq, op=op, name=name, ok=ok,  # type: ignore[arg-type]
                        refusal=refusal, parent_seq=parent_seq, duration_s=duration_s)
        self._append(span)

    def record_phase(self, *, phase: str, started_mono: float, case_id: str | None = None,
                     ok: bool = True, nested: bool = False, note: str | None = None) -> None:
        """One timed phase, measured on the monotonic clock from `started_mono` to now."""
        duration = max(0.0, time.monotonic() - started_mono)
        finished = utc_now()
        self._append(PhaseSpan(
            trace_id=self.trace_id, case_id=case_id, phase=phase, ok=ok, nested=nested,
            note=note, started=finished - timedelta(seconds=duration), finished=finished,
            duration_s=duration))
        if duration > SLOW_PHASE_S:
            print(f"slow phase: {phase} {duration:.0f}s", file=sys.stderr)


@contextmanager
def traced_phase(trace: TraceWriter | None, case_id: str | None, phase: str, *,
                 nested: bool = False) -> Iterator[None]:
    """Time the block as one `PhaseSpan` (ok=False when it raises; the error propagates).
    A no-op when `trace` is None, so untraced use costs nothing."""
    started, ok = time.monotonic(), True
    try:
        yield
    except BaseException:
        ok = False
        raise
    finally:
        if trace is not None:
            trace.record_phase(phase=phase, started_mono=started, case_id=case_id, ok=ok,
                               nested=nested)


def read_tool_spans(path: Path) -> list[ToolSpan]:
    """The agent-layer lines of `trace.jsonl`, in order; no trace yet returns an empty list."""
    text = read_text_path(path)
    if text is None:
        return []
    rows = (json.loads(line) for line in text.splitlines() if line.strip())
    return [ToolSpan.model_validate(r) for r in rows if r.get("kind") == "tool"]


def read_spans(
    path: Path, *, include_phases: bool = False,
) -> list[StageSpan | LLMSpan | PhaseSpan]:
    """RT7: parse `trace.jsonl` back into spans for the run-view panel -- a
    VIEW over the file. A run with no trace yet returns an empty list, never
    an error. Phase spans are returned only with `include_phases=True`, so the
    stage/LLM consumers (run view, failure bundle) see exactly what they always did."""
    text = read_text_path(path)
    if text is None:
        return []
    spans: list[StageSpan | LLMSpan | PhaseSpan] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TraceParseError(f"{path.name}:{number}: not valid JSON") from exc
        if raw.get("kind") == "tool":  # agent-layer spans: `read_tool_spans`
            continue
        if raw.get("kind") == "phase":
            if include_phases:
                spans.append(PhaseSpan.model_validate(raw))
            continue
        if raw.get("kind") == "llm_call":
            spans.append(LLMSpan.model_validate(raw))
        else:
            spans.append(StageSpan.model_validate(raw))
    return spans


def phase_summary(path: Path, wall_s: float) -> tuple[dict[str, float], float]:
    """`(phase_totals_s, unaccounted_s)` for a run: seconds per phase name, and the run's wall
    time minus every top-level phase (nested phases sit inside a top-level one).
    Never negative: parallel workers' phases overlap, so their sum can exceed the wall."""
    spans = read_spans(path, include_phases=True)
    totals: dict[str, float] = {}
    accounted = 0.0
    for span in spans:
        if isinstance(span, PhaseSpan):
            totals[span.phase] = round(totals.get(span.phase, 0.0) + span.duration_s, 3)
            accounted += 0.0 if span.nested else span.duration_s
    return totals, round(max(0.0, wall_s - accounted), 3)
