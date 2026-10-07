"""Shared fixtures for the bug-loop tests (qa/contracts/team-bug-loop.md TB1-TB6).

A real `ProjectStore` in a tmp dir: a case, its rubric, and runs whose only artifacts are
`Verdict` files — the loop is meant to read nothing else (TB3).
"""

from __future__ import annotations

from pathlib import Path

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Result
from autotester.schema.flowspec import ExpectedState, Step
from autotester.schema.project import Project
from autotester.schema.run import Run
from autotester.schema.verdict import Criterion, Failure, Rubric, Verdict
from autotester.stages.bug_loop import load_bugs
from autotester.store.project_store import ProjectStore

PROJECT = "demo"


def make_store(tmp_path: Path) -> ProjectStore:
    store = ProjectStore(PROJECT, root=tmp_path)
    store.save_project(Project(slug=PROJECT, name="Demo", base_url="https://demo.test"))
    return store


def add_case(store: ProjectStore, target: str = "/dash", *, pinned: bool = False,
             criteria: tuple[tuple[str, str], ...] = (("C1", "heading is shown"),)) -> Case:
    step = Step(order=1, action=Action.NAVIGATE, target=target,
                expected=ExpectedState(visible_text=["Dashboard"]))
    case = Case(project=PROJECT, flow_id="flow-a", kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY, title=f"open {target}", steps=[step],
                pinned=pinned, pinned_issue_id="iss_x" if pinned else None)
    store.add_case(case)
    set_criteria(store, case, criteria)
    return case


def set_criteria(store: ProjectStore, case: Case, criteria: tuple[tuple[str, str], ...]) -> None:
    store.save_rubric(Rubric(id=f"rub_{case.id}", case_id=case.id,
                             criteria=[Criterion(id=i, text=t) for i, t in criteria]))


def verdict(run_id: str, case: Case, result: Result, *, failing: tuple[str, ...] = (),
            total: int = 1, met: int | None = None, seen: int = 1, asked: int = 1) -> Verdict:
    fails = [Failure(criterion_id=c, reason=f"{c} not met", evidence_refs=["shot.png"])
             for c in failing]
    return Verdict(run_id=run_id, case_id=case.id, result=result, criteria_total=total,
                   criteria_met=(total - len(fails) if met is None else met), failures=fails,
                   grader_provider="judge", images_seen=seen, images_requested=asked)


def save_run(store: ProjectStore, run_id: str, *verdicts: Verdict) -> str:
    store.save_run(Run(id=run_id, project=PROJECT, case_ids=[v.case_id for v in verdicts]))
    for item in verdicts:
        store.save_verdict(run_id, item)
    return run_id


def bug_of(store: ProjectStore, key: str | None = None):
    bugs = load_bugs(store)
    assert len(bugs) == 1 or key, f"expected one bug, got {len(bugs)}"
    return bugs[0] if key is None else next(b for b in bugs if b.bug_key == key)
