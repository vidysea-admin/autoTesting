"""Checker A probe (throwaway, not part of the repo): can `priorities` skip/weaken/re-scope the
approval gate?  Rows: {None, [], p0, p1, all, unknown} x {launch_run, queued re-check}, no approval.
Expected: a refusal (403 / 400 no cases / ValueError for unknown) with the data root byte-identical,
zero browser sessions, zero judge calls."""
import os
import autotester
import pytest
from test_run_launcher_approval import world, _listing, Counters  # noqa: F401  (fixture)
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind
from autotester.schema.flowspec import Step
from autotester.stages.run_launcher import LaunchRefused, launch_run

assert autotester.__file__.lower().startswith(os.environ["MR_COPY"].lower()), autotester.__file__


def _more(store):
    for i, pr in enumerate(["p0", "p1", "p3"]):
        store.add_case(Case(project="demo", flow_id=f"f{i}", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                            title=f"t{i}", priority=pr, pinned=(pr == "p0"),
                            steps=[Step(order=0, action=Action.CLICK, target=f"#g{i}")]))


@pytest.mark.parametrize("pri", [None, [], ["p0"], ["p1"], ["p2"], ["p0", "p1", "p2", "p3"], ["p9"]])
def test_launch_run_priorities_never_skip_approval(world, pri, tmp_path):
    store, seams = world
    _more(store)
    before = _listing(tmp_path)
    with pytest.raises((LaunchRefused, ValueError)) as ex:
        launch_run("demo", seams=seams, priorities=pri)
    if isinstance(ex.value, LaunchRefused):
        assert ex.value.status in (403, 400)
        if ex.value.status == 400:
            assert "no cases" in ex.value.reason
        else:
            assert "no approval exists" in ex.value.reason
    else:
        assert "unknown case priority" in str(ex.value)
    assert _listing(tmp_path) == before
    assert Counters.sessions == 0 and Counters.judgments == 0
    assert not store.paths.runs_dir.exists()


@pytest.mark.parametrize("pri", [None, [], ["p1"], ["p0", "p1", "p2", "p3"]])
def test_queued_recheck_with_priorities_is_gated(world, pri, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from autotester.schema.run_queue import QueueEntry
    from autotester.ui import routes_runs
    from autotester.ui.run_queue import RunRefused
    store, seams = world
    _more(store)
    monkeypatch.setattr(routes_runs, "for_role", lambda project, role: seams.judge_factory(project))
    before = _listing(tmp_path)
    entry = QueueEntry(id="run-probe", project="demo", priorities=pri)
    with pytest.raises(RunRefused):
        routes_runs._run_queued(entry)
    assert _listing(tmp_path) == before
    assert Counters.sessions == 0 and Counters.judgments == 0
