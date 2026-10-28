"""Run-teardown stall, the wiring: a run's saved `Run` carries phase totals and the unaccounted
remainder, a failed judge tier leaves a trace row, every judge tier is bounded, and a
memory-starved host is warned about. Fakes only -- no browser, no network, no model."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel
from run_approval_fixture import grant_live_case_approval

import autotester.ui.run_execution as run_execution
from autotester.browser.session import BrowserSession
from autotester.core.redact import Redactor
from autotester.core.trace import TraceWriter, read_spans
from autotester.providers import langchain_fallback as lcf
from autotester.providers.langchain_fallback import LangChainFallbackProvider
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.trace import PhaseSpan
from autotester.schema.verdict import Verdict
from autotester.stages import run_launcher
from autotester.stages.parallel_run import ParallelPlan
from autotester.stages.run_launcher import RunSeams, launch_run, warn_if_memory_starved
from autotester.store.project_store import ProjectStore


class _Judge:
    trace = None

    def __init__(self, project: Project) -> None:
        self.project = project

    def available(self) -> bool:
        return True


# --- (a) the saved Run carries the phase summary --------------------------------------------

def _demo_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    """An approved project with one entry case (it navigates to the project's own base URL)."""
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    grant_live_case_approval(store)
    store.add_case(Case(project="demo", flow_id="home", kind=CaseKind.BEST,
                        case_class=CaseClass.HAPPY, title="Home loads",
                        steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test")]))
    return store


def test_a_launched_run_records_phase_totals_and_unaccounted_seconds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _demo_store(tmp_path, monkeypatch)

    def graded(case, session, judge, run_id, store_):
        return (RawResult(case_id=case.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case.id, result=Result.PASS,
                        grader_provider="mock"))

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(run_execution, "_wipe_entry_profile", lambda _p: time.sleep(0.06))
    monkeypatch.setattr(run_execution, "run_and_grade_case_resilient", graded)
    seams = RunSeams(judge_factory=_Judge, free_ram_mb=lambda: 16000.0,
                     planner=lambda project, **_kw: ParallelPlan(1, 1, 1, "config", 16000.0, 4))

    run = launch_run("demo", seams=seams)

    saved = store.load_run(run.id)
    assert saved is not None and saved.phase_totals_s is not None
    assert {"entry_profile_wipe", "session_start", "case_pipeline",
            "save_result"} <= set(saved.phase_totals_s)
    assert saved.unaccounted_s is not None and saved.unaccounted_s >= 0.0
    # D-112 / F2: the seconds held off the approval clock are in run.json, auditable
    assert saved.excluded_s is not None and set(saved.excluded_s) == {
        "judging", "housekeeping", "total"}
    assert saved.excluded_s["housekeeping"] >= 0.05  # the slowed profile wipe
    assert saved.excluded_s["total"] >= saved.excluded_s["housekeeping"] - 0.001
    spans = read_spans(store.paths.run_trace(run.id), include_phases=True)
    assert any(isinstance(s, PhaseSpan) and s.phase == "save_result" for s in spans)


# --- (e) a failed judge tier is traced, and every tier is bounded ---------------------------

class _Answer(BaseModel):
    result: str


class _Raises:
    def with_structured_output(self, schema, include_raw=False):
        return self

    def invoke(self, _prompt):
        raise TimeoutError("vendor hung")


class _Answers:
    def with_structured_output(self, schema, include_raw=False):
        return self

    def invoke(self, _prompt):
        return {"parsed": _Answer(result="ok"), "raw": SimpleNamespace(usage_metadata={})}


def test_a_failed_judge_tier_leaves_a_trace_row_and_the_next_tier_answers(tmp_path) -> None:
    trace = TraceWriter(tmp_path / "t.jsonl", "run-1", Redactor({}))
    provider = LangChainFallbackProvider(
        chain=[("anthropic", _Raises), ("gemini", _Answers)])
    provider.trace = trace
    assert provider.judge("p", _Answer, fed_id="c1").result == "ok"
    failed = [s for s in read_spans(trace.path, include_phases=True)
              if isinstance(s, PhaseSpan) and s.phase == "judge_tier_failed"]
    assert len(failed) == 1
    assert failed[0].ok is False and failed[0].nested and failed[0].case_id == "c1"
    assert failed[0].note == "anthropic/judge: TimeoutError"  # the type, never the message


def test_the_default_tiers_carry_a_timeout_and_a_retry_cap(monkeypatch) -> None:
    for key in ("OLLAMA_BASE_URL", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x-anthropic")
    monkeypatch.setenv("GEMINI_API_KEY", "x-gemini")
    chain = dict(lcf._default_chain())
    claude, gemini = chain["anthropic"](), chain["gemini"]()
    assert claude.default_request_timeout == lcf.JUDGE_TIMEOUT_S
    assert claude.max_retries == lcf.JUDGE_MAX_RETRIES
    assert gemini.timeout == lcf.JUDGE_TIMEOUT_S and gemini.max_retries == lcf.JUDGE_MAX_RETRIES


# --- (f) a memory-starved host is warned about ----------------------------------------------

def test_prepare_run_warns_once_when_free_ram_is_under_two_gb(capsys) -> None:
    assert warn_if_memory_starved(RunSeams(free_ram_mb=lambda: 700.0)) is True
    err = capsys.readouterr().err
    assert "memory-starved" in err and "0.7 GB" in err


def test_prepare_run_itself_issues_the_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    _demo_store(tmp_path, monkeypatch)
    run_launcher.prepare_run("demo", RunSeams(judge_factory=_Judge, free_ram_mb=lambda: 900.0))
    assert "memory-starved" in capsys.readouterr().err


def test_no_warning_with_headroom_or_when_the_measurement_fails(capsys) -> None:
    assert warn_if_memory_starved(RunSeams(free_ram_mb=lambda: 8000.0)) is False

    def broken() -> float:
        raise OSError("no meminfo")

    assert warn_if_memory_starved(RunSeams(free_ram_mb=broken)) is False
    assert capsys.readouterr().err == ""
    assert run_launcher.LOW_RAM_WARN_MB == 2048.0


def test_a_garbage_or_unprintable_measurement_never_raises_out_of_the_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert warn_if_memory_starved(RunSeams(free_ram_mb=lambda: None)) is False  # type: ignore[arg-type,return-value]
    assert warn_if_memory_starved(RunSeams(free_ram_mb=lambda: "lots")) is False  # type: ignore[arg-type,return-value]

    class _Broken:
        def write(self, _text: str) -> int:
            raise OSError("closed stderr")

        def flush(self) -> None:
            raise OSError("closed stderr")

    monkeypatch.setattr(sys, "stderr", _Broken())
    assert warn_if_memory_starved(RunSeams(free_ram_mb=lambda: 100.0)) is False


def test_wall_clock_description_says_target_acting_time_only() -> None:
    from autotester.schema.approval import RunApproval
    text = (RunApproval.model_fields["wall_clock_s"].description or "").lower()
    assert "acting" in text and "judging" in text and "housekeeping" in text
    assert "in total" not in text
