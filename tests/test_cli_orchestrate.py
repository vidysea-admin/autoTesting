"""What `autotester orchestrate` ACTUALLY does — AT-575.

T-163's resumable orchestrator (`stages/orchestrate.py::run_or_resume`, D-036)
had no caller outside `tests/test_orchestrate*.py`, so resume-after-
interruption was reachable only from pytest calling the driver directly —
never through anything an operator types. These tests drive the real CLI
(`typer.testing.CliRunner`) exactly the way `test_ingest_real_cli.py` and
`test_crawl_real_cli.py` do for their own commands, against a temp
`AUTOTESTER_ROOT` — never the real `.env` or `projects/`.

Fix-cycle-2 resume/consent/mode tests live in `test_cli_orchestrate_resume.py`
(split at the 300-line cap, C2).

Contract: qa/contracts/orchestrator.md OR1-OR6.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester import providers
from autotester.cli import app
from autotester.providers.mock import MockProvider
from autotester.schema.enums import ReviewStatus, SourceKind
from autotester.schema.observation import ObservedScreen, VideoObservation
from autotester.schema.project import Project, SecretRef, Source
from autotester.schema.run_state import RunState, StageName
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore

runner = CliRunner()
BASE_URL = "https://demo.test"


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


def _seed_project(root: Path, **kw: object) -> ProjectStore:
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="Demo", base_url=BASE_URL,
                               allowed_domains=["demo.test"], **kw))
    return store


def _a_video(root: Path) -> Path:
    path = root / "erp1.mp4"
    path.write_bytes(b"fake-mp4")
    return path


def _register(root: Path, path: Path) -> str:
    result = runner.invoke(app, ["ingest", "register", "demo", str(path)])
    assert result.exit_code == 0, result.output
    return ProjectStore("demo", root).list_sources()[-1].id


def _mock_ingest_provider(monkeypatch: pytest.MonkeyPatch) -> MockProvider:
    provider = MockProvider(responses={"vision": [
        VideoObservation(screens=[ObservedScreen(name="Home", t_start=1.0)])]})
    monkeypatch.setattr(providers, "get", lambda _id, **_kw: provider)
    return provider


def _state(root: Path, run_id: str) -> RunState:
    loaded = read_json(ProjectStore("demo", root).paths.run_dir(run_id) / "state.json", RunState)
    assert loaded is not None
    return loaded


# -- (a) a fresh learn run leaves RunState checkpoints ----------------------

def test_fresh_learn_run_checkpoints_ingest_and_model_through_the_cli(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_project(root)
    _mock_ingest_provider(monkeypatch)
    source_id = _register(root, _a_video(root))

    result = runner.invoke(app, [
        "orchestrate", "demo", "--provider", "mock", "--run-id", "run_fresh"])

    assert result.exit_code == 0, result.output
    state = _state(root, "run_fresh")
    assert state.mode == "learn"
    assert state.checkpoint(StageName.INGEST).status == "done"
    assert state.checkpoint(StageName.MODEL).status == "done"
    # MODEL actually folded INGEST's proposal into the reviewed flowspec —
    # this is the whole point of driving `run_or_resume`, not a direct call.
    spec = ProjectStore("demo", root).load_flowspec()
    assert spec is not None and spec.screens
    assert spec.review.status is ReviewStatus.DRAFT
    assert source_id in spec.source_ids


# -- (b) interrupt mid-stage, re-invoke, assert resume never redoes INGEST --

def test_resume_after_interruption_never_redoes_the_done_stage(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OR2/OR4 through the entry point: MODEL raises on the first invocation
    (INGEST already `done`); a second invocation with the SAME --run-id must
    not call `ingest_video` again and must resume exactly at MODEL."""
    _seed_project(root)
    _mock_ingest_provider(monkeypatch)
    _register(root, _a_video(root))

    import autotester.stages.orchestrate_runners as runners_mod
    real_ingest = runners_mod.ingest_video
    ingest_calls: list[int] = []

    def _counting_ingest(*a: object, **kw: object) -> object:
        ingest_calls.append(1)
        return real_ingest(*a, **kw)

    real_merge = runners_mod.merge_flowspec
    model_calls: list[int] = []

    def _flaky_merge(existing: object, incoming: object, **kw: object) -> object:
        model_calls.append(1)
        if len(model_calls) == 1:
            raise RuntimeError("boom-model")
        return real_merge(existing, incoming, **kw)

    monkeypatch.setattr(runners_mod, "ingest_video", _counting_ingest)
    monkeypatch.setattr(runners_mod, "merge_flowspec", _flaky_merge)

    first = runner.invoke(app, [
        "orchestrate", "demo", "--provider", "mock", "--run-id", "run_resume"])
    assert first.exit_code == 1, first.output  # a failed checkpoint is an honest non-zero exit
    state1 = _state(root, "run_resume")
    assert state1.checkpoint(StageName.INGEST).status == "done"
    assert state1.checkpoint(StageName.MODEL).status == "failed"
    assert "boom-model" in (state1.checkpoint(StageName.MODEL).error or "")
    ingest_ref_after_first = state1.checkpoint(StageName.INGEST).artifact_ref
    assert len(ingest_calls) == 1

    second = runner.invoke(app, [
        "orchestrate", "demo", "--provider", "mock", "--run-id", "run_resume"])
    assert second.exit_code == 0, second.output

    assert len(ingest_calls) == 1, "resume re-ran the already-done INGEST stage"
    state2 = _state(root, "run_resume")
    assert state2.checkpoint(StageName.INGEST).artifact_ref == ingest_ref_after_first, (
        "a done stage's artifact was rewritten on resume")
    assert state2.checkpoint(StageName.MODEL).status == "done"
    assert len(model_calls) == 2, "resume did not re-enter the failed MODEL stage"


