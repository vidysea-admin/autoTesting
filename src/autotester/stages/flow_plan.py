"""Derive each completed flow's persisted validation plan from a finished run (AT-898, RR6).

One job — turn the frozen `PipelineBatch` a REPORT stage reads into `FlowPlan`s: one per flow
whose cases were all observed and graded in that run, naming exactly those cases. Pure: it
reads the batch and returns rows; the caller persists them via `store.save_flow_plan`.
"""

from __future__ import annotations

from autotester.schema.release import FlowPlan
from autotester.schema.run_state import PipelineBatch


def plans_from_batch(batch: PipelineBatch) -> list[FlowPlan]:
    """One plan per flow with at least one frozen case, every case observed and graded.

    A flow with any case lacking a result or verdict is not 'completed' and gets no plan,
    so a half-run flow stays `not run` in the next release instead of a partial plan."""
    observed = {r.case_id for r in batch.results}
    graded = {v.case_id for v in batch.verdicts}
    by_flow: dict[str, list[str]] = {}
    for case in batch.cases:
        by_flow.setdefault(case.flow_id, []).append(case.id)
    return [FlowPlan(project=batch.project, flow_id=flow, case_ids=list(dict.fromkeys(ids)))
            for flow, ids in by_flow.items()
            if all(i in observed and i in graded for i in ids)]
