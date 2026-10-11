"""T-167 RR2 repair (fix cycle 1): the approval must cover what the release really costs.

A hand-written `scope.json` that under-declares its bounds must not let a small approval
authorise a bigger release, and no byte may be written or graph invoked before the gate passes.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from run_approval_fixture import grant_live_case_approval
from test_regression_trigger import ALL, PASS, PROJECT, YES, _outcome, _runners, _store

from autotester.core.consent import ApprovalRequired
from autotester.schema.run_state import StageName
from autotester.stages import orchestrate, release
from autotester.stages.release import start_release


def _under_declared(tmp_path: Path):
    """3 planned cases, one signed approval of 1 action, and a scope file claiming 1 action."""
    store = _store(tmp_path, approve=False, flows=ALL)
    approval = grant_live_case_approval(store, max_actions=1)
    honest = release.build_scope(PROJECT, store, run_id="rel", approval_id=approval.id,
                                 max_actions=3)
    forged = honest.model_copy(update={"max_actions": 1, "wall_clock_s": 8.0})
    store.save_release_scope(forged)
    return store


def test_rr2_an_under_declared_scope_on_disk_is_refused_before_anything_runs(
        tmp_path: Path) -> None:
    store = _under_declared(tmp_path)
    run_dir = store.paths.run_dir("rel")
    before = sorted(p.name for p in run_dir.rglob("*"))
    calls: list[str] = []
    runners = _runners(store, _outcome(f1=PASS, f2=PASS, f3=PASS), calls)
    with pytest.raises(ApprovalRequired, match="narrower"):
        start_release(PROJECT, store, run_id="rel", runners=runners)
    with pytest.raises(ApprovalRequired, match="narrower"):  # the human 'yes' cannot rescue it
        start_release(PROJECT, store, run_id="rel", runners=runners, decision=YES)
    assert calls == [] and sorted(p.name for p in run_dir.rglob("*")) == before == ["scope.json"]


def test_rr2_an_under_declared_wall_clock_alone_is_refused(tmp_path: Path) -> None:
    """Only the wall clock is forged: actions are honest (3) and the approval covers them, but
    its wall clock (8 s) is below what 3 actions cost, so the `max(...)` clause must refuse."""
    store = _store(tmp_path, approve=False, flows=ALL)
    approval = grant_live_case_approval(store, max_actions=3, wall_clock_s=8.0)
    honest = release.build_scope(PROJECT, store, run_id="rel", approval_id=approval.id,
                                 max_actions=3)
    store.save_release_scope(honest.model_copy(update={"wall_clock_s": 8.0}))
    calls: list[str] = []
    with pytest.raises(ApprovalRequired, match="narrower"):
        start_release(PROJECT, store, run_id="rel",
                      runners=_runners(store, _outcome(f1=PASS, f2=PASS, f3=PASS), calls))
    assert calls == []


def test_rr2_a_honestly_frozen_scope_stays_resumable(tmp_path: Path) -> None:
    store = _store(tmp_path, flows=ALL)
    runners = _runners(store, _outcome(f1=PASS, f2=PASS, f3=PASS))
    paused = start_release(PROJECT, store, run_id="rel", runners=runners)
    assert paused.checkpoint(StageName.CONFIRM).status == "awaiting_human"
    done = start_release(PROJECT, store, run_id="rel", runners=runners, decision=YES)
    assert done.next_pending() is None


def test_rr2_preflight_runs_before_any_disk_write_and_before_graph_invoke(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(tmp_path, flows=ALL)
    seen: dict[str, object] = {"invoked": False}
    compile_real, preflight_real = orchestrate._compile, orchestrate.release_preflight

    class Spy:
        def __init__(self, graph) -> None:  # type: ignore[no-untyped-def]
            self._graph = graph

        def invoke(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            seen["invoked"] = True
            return self._graph.invoke(*args, **kwargs)

        def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
            return getattr(self._graph, name)

    def preflight(project, ctx):  # type: ignore[no-untyped-def]
        files = lambda: sorted(p.as_posix() for p in tmp_path.rglob("*"))  # noqa: E731
        seen["before"], seen["invoked_at_entry"] = files(), seen["invoked"]
        preflight_real(project, ctx)
        seen["after"], seen["invoked_at_exit"] = files(), seen["invoked"]

    monkeypatch.setattr(orchestrate, "release_preflight", preflight)
    monkeypatch.setattr(orchestrate, "_compile", lambda *a, **k: Spy(compile_real(*a, **k)))
    start_release(PROJECT, store, run_id="rel", runners=_runners(store, {}))
    assert seen["before"] == seen["after"], "a file was written before the approval check passed"
    assert seen["invoked_at_entry"] is False and seen["invoked_at_exit"] is False
    assert seen["invoked"] is True  # the graph did run afterwards, so the spy was live
