"""AT-774: a retired case is never run; `prepare_run` is the one place a run picks its cases.

The launcher is the single run entry (`tests/test_run_launcher.py`), so pinning the selection in
`stages/run_launcher.py::prepare_run` pins the UI Run button, the queue worker, the Test button
and the scheduler tick at once. Retirement beats a pin: a retired pinned p0 is not run either.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from run_approval_fixture import grant_live_case_approval

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, CaseStatus
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.stages.run_launcher import LaunchRefused, RunSeams, prepare_run
from autotester.store.project_store import ProjectStore


class _Judge:
    trace = None

    def __init__(self, project: Project) -> None:
        self.project = project

    def available(self) -> bool:
        return True


def _case(flow: str, status: CaseStatus, **extra: object) -> Case:
    return Case(project="demo", flow_id=flow, kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title=flow, status=status, steps=[Step(order=0, action=Action.CLICK, target="#go")],
                **extra)


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    s = ProjectStore("demo", tmp_path)
    s.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                           allowed_domains=["demo.test"]))
    grant_live_case_approval(s)
    return s


def test_prepare_run_skips_retired_cases(store: ProjectStore) -> None:
    live, gone = _case("live", CaseStatus.APPROVED), _case("gone", CaseStatus.RETIRED)
    for c in (live, gone):
        store.add_case(c)
    prepared = prepare_run("demo", RunSeams(judge_factory=_Judge))
    assert [c.id for c in prepared.cases] == [live.id]
    assert len(prepared.entry_flags) == 1
    assert {c.id for c in store.list_cases()} == {live.id, gone.id}   # retired stays listed


def test_a_retired_pinned_case_is_not_run_either(store: ProjectStore) -> None:
    live = _case("live", CaseStatus.PROPOSED, priority="p0")
    pinned = _case("pinned", CaseStatus.RETIRED, pinned=True, pinned_issue_id="AT-1")
    for c in (live, pinned):
        store.add_case(c)
    prepared = prepare_run("demo", RunSeams(judge_factory=_Judge), priorities=["p0", "p1"])
    assert [c.id for c in prepared.cases] == [live.id]


def test_a_project_of_only_retired_cases_has_nothing_to_run(store: ProjectStore) -> None:
    store.add_case(_case("gone", CaseStatus.RETIRED))
    with pytest.raises(LaunchRefused) as refused:
        prepare_run("demo", RunSeams(judge_factory=_Judge))
    assert refused.value.status == 400 and "no cases to run" in refused.value.reason
