"""AT-956 / TF2: `priorities` only narrows the cases; it can never skip the live-case approval.

Rows: priorities {None, [], p0, p1, p2, all four, unknown} x no approval, through `launch_run`
and a queued re-check. A swallowed refusal turns these red; the data root stays byte-identical.
"""

from __future__ import annotations

import pytest
from test_run_launcher_approval import Counters, _listing, world  # noqa: F401

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind
from autotester.schema.flowspec import Step
from autotester.stages.run_launcher import LaunchRefused, launch_run


def _more(store):
    for i, pr in enumerate(["p0", "p1", "p3"]):
        store.add_case(Case(project="demo", flow_id=f"f{i}", kind=CaseKind.BEST,
                            case_class=CaseClass.HAPPY,
                            title=f"t{i}", priority=pr, pinned=(pr == "p0"),
                            steps=[Step(order=0, action=Action.CLICK, target=f"#g{i}")]))


ROWS = [None, [], ["p0"], ["p1"], ["p2"], ["p0", "p1", "p2", "p3"], ["p9"]]


@pytest.mark.parametrize("pri", ROWS)
def test_launch_run_priorities_never_skip_approval(world, pri, tmp_path):  # noqa: F811
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
def test_queued_recheck_with_priorities_is_gated(world, pri, tmp_path, monkeypatch):  # noqa: F811
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
