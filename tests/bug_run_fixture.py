"""Builders for the process_run tests: a project on disk with cases, rubrics, runs and verdicts."""

from __future__ import annotations

from pathlib import Path

from bug_loop_fixture import PROJECT, at

from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, CaseKind, Result
from autotester.schema.run import Run
from autotester.schema.verdict import Criterion, Failure, Rubric, Verdict
from autotester.store.project_store import ProjectStore


def make_store(root: Path) -> ProjectStore:
    return ProjectStore(PROJECT, root)


def add_case(store: ProjectStore, flow: str = "checkout", *,
             criteria: tuple[tuple[str, str], ...] = (("C1", "Pay button submits the order"),),
             rubric: bool = True, pinned: bool = False) -> Case:
    """A case in the project, with its rubric saved unless `rubric=False`."""
    rub = Rubric(id=f"rub_{flow}", criteria=[Criterion(id=i, text=t) for i, t in criteria])
    case = Case(project=PROJECT, flow_id=flow, kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title=f"{flow} happy path", rubric_ref=rub.id if rubric else None,
                pinned=pinned, pinned_issue_id="iss_aaaaaaaaaaaa" if pinned else None)
    if rubric:
        store.save_rubric(rub)
    store.add_case(case)
    return case


def set_criteria(store: ProjectStore, case: Case, criteria: tuple[tuple[str, str], ...]) -> None:
    """Re-save the case's rubric with other criteria (the bar moved)."""
    store.save_rubric(Rubric(id=str(case.rubric_ref),
                             criteria=[Criterion(id=i, text=t) for i, t in criteria]))


def verdict(case: Case, run_id: str, result: Result, *, failing: tuple[str, ...] = ("C1",),
            met: int | None = None, total: int = 1, images: tuple[int, int] = (0, 0)) -> Verdict:
    fails = [Failure(criterion_id=c, reason="it did nothing") for c in failing
             ] if result is Result.FAIL else []
    ok = (total if result is Result.PASS else total - len(fails)) if met is None else met
    return Verdict(run_id=run_id, case_id=case.id, result=result, criteria_met=ok,
                   criteria_total=total, failures=fails, images_requested=images[0],
                   images_seen=images[1])


def finished_run(store: ProjectStore, run_id: str, minute: int, verdicts: list[Verdict],
                 cases: list[Case]) -> Run:
    """A run that finished at fixture minute `minute`, with these verdicts saved."""
    for v in verdicts:
        store.save_verdict(run_id, v)
    run = Run(id=run_id, project=PROJECT, case_ids=[c.id for c in cases], finished_at=at(minute))
    store.save_run(run)
    return run
