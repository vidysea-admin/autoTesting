"""T-172 driver: the redacted per-run trace (qa/contracts/run-trace.md RT1-RT7,
D-041 phase 1).

Fully offline: mock stage runners and `MockProvider`, driven against a temp
project dir -- no browser, network, or model. Each RT row in the manifest
carries a single-hunk falsifying edit reproduced red->green.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.core.redact import Redactor
from autotester.core.trace import TraceWriter, read_spans
from autotester.providers.mock import MockProvider
from autotester.schema.enums import SourceKind
from autotester.schema.project import Project, SecretRef, Source
from autotester.schema.run_state import RunState, StageCheckpoint, StageName
from autotester.schema.trace import LLMSpan, StageSpan
from autotester.stages.orchestrate import StageContext, run_or_resume
from autotester.store.filestore import write_json
from autotester.store.project_store import ProjectStore
from autotester.ui.routes_report import _trace_card


def _store(tmp_path: Path) -> ProjectStore:
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    store.add_source(Source(project="demo", kind=SourceKind.VIDEO, path="/tmp/a.mp4",
                             sha256="sha-a"))
    return store


def _recorder(tmp_path: Path, name: str):
    calls = {"n": 0}
    path = tmp_path / f"{name}.txt"

    def _run(ctx: StageContext, prev_ref: str | None) -> str:
        calls["n"] += 1
        path.write_text(str(calls["n"]), encoding="utf-8")
        return str(path)

    return _run, calls, path


def _lines(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in raw if line.strip()]


# -- RT1 ---------------------------------------------------------------------

def test_two_runs_of_a_project_get_two_distinct_nonempty_trace_files(tmp_path: Path) -> None:
    store = _store(tmp_path)
    project = Project(slug="demo", name="D", base_url="https://demo.test")
    ingest, _, _ = _recorder(tmp_path, "a")
    ctx1 = StageContext(store=store, run_id="run_a", runners={StageName.INGEST: ingest})
    ctx2 = StageContext(store=store, run_id="run_b", runners={StageName.INGEST: ingest})

    run_or_resume(project, ctx1)
    run_or_resume(project, ctx2)

    trace_a = store.paths.run_trace("run_a")
    trace_b = store.paths.run_trace("run_b")
    assert trace_a != trace_b
    assert trace_a.exists() and trace_b.exists()
    assert trace_a.stat().st_size > 0
    assert trace_b.stat().st_size > 0


# -- RT2 -----------------------------------------------------------------

def test_every_span_trace_id_equals_the_runs_own_run_id(tmp_path: Path) -> None:
    store = _store(tmp_path)
    project = Project(slug="demo", name="D", base_url="https://demo.test")
    ingest, _, _ = _recorder(tmp_path, "a")
    ctx = StageContext(store=store, run_id="run_tid", runners={StageName.INGEST: ingest})

    run_or_resume(project, ctx)

    lines = _lines(store.paths.run_trace("run_tid"))
    assert lines, "expected at least one span"
    assert all(line["trace_id"] == "run_tid" for line in lines)


# -- RT3 -----------------------------------------------------------------

def test_a_run_produces_exactly_one_stage_span_per_stage_that_ran(tmp_path: Path) -> None:
    """A fixture run with stages [MODEL, EXECUTE, GRADE] -> exactly those three
    stage spans, in stage order, no others (a stage that never ran -- INGEST,
    DISCOVER, EXPAND, REPORT here -- produces no span)."""
    store = _store(tmp_path)
    project = Project(slug="demo", name="D", base_url="https://demo.test")
    run_id = "run_three"
    custom_stages = [StageName.MODEL, StageName.EXECUTE, StageName.GRADE]
    state = RunState(
        run_id=run_id, project_slug="demo", mode="explore", mode_reason="fixture",
        stages=[StageCheckpoint(stage=s) for s in custom_stages],
    )
    write_json(store.paths.run_dir(run_id) / "state.json", state)

    runners = {}
    for s in custom_stages:
        run_fn, _, _ = _recorder(tmp_path, s.value)
        runners[s] = run_fn
    ctx = StageContext(store=store, run_id=run_id, runners=runners)

    run_or_resume(project, ctx)

    spans = [s for s in read_spans(store.paths.run_trace(run_id)) if isinstance(s, StageSpan)]
    assert [s.stage for s in spans] == custom_stages
    assert all(s.status == "done" for s in spans)


def test_a_stage_that_never_ran_produces_no_span(tmp_path: Path) -> None:
    """The standard learn pipeline's INGEST runs; MODEL has no registered
    runner, so the walk stops there and produces no EXPAND/EXECUTE/etc span."""
    store = _store(tmp_path)
    project = Project(slug="demo", name="D", base_url="https://demo.test")
    ingest, _, _ = _recorder(tmp_path, "a")
    ctx = StageContext(store=store, run_id="run_stop", runners={StageName.INGEST: ingest})

    run_or_resume(project, ctx)

    spans = [s for s in read_spans(store.paths.run_trace("run_stop")) if isinstance(s, StageSpan)]
    assert [s.stage for s in spans] == [StageName.INGEST]


# -- RT4 -----------------------------------------------------------------

def test_a_fixture_stage_of_2_judge_calls_and_1_act_call_makes_3_llm_spans(
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "trace.jsonl"
    writer = TraceWriter(trace_path, "trace-xyz")
    provider = MockProvider(model="mock", responses={
        "agent": [{"steps": []}], "judge": [{"result": "PASS"}, {"result": "FAIL"}],
    })
    provider.trace = writer

    provider.act("do the thing", object, prompt_file="expand_case_v1.md", fed_id="flow-1")
    provider.judge("grade it", object, prompt_file="grade_v1.md", fed_id="case-1")
    provider.judge("grade it again", object, prompt_file="grade_v1.md", fed_id="case-2")

    spans = [s for s in read_spans(trace_path) if isinstance(s, LLMSpan)]
    assert len(spans) == 3
    assert [s.role for s in spans] == ["agent", "judge", "judge"]
    for span in spans:
        assert span.trace_id == "trace-xyz"
        assert span.provider == "mock:mock"
        assert span.prompt_file is not None
        assert span.fed_id is not None
        assert span.input_tokens > 0
        assert span.output_tokens > 0


# -- RT5 -----------------------------------------------------------------

def test_provider_base_record_is_the_only_site_that_appends_an_llm_span() -> None:
    """`grep -rn` for trace-span-append logic outside providers/base.py returns
    nothing (RT5, core-invariants C3)."""
    src = Path(__file__).resolve().parents[1] / "src" / "autotester"
    offenders = []
    for path in src.rglob("*.py"):
        if path.name == "base.py" and path.parent.name == "providers":
            continue
        if path.parent.name == "core" and path.name == "trace.py":
            continue  # the writer's own method definition, not a second call site
        text = path.read_text(encoding="utf-8")
        if ".record_llm(" in text:
            offenders.append(str(path))
    assert offenders == []


# -- RT6 -----------------------------------------------------------------

def test_every_span_is_redacted_before_it_is_persisted(tmp_path: Path) -> None:
    """Seed a fake secret bound to a SecretRef-style value, drive a span whose
    fed_id would otherwise carry it, and grep the resulting trace.jsonl for the
    raw value -> zero matches."""
    secret_value = "sk-fake-9f2c7a1b"
    redactor = Redactor({"API_KEY": secret_value})
    trace_path = tmp_path / "trace.jsonl"
    writer = TraceWriter(trace_path, "trace-secret", redactor=redactor)

    writer.record_llm(
        provider="mock:mock", role="agent", prompt_file="p.md",
        input_tokens=10, output_tokens=5, latency_s=0.1, retries=0,
        fallback_hops=0, fed_id=f"case-{secret_value}",
    )

    raw = trace_path.read_text(encoding="utf-8")
    assert secret_value not in raw
    assert "REDACTED" in raw


def test_redactor_assert_clean_raises_on_a_surviving_secret() -> None:
    redactor = Redactor({"API_KEY": "sk-fake-9f2c7a1b"})
    redactor.assert_clean(redactor.scrub("prefix sk-fake-9f2c7a1b suffix"))  # scrubbed -> fine
    try:
        redactor.assert_clean("prefix sk-fake-9f2c7a1b suffix")  # never scrubbed -> raise
    except ValueError:
        pass
    else:
        raise AssertionError("assert_clean did not raise on a raw secret")


def test_the_real_stagecontext_wiring_never_leaks_a_declared_secret(tmp_path: Path) -> None:
    """RT6 through the REAL production wiring (AT-561, checker cycle 1 FAIL):
    a `StageContext` built with a project's `SecretStore` (no `trace=` kwarg,
    exactly how `orchestrate_runners.make_ingest_runner` is actually driven)
    must never fall back to an unredacted `Redactor({})`. The prior RT6 tests
    hand-built a populated `Redactor` and proved only the mechanism; this one
    drives the mechanism through the wiring a real run would actually use."""
    store = _store(tmp_path)
    secret_value = "sk-real-DEADBEEF12345"
    secrets = SecretStore(
        Project(slug="demo", name="D", base_url="https://demo.test",
               secrets=[SecretRef(key="FAKE_API_KEY")]),
        {"FAKE_API_KEY": secret_value},
    )
    provider = MockProvider(model="mock", responses={"agent": [{"steps": []}]})

    def ingest_runner(ctx: StageContext, prev_ref: str | None) -> str:
        provider.trace = ctx.trace  # exactly orchestrate_runners.make_ingest_runner's own line
        provider.act(f"do something with {secret_value}", object,
                     prompt_file="p.md", fed_id=f"case-{secret_value}")
        return "ok"

    ctx = StageContext(store=store, run_id="run_real_wiring", secrets=secrets,
                       runners={StageName.INGEST: ingest_runner})
    run_or_resume(Project(slug="demo", name="D", base_url="https://demo.test"), ctx)

    raw = store.paths.run_trace("run_real_wiring").read_text(encoding="utf-8")
    assert secret_value not in raw


# -- RT7 -----------------------------------------------------------------

def test_the_run_view_panel_reflects_a_mutated_trace_file(tmp_path: Path) -> None:
    store = _store(tmp_path)
    run_id = "run_view_test"
    writer = TraceWriter(store.paths.run_trace(run_id), run_id)
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC)
    writer.record_stage(StageCheckpoint(stage=StageName.MODEL, status="done",
                                        started=t0, finished=t1))

    before = _trace_card(store, run_id)
    assert "1.00s" in before
    assert "999.00s" not in before

    lines = store.paths.run_trace(run_id).read_text(encoding="utf-8").splitlines()
    mutated = json.loads(lines[0])
    mutated["duration_s"] = 999.0
    store.paths.run_trace(run_id).write_text(json.dumps(mutated) + "\n", encoding="utf-8")

    after = _trace_card(store, run_id)
    assert "999.00s" in after
