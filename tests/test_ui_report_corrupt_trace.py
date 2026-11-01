"""E1 (qa/contracts/e2e-fixes.md E1.1-E1.3, AT-1412): a corrupt `trace.jsonl` line degrades the
Trace card, never the run page, and never loses the saved `Run`. Fakes only -- no browser."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from run_approval_fixture import grant_live_case_approval
from test_run_launcher_approval import world  # noqa: F401  (the launcher fixture, one place)

from autotester.core.trace import TraceParseError, read_spans
from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, CaseKind, Outcome, Result
from autotester.schema.project import Project
from autotester.schema.run import RawResult, Run
from autotester.schema.run_state import StageName
from autotester.schema.trace import StageSpan
from autotester.schema.verdict import Verdict
from autotester.stages import run_launcher
from autotester.stages.run_launcher import launch_run
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

CANARY = "CANARY-corrupt-line-4f9a"


@pytest.fixture
def scratch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


def _store_with_run(root: Path, trace_lines: list[str] | None) -> ProjectStore:
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    store.add_case(Case(id="case_1", project="demo", flow_id="f", kind=CaseKind.BEST,
                        case_class=CaseClass.HAPPY, title="Check one"))
    store.save_run(Run(id="run_1", project="demo", case_ids=["case_1"]))
    store.save_result("run_1", RawResult(case_id="case_1", outcome=Outcome.COMPLETED))
    store.save_verdict("run_1", Verdict(run_id="run_1", case_id="case_1", result=Result.PASS,
                                        grader_provider="mock", rubric_hash="rub_x"))
    if trace_lines is not None:
        path = store.paths.run_trace("run_1")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(trace_lines) + "\n", encoding="utf-8")
    return store


def _good_line() -> str:
    return StageSpan(trace_id="run_1", stage=StageName.EXECUTE, status="done",
                     duration_s=1.5).model_dump_json()


def _get(root: Path):
    return TestClient(app).get("/projects/demo/runs/run_1")


def test_e1_1_a_corrupt_trace_line_still_renders_the_run_page(scratch) -> None:
    _store_with_run(scratch, [_good_line(), f"not json {CANARY}"])
    resp = _get(scratch)
    assert resp.status_code == 200
    assert "Run bounds" in resp.text and "Check one" in resp.text and "run_1" in resp.text


def test_e1_2_the_trace_card_states_the_failure_and_leaks_no_line_content(scratch) -> None:
    _store_with_run(scratch, [_good_line(), f"not json {CANARY}"])
    text = _get(scratch).text
    card = text[text.index("Trace"):]
    assert "trace.jsonl:2" in card and "not valid JSON" in card
    assert "could not be read" in card
    assert CANARY not in text
    assert "<td>EXECUTE" not in text and "1.50s" not in text   # no span shown as if clean


def test_e1_2_a_run_with_no_trace_file_shows_no_trace_card(scratch) -> None:
    store = _store_with_run(scratch, None)
    assert not store.paths.run_trace("run_1").exists()
    resp = _get(scratch)
    assert resp.status_code == 200
    assert "<h2>Trace</h2>" not in resp.text and "could not be read" not in resp.text


def test_e1_2_a_clean_trace_still_renders_its_rows(scratch) -> None:
    _store_with_run(scratch, [_good_line()])
    text = _get(scratch).text
    assert "1.50s" in text and "could not be read" not in text


def test_e1_3_read_spans_still_raises_on_a_bad_line(scratch) -> None:
    store = _store_with_run(scratch, [_good_line(), f"not json {CANARY}"])
    with pytest.raises(TraceParseError, match=r"trace\.jsonl:2"):
        read_spans(store.paths.run_trace("run_1"))


def test_e1_3_a_corrupt_trace_does_not_lose_the_saved_run(world, monkeypatch) -> None:  # noqa: F811
    store, seams = world
    grant_live_case_approval(store)
    real = run_launcher.run_cases_traced

    def corrupting(store_, run_id, *a, **kw):
        plan = real(store_, run_id, *a, **kw)
        with store_.paths.run_trace(run_id).open("a", encoding="utf-8") as fh:
            fh.write(f"not json {CANARY}\n")
        return plan

    monkeypatch.setattr(run_launcher, "run_cases_traced", corrupting)
    run = launch_run("demo", seams=seams)
    saved = store.load_run(run.id)
    assert saved is not None and saved.id == run.id
    assert saved.phase_totals_s is None and saved.unaccounted_s is None   # NOT RECORDED, not 0
