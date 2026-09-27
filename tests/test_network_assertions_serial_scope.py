"""AT-578 (found while fixing AT-577, checker verdict 9b0ccb8): `browser/
assertions.py::_network_met` scanned the WHOLE session evidence, not just
the current case's -- on the serial route (one session shared across
cases), an EARLIER case's captured request could silently satisfy a LATER
case's `network` expectation. The assertion-side twin of AT-577. Split from
`test_network_assertions.py` at doctor's 300-line cap; reuses its fakes.
Contract: qa/contracts/network-assertions.md NA3.
"""

from __future__ import annotations

from pathlib import Path

from test_network_assertions import LOGIN, make_case, make_project, session_with_fake_page

from autotester.schema.enums import Action, EvidenceKind, Outcome
from autotester.schema.flowspec import ExpectedState, Step
from autotester.stages.execute import run_case


def test_case_2_network_assertion_is_unmet_when_only_case_1_observed_the_pattern(
    tmp_path: Path,
) -> None:
    """Two cases run back-to-back on ONE shared session (the serial route's
    shape). Case 1 observes the pattern its own step needs; case 2 does not
    observe it at all -- case 2's own `network` assertion must read unmet,
    never satisfied by case 1's earlier, already-drained capture."""
    project = make_project()
    session = session_with_fake_page(tmp_path, project)

    session.observer.responses = [("POST", "https://app.pathlynks.test/api/save", 200)]
    case1_steps = [Step(order=1, action=Action.NAVIGATE, target=LOGIN)]
    result1 = run_case(make_case(case1_steps), session)
    assert result1.outcome is Outcome.COMPLETED
    assert any(e.kind is EvidenceKind.NETWORK and "api/save" in e.path
               for e in result1.evidence)

    session.observer.responses = []  # case 2 observes nothing matching
    case2_steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.ASSERT, target="",
             expected=ExpectedState(network=["/api/save"])),
    ]
    result2 = run_case(make_case(case2_steps), session)

    assert result2.outcome is Outcome.ASSERTION_FAILED, (
        "case 2 must not be satisfied by case 1's earlier network capture"
    )
    asserts = [e for e in result2.evidence
               if e.kind is EvidenceKind.NETWORK and e.path.startswith("assert network")]
    assert len(asserts) == 1
    assert "unmet" in asserts[0].path


def test_case_2_network_assertion_is_met_when_case_2_itself_observes_the_pattern(
    tmp_path: Path,
) -> None:
    """Sibling of the test above: scoping to the current case must not make
    a genuinely-met assertion read as unmet -- case 2 observing its OWN
    matching request still reads met."""
    project = make_project()
    session = session_with_fake_page(tmp_path, project)

    session.observer.responses = [("GET", "https://app.pathlynks.test/api/unrelated", 200)]
    run_case(make_case([Step(order=1, action=Action.NAVIGATE, target=LOGIN)]), session)

    session.observer.responses = [("POST", "https://app.pathlynks.test/api/save", 200)]
    case2_steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.ASSERT, target="",
             expected=ExpectedState(network=["/api/save"])),
    ]
    result2 = run_case(make_case(case2_steps), session)

    assert result2.outcome is Outcome.COMPLETED
    asserts = [e for e in result2.evidence
               if e.kind is EvidenceKind.NETWORK and e.path.startswith("assert network")]
    assert len(asserts) == 1
    assert "met" in asserts[0].path and "unmet" not in asserts[0].path
