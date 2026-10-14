"""A logged-out-precondition case runs in the wiped entry profile, never the signed-in one."""

from __future__ import annotations

import pytest

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.stages.entry_precondition import requires_unauthenticated
from autotester.stages.run_launcher import is_entry_case

PROJECT = Project(slug="demo", name="Demo", base_url="https://demo.test/signin",
                  allowed_domains=["demo.test"])


def _case(case_class: CaseClass, target: str, preconditions: list[str] | None = None) -> Case:
    return Case(project="demo", flow_id="f", kind=CaseKind.EDGE, case_class=case_class,
                title="t", preconditions=preconditions or [],
                steps=[Step(order=1, action=Action.NAVIGATE, target=target)])


def test_deeplink_unauth_class_is_an_entry_case_though_it_navigates_elsewhere() -> None:
    assert is_entry_case(_case(CaseClass.DEEPLINK_UNAUTH, "https://demo.test/dashboard"), PROJECT)


@pytest.mark.parametrize("text", [
    "User is not logged in", "Visitor is logged out", "Unauthenticated session",
    "no active session", "opened without being authenticated"])
def test_logged_out_preconditions_are_entry_cases(text: str) -> None:
    case = _case(CaseClass.HAPPY, "https://demo.test/x", [text])
    assert requires_unauthenticated(case) and is_entry_case(case, PROJECT)


@pytest.mark.parametrize("text", ["User is authenticated", "logged in as admin", "has a session"])
def test_signed_in_preconditions_stay_normal_cases(text: str) -> None:
    case = _case(CaseClass.HAPPY, "https://demo.test/x", [text])
    assert not requires_unauthenticated(case) and not is_entry_case(case, PROJECT)


def test_existing_base_url_entry_rule_unchanged() -> None:
    assert is_entry_case(_case(CaseClass.HAPPY, PROJECT.base_url), PROJECT)
