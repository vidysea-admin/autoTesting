"""`autotester orchestrate` resume edge cases — AT-575 fix cycle 2.

Split out of `test_cli_orchestrate.py` at the 300-line cap (C2): these four
tests all belong to the same fix-cycle-2 story (checker verdict `a6efb6c`,
FAIL on cycle 1 for a copied D-018 consent gate, plus two questions the
coordinator decided to fix rather than leave open):

- consent is skipped on resume ONLY when the stored DISCOVER checkpoint's
  status is exactly `"done"` — never on `failed`/`pending`/missing;
- `mode` is read from the stored `RunState` on resume, never recomputed from
  the project's CURRENT sources (which could have changed since the run
  started);
- an unknown `--run-id` (no `state.json` on disk) behaves like a fresh run,
  with a one-line note, never a crash.

Same fixtures/conventions as `test_cli_orchestrate.py` (temp `AUTOTESTER_ROOT`,
`typer.testing.CliRunner`, never the real `.env`/`projects/`).
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester import cli_orchestrate, providers
from autotester.cli import app
from autotester.providers.mock import MockProvider
from autotester.schema.enums import SourceKind
from autotester.schema.flowspec import FlowSpec, Screen
from autotester.schema.observation import ObservedScreen, VideoObservation
from autotester.schema.project import Project, Source
from autotester.schema.run_state import RunState, StageName
from autotester.stages.orchestrate_runners import _persist_proposal
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore

runner = CliRunner()
BASE_URL = "https://demo.test"
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


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


def _grant_crawl_approval(root: Path) -> None:
    result = runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", BASE_URL,
        "--scope", "read-only crawl", "--granted-by", "umesh",
        "--expires", TOMORROW, "--max-actions", "200", "--wall-clock", "600"])
    assert result.exit_code == 0, result.output


def _revoke_approvals(root: Path) -> None:
    """Simulate every granted approval having expired/vanished — no CLI to
    revoke one, so this drops the file the same way an operator letting an
    approval lapse would leave nothing valid behind."""
    ProjectStore("demo", root).paths.approvals.unlink(missing_ok=True)


def _fake_discover_runner(*, succeed: bool):
    """A DISCOVER stage runner that never opens a browser — swaps in for
    `make_discover_runner` so these tests can reach a `done` or `failed`
    DISCOVER checkpoint deterministically and offline."""
    def _factory(proj: object, crawl_fn: object):
        def _run(ctx: object, prev_ref: object) -> str:
            if not succeed:
                raise RuntimeError("boom-discover")
            spec = FlowSpec(project=proj.slug, screens=[Screen(id="s_home", name="Home")])
            return _persist_proposal(ctx, StageName.DISCOVER, spec)
        return _run
    return _factory


def _flaky_merge(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """`merge_flowspec` (MODEL's own work) raises on its first call only."""
    import autotester.stages.orchestrate_runners as runners_mod
    real_merge = runners_mod.merge_flowspec
    calls: list[int] = []

    def _merge(existing: object, incoming: object, **kw: object) -> object:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom-model")
        return real_merge(existing, incoming, **kw)

    monkeypatch.setattr(runners_mod, "merge_flowspec", _merge)
    return calls


# -- consent skips ONLY when DISCOVER is stored `done` ----------------------

def test_resume_past_a_done_discover_skips_consent_even_if_the_approval_lapsed(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checker question 1 / coordinator decision: DISCOVER already `done`
    means a resume will never open a browser, so a since-lapsed approval must
    not block it. First invocation: DISCOVER succeeds (fake, no browser),
    MODEL fails once. The approval is then revoked entirely. Second
    invocation, same --run-id: MODEL resumes and succeeds, no consent
    refusal, even though NO valid approval exists any more."""
    store = _seed_project(root)
    store.add_source(Source(project="demo", kind=SourceKind.URL, url=BASE_URL))
    _grant_crawl_approval(root)
    monkeypatch.setattr(cli_orchestrate, "make_discover_runner",
                        _fake_discover_runner(succeed=True))
    model_calls = _flaky_merge(monkeypatch)

    first = runner.invoke(app, ["orchestrate", "demo", "--run-id", "run_explore_resume"])
    assert first.exit_code == 1, first.output
    state1 = _state(root, "run_explore_resume")
    assert state1.checkpoint(StageName.DISCOVER).status == "done"
    assert state1.checkpoint(StageName.MODEL).status == "failed"
    assert len(model_calls) == 1

    _revoke_approvals(root)
    assert not store.paths.approvals.exists()

    second = runner.invoke(app, ["orchestrate", "demo", "--run-id", "run_explore_resume"])

    assert second.exit_code == 0, second.output
    assert "refusing to start a crawl" not in second.output.lower(), (
        "a resume past a done DISCOVER was blocked by consent it will never need")
    state2 = _state(root, "run_explore_resume")
    assert state2.checkpoint(StageName.DISCOVER).status == "done"
    assert state2.checkpoint(StageName.MODEL).status == "done"
    assert len(model_calls) == 2


def test_resume_past_a_failed_discover_still_hits_consent(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checker amendment: only an exact `"done"` DISCOVER skips the preflight
    — a FAILED one must still hit it (no browser opened either way here, but
    the gate itself must still fire) and the refusal must leave no NEW trace
    span, matching the fresh-run refusal's own "no trace" invariant."""
    store = _seed_project(root)
    store.add_source(Source(project="demo", kind=SourceKind.URL, url=BASE_URL))
    _grant_crawl_approval(root)
    monkeypatch.setattr(cli_orchestrate, "make_discover_runner",
                        _fake_discover_runner(succeed=False))

    first = runner.invoke(app, ["orchestrate", "demo", "--run-id", "run_discover_fail"])
    assert first.exit_code == 1, first.output
    state1 = _state(root, "run_discover_fail")
    assert state1.checkpoint(StageName.DISCOVER).status == "failed"
    trace_path = store.paths.run_trace("run_discover_fail")
    trace_before = trace_path.read_text(encoding="utf-8") if trace_path.exists() else ""

    _revoke_approvals(root)

    second = runner.invoke(app, ["orchestrate", "demo", "--run-id", "run_discover_fail"])

    assert second.exit_code == 2, second.output
    assert "approv" in second.output.lower()
    trace_after = trace_path.read_text(encoding="utf-8") if trace_path.exists() else ""
    assert trace_after == trace_before, "a refused resume wrote a new trace span"


# -- mode is read from stored state, not recomputed on resume ---------------

def test_resume_keeps_the_stored_mode_even_if_current_sources_would_flip_it(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checker question 2 / coordinator decision: a run that started `learn`
    must resume `learn` even if its teaching Source is later removed (which
    would flip a freshly-computed `choose_mode` to `explore`). The old,
    recompute-on-resume code would try to wire DISCOVER for this resume and
    hit the crawl-consent gate — no crawl approval is granted in this test,
    so that bug would show up as an unexpected exit 2 / crawl-consent refusal."""
    _seed_project(root)
    _mock_ingest_provider(monkeypatch)
    _register(root, _a_video(root))
    model_calls = _flaky_merge(monkeypatch)

    first = runner.invoke(app, [
        "orchestrate", "demo", "--provider", "mock", "--run-id", "run_mode_lock"])
    assert first.exit_code == 1, first.output
    state1 = _state(root, "run_mode_lock")
    assert state1.mode == "learn"
    assert state1.checkpoint(StageName.INGEST).status == "done"
    assert state1.checkpoint(StageName.MODEL).status == "failed"

    # Remove the teaching Source -- a fresh `choose_mode` would now say "explore".
    ProjectStore("demo", root).paths.sources_index.write_text("", encoding="utf-8")

    second = runner.invoke(app, [
        "orchestrate", "demo", "--provider", "mock", "--run-id", "run_mode_lock"])

    assert second.exit_code == 0, second.output
    assert "refusing to start a crawl" not in second.output.lower(), (
        "resume recomputed mode as explore and hit the crawl-consent gate")
    state2 = _state(root, "run_mode_lock")
    assert state2.mode == "learn"
    assert state2.checkpoint(StageName.MODEL).status == "done"
    assert state2.checkpoint(StageName.DISCOVER) is None
    assert len(model_calls) == 2


# -- an unknown --run-id behaves like a fresh run ----------------------------

def test_unknown_run_id_starts_fresh_with_a_clear_message_not_a_crash(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `--run-id` naming no `state.json` on disk (typo, or a ledger the
    operator no longer has) must behave exactly like a freshly-minted one,
    with a one-line note -- never a traceback."""
    _seed_project(root)
    _mock_ingest_provider(monkeypatch)
    _register(root, _a_video(root))

    result = runner.invoke(app, [
        "orchestrate", "demo", "--provider", "mock", "--run-id", "totally-unknown-id"])

    assert result.exit_code == 0, result.output
    assert "no existing run 'totally-unknown-id'" in result.output
    state = _state(root, "totally-unknown-id")
    assert state.mode == "learn"
    assert state.checkpoint(StageName.INGEST).status == "done"
    assert state.checkpoint(StageName.MODEL).status == "done"
