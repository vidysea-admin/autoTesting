"""AT-1304: a short numeric secret must not corrupt trace.jsonl (T-136 live r3, D4).

The live run declared AUTOTESTER_SMTP_PORT=587; `TraceWriter` scrubbed the ENCODED line, so a
latency of 0.587 became `0.[REDACTED]:...`, the line stopped being JSON and every failure bundle
was `assembly_failed`. Strings must still be scrubbed (core-invariants redaction), numbers and
timestamps must survive. Offline: a temp dir, no browser, network or model.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from autotester.core.redact import Redactor
from autotester.core.trace import TraceParseError, TraceWriter, read_spans
from autotester.schema.run_state import StageCheckpoint, StageName
from autotester.schema.trace import LLMSpan, StageSpan

KEY = "AUTOTESTER_SMTP_PORT"


def _writer(tmp_path: Path, secret: str = "587", key: str = KEY) -> TraceWriter:
    return TraceWriter(tmp_path / "trace.jsonl", "run-1", redactor=Redactor({key: secret}))


def _lines(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_smtp_port_587_secret_while_a_step_latency_is_0_587_stays_valid_json(tmp_path) -> None:
    w = _writer(tmp_path)
    w.record_llm(provider="mock:mock", role="judge", prompt_file="p.md", input_tokens=587,
                 output_tokens=5870, latency_s=0.587, retries=0, fallback_hops=0, fed_id=None)
    row = _lines(w.path)[0]  # json.loads must not raise
    assert row["latency_s"] == 0.587 and row["input_tokens"] == 587 and row["output_tokens"] == 5870
    span = read_spans(w.path)[0]
    assert isinstance(span, LLMSpan) and span.latency_s == 0.587 and span.input_tokens == 587


def test_a_timestamp_containing_the_secret_digits_still_parses(tmp_path) -> None:
    w = _writer(tmp_path)
    start = datetime(2026, 10, 19, 5, 58, 7, 587000, tzinfo=UTC)
    end = datetime(2026, 10, 19, 5, 58, 9, 587000, tzinfo=UTC)
    w.record_stage(StageCheckpoint(stage=StageName.EXECUTE, status="done",
                                   started=start, finished=end))
    span = read_spans(w.path)[0]
    assert isinstance(span, StageSpan)
    assert (span.started, span.finished, span.duration_s) == (start, end, 2.0)


def test_string_fields_are_still_scrubbed_with_the_same_numeric_secret(tmp_path) -> None:
    w = _writer(tmp_path)
    w.record_llm(provider="mock:mock", role="judge", prompt_file=None, input_tokens=1,
                 output_tokens=1, latency_s=0.587, retries=0, fallback_hops=0,
                 fed_id="case-587-x")
    w.record_stage(StageCheckpoint(stage=StageName.EXECUTE, status="failed",
                                   error="smtp refused on port 587"))
    llm, stage = _lines(w.path)
    assert llm["fed_id"] == f"case-[REDACTED]:{KEY}-x"
    assert stage["error"] == f"smtp refused on port [REDACTED]:{KEY}"
    assert llm["latency_s"] == 0.587


def test_no_raw_long_secret_reaches_disk_even_with_json_special_characters(tmp_path) -> None:
    secret = 'pa"ss' + chr(92) + 'w0rd-Zq91'  # a quote and a backslash: JSON escapes both
    w = _writer(tmp_path, secret=secret, key="APP_PASSWORD")
    w.record_stage(StageCheckpoint(stage=StageName.EXECUTE, status="failed",
                                   error=f"login rejected for {secret}"))
    raw = w.path.read_text(encoding="utf-8")
    assert secret not in raw and json.dumps(secret)[1:-1] not in raw
    assert _lines(w.path)[0]["error"] == "login rejected for [REDACTED]:APP_PASSWORD"


def test_the_assert_clean_gate_still_refuses_a_line_scrub_failed_to_mask(tmp_path) -> None:
    class BrokenScrub(Redactor):
        def scrub(self, text: str) -> str:  # a regression that masks nothing
            return text

    w = TraceWriter(tmp_path / "trace.jsonl", "run-1",
                    redactor=BrokenScrub({"APP_PASSWORD": "sk-fake-9f2c7a1b"}))
    with pytest.raises(ValueError, match="raw secret"):
        w.record_stage(StageCheckpoint(stage=StageName.EXECUTE, status="failed",
                                       error="boom sk-fake-9f2c7a1b"))
    assert not w.path.exists()


def test_an_unparseable_trace_line_names_the_file_and_line(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    good = StageSpan(trace_id="r", stage=StageName.EXECUTE, status="done").model_dump_json()
    path.write_text(good + '\n{"latency_s":0.[REDACTED]:X}\n', encoding="utf-8")
    with pytest.raises(TraceParseError, match=r"trace\.jsonl:2"):
        read_spans(path)
