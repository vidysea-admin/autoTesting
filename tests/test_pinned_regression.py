"""AT-585 / T-184 — a known bug becomes a PINNED Case that runs in every
regression run and cannot be pruned.

Contract this fixes: stages/issues.py used to only emit Excel rows (VL5/VL6);
there was no path from a confirmed `Issue` to a `Case`, and REGRESSION_ANCHOR
(stages/expand.py) only ever replays a flow's happy path. This does not open
`CaseClass` (D-005/D-014: "CaseClass stays closed") — pinning is a marker on
`Case`, not a new taxonomy member. It is also NOT the p0-p3 priority system —
that is T-178's job; see the module docstring on `Case.pinned` for the planned
subsumption.

Every regression run already runs every case on file (`ProjectStore.list_cases()`
via `routes_runs.py::trigger_run` — there is no run-time filtering to bypass),
so "included in every regression run" falls out of `add_case` for free. The
gap this file is red against is (1) no issue->case constructor exists, and
(2) nothing stops `delete_case` from pruning a pinned case.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, IssueCategory, Severity
from autotester.schema.flowspec import Step
from autotester.schema.issue import Issue
from autotester.stages.issues import pin_issue_as_case
from autotester.store.project_store import PinnedCaseError, ProjectStore


def a_repro_steps() -> list[Step]:
    return [
        Step(order=1, action=Action.NAVIGATE, target="/signup"),
        Step(order=2, action=Action.FILL, target="#email", value="a@b.com"),
        Step(order=3, action=Action.CLICK, target="#google-sign-in"),
        Step(order=4, action=Action.ASSERT, target="#email-field", value="a@b.com"),
    ]


def an_issue(**kw) -> Issue:
    return Issue(
        project=kw.pop("project", "erp"), source_id=kw.pop("source_id", "src_1"),
        recording_label=kw.pop("recording_label", "signup.mp4"), at_s=kw.pop("at_s", 12.0),
        screen=kw.pop("screen", "Signup"),
        title=kw.pop("title", "Google sign-in drops the data filled at signup"),
        what_is_wrong=kw.pop(
            "what_is_wrong", "fields filled before the Google redirect are gone on return"),
        category=kw.pop("category", IssueCategory.OTHER),
        severity=kw.pop("severity", Severity.S1),
        **kw,
    )


# -- the missing constructor: Issue -> pinned Case ---------------------------

def test_pin_issue_as_case_marks_it_pinned_and_traces_to_the_issue() -> None:
    issue = an_issue()

    case = pin_issue_as_case(issue, flow_id="flow_signup", steps=a_repro_steps())

    assert case.pinned is True
    assert case.pinned_issue_id == issue.id


def test_the_pinned_case_stays_inside_the_closed_taxonomy() -> None:
    """D-005/D-014: CaseClass stays closed -- Issue is a separate artifact.
    Pinning must not invent a new CaseClass member; it reuses the existing
    ANCHOR bucket (the taxonomy's own "must survive every regression run"
    class), same as the auto-generated happy-path anchor."""
    case = pin_issue_as_case(an_issue(), flow_id="flow_signup", steps=a_repro_steps())

    assert case.case_class is CaseClass.REGRESSION_ANCHOR
    assert case.kind is CaseKind.ANCHOR


def test_the_pinned_case_carries_the_confirmed_repro_steps_not_a_guess() -> None:
    steps = a_repro_steps()
    case = pin_issue_as_case(an_issue(), flow_id="flow_signup", steps=steps)

    assert case.steps == steps


def test_the_pinned_case_title_and_rationale_name_the_bug() -> None:
    issue = an_issue(title="Google sign-in drops the data filled at signup")
    case = pin_issue_as_case(issue, flow_id="flow_signup", steps=a_repro_steps())

    assert "Google sign-in drops the data filled at signup" in case.title
    assert issue.id in case.rationale


def test_severity_carries_over_from_the_issue() -> None:
    case = pin_issue_as_case(an_issue(severity=Severity.S1), flow_id="f", steps=a_repro_steps())

    assert case.severity is Severity.S1


# -- schema invariant: a pinned_issue_id without pinned=True is refused ------

def test_pinned_issue_id_without_the_pinned_flag_is_rejected() -> None:
    """The marker and the traceability field must not go out of sync -- a
    caller cannot set the trace without also setting the flag."""
    with pytest.raises(ValidationError):
        Case(
            project="erp", flow_id="f", kind=CaseKind.ANCHOR,
            case_class=CaseClass.REGRESSION_ANCHOR, title="x",
            pinned=False, pinned_issue_id="iss_123",
        )


# -- included in every regression run: it is just another case on file ------

def test_a_pinned_case_is_on_file_like_any_other_case(tmp_path) -> None:
    store = ProjectStore("erp", tmp_path)
    case = pin_issue_as_case(an_issue(), flow_id="flow_signup", steps=a_repro_steps())

    store.add_case(case)

    assert case.id in {c.id for c in store.list_cases()}


# -- cannot be pruned ---------------------------------------------------------

def test_deleting_a_pinned_case_is_refused(tmp_path) -> None:
    store = ProjectStore("erp", tmp_path)
    case = pin_issue_as_case(an_issue(), flow_id="flow_signup", steps=a_repro_steps())
    store.add_case(case)

    with pytest.raises(PinnedCaseError):
        store.delete_case(case.id)

    assert case.id in {c.id for c in store.list_cases()}


def test_an_unpinned_case_still_deletes_normally(tmp_path) -> None:
    """The guard must not regress ordinary case deletion (AT-057's onboarding
    path relies on it)."""
    store = ProjectStore("erp", tmp_path)
    ordinary = Case(
        project="erp", flow_id="f", kind=CaseKind.BEST,
        case_class=CaseClass.HAPPY, title="ordinary happy path",
    )
    store.add_case(ordinary)

    assert store.delete_case(ordinary.id) is True
    assert ordinary.id not in {c.id for c in store.list_cases()}