# -- (c) secrets reach StageContext -> the RT6 trace gate is live -----------

def test_secrets_reach_stagecontext_so_the_trace_gate_never_falls_back(
    root: Path, monkeypatch: pytest.MonkeyPatch, recwarn: pytest.WarningsRecorder,
) -> None:
    """AT-561: with no `secrets=`, `StageContext` silently builds an unredacted
    `Redactor({})` and warns `RuntimeWarning`. The command must pass the
    project's `SecretStore` through, so that warning never fires on a real
    invocation -- proving the CLI wires `secrets=` rather than leaving the
    trace's redactor empty."""
    (root / ".env").write_text("DEMO_PASSWORD=s3cr3t-fake-value\n", encoding="utf-8")
    _seed_project(root, secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    _mock_ingest_provider(monkeypatch)
    _register(root, _a_video(root))

    result = runner.invoke(app, [
        "orchestrate", "demo", "--provider", "mock", "--run-id", "run_secrets"])

    assert result.exit_code == 0, result.output
    leaks = [w for w in recwarn.list if "no `secrets=`" in str(w.message)]
    assert not leaks, "StageContext fell back to an unredacted Redactor({}) — RT6 gate is dark"


# -- (d) consent is refused before an outward-facing DISCOVER run -----------

def test_explore_mode_without_an_approval_refuses_before_the_crawl_starts(
    root: Path,
) -> None:
    """OR1's `explore` path is outward-facing (DISCOVER crawls the live site) —
    it must honour the same D-018 consent gate `autotester explore` does, and
    never bypass it just because it is reached through the orchestrator."""
    store = _seed_project(root)
    store.add_source(Source(project="demo", kind=SourceKind.URL, url=BASE_URL))

    result = runner.invoke(app, ["orchestrate", "demo"])

    assert result.exit_code == 2, result.output
    assert "approv" in result.output.lower()
    # AT-111's invariant, honoured here too: a refused run leaves no run dir.
    assert not store.paths.runs_dir.exists() or not list(store.paths.runs_dir.iterdir())
