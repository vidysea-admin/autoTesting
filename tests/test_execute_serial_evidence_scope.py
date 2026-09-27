"""AT-577: `execute.py::run_case` scoped to only the calling case's own
evidence. Split from test_execute.py at doctor's 300-line cap.

The serial route (`ui/routes_runs.py::_run_cases_serially`) reuses one
`BrowserSession` across every non-entry case in a run (login continuity
across the whole run). `run_case` used to return
`list(session.state.evidence)` -- the session's WHOLE history -- so every
case after the first carried every earlier case's screenshots too, and the
grader judged case 2 partly on case 1's pages (visible on the run view as
well, since every reader renders `result.evidence`). Contract:
qa/contracts/execute.md E4 (a RawResult carries the evidence the session
recorded FOR THIS CASE, not a running session's full history).
"""

from __future__ import annotations

from pathlib import Path

from test_execute import make_case, session_with_fake_page

from autotester.schema.enums import Action, Outcome
from autotester.schema.flowspec import Step
from autotester.stages.execute import run_case


def test_two_cases_on_one_shared_session_get_disjoint_evidence(tmp_path: Path) -> None:
    """AT-577: run two cases back-to-back on the SAME session (the serial
    route's shape) and assert neither result's evidence overlaps the
    other's -- before the fix, case 2's evidence included case 1's."""
    session = session_with_fake_page(tmp_path)
    case1 = make_case([Step(order=1, action=Action.CLICK, target="#a")])
    case2 = make_case([Step(order=1, action=Action.CLICK, target="#b")])

    result1 = run_case(case1, session)
    result2 = run_case(case2, session)

    assert result1.outcome is Outcome.COMPLETED
    assert result2.outcome is Outcome.COMPLETED
    assert result1.evidence, "case 1 must still record its own evidence"
    assert result2.evidence, "case 2 must still record its own evidence"
    paths1 = {e.path for e in result1.evidence}
    paths2 = {e.path for e in result2.evidence}
    assert paths1.isdisjoint(paths2), (
        f"case 2's evidence must not include case 1's: shared={paths1 & paths2}"
    )
    # the session itself keeps accumulating (screenshot filenames stay
    # unique via the session-wide counter) -- only the RESULT is scoped
    assert len(session.state.evidence) == len(result1.evidence) + len(result2.evidence)


def test_a_third_case_still_only_sees_its_own_slice(tmp_path: Path) -> None:
    """Guards an off-by-one at the boundary: the THIRD case on a reused
    session must start counting from where the second case left off, not
    from 0 and not from case 1's end."""
    session = session_with_fake_page(tmp_path)
    cases = [make_case([Step(order=1, action=Action.CLICK, target=f"#c{i}")]) for i in range(3)]
    results = [run_case(c, session) for c in cases]

    all_paths = [{e.path for e in r.evidence} for r in results]
    for i, paths in enumerate(all_paths):
        for j, other in enumerate(all_paths):
            if i != j:
                assert paths.isdisjoint(other), f"case {i} and case {j} overlap: {paths & other}"
    assert sum(len(p) for p in all_paths) == len(session.state.evidence)
