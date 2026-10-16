"""T-179b HG-1 gaps (ISS-t179b-hg1-1/-2): invisible-filler click names and 'close account'-style
phrases are refused under READ_ONLY; ALLOW_WRITES behaviour for them is unchanged."""

from __future__ import annotations

import pytest

from autotester.agents import guards
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.project import Project

FILLERS = ["\u2800", "\u3164", "\u115f", "\u1160", "\uffa0", "\u200b", "\u200d", "\u2060",
           "\ufeff", "\u00ad", "\u200e", " \u2800\u3164 ", "\u2800\u200b\uffa0"]
PHRASES = ["Close account", "Close my account", "Deactivate account", "Terminate account",
           "Cancel account", "Cancel my subscription", "Cancel subscription",
           "Close subscription", "Deactivate subscription", "Terminate subscription",
           "Close membership"]
SAFE = ["Open menu", "Close dialog", "Close account settings"]


def _project(policy: WritePolicy) -> Project:
    return Project(slug="demo", name="Demo", base_url="https://app.test",
                   allowed_domains=["app.test"], write_policy=policy)


def _case(target: str) -> Case:
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="c", steps=[Step(order=1, action=Action.CLICK, target=target)])


@pytest.mark.parametrize("name", FILLERS)
def test_read_only_refuses_invisible_filler_names(name: str) -> None:
    out = guards.write_policy_refusal(_case(name), _project(WritePolicy.READ_ONLY))
    assert out is not None and "unnamed control" in out[1]


@pytest.mark.parametrize("name", [f"\u2800{p}\u3164" for p in PHRASES] + PHRASES)
def test_read_only_refuses_account_closing_phrases(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.READ_ONLY))


@pytest.mark.parametrize("name", SAFE)
def test_read_only_still_allows_ordinary_names(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.READ_ONLY)) is None


@pytest.mark.parametrize("name", ["\u2800", "\u3164", "\u115f", "\u1160", "\uffa0"])
def test_allow_writes_unchanged_for_fillers(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.ALLOW_WRITES)) is None


@pytest.mark.parametrize("name", ["Cancel subscription", "Close subscription",
                                  "Deactivate subscription", "Terminate subscription"])
def test_allow_writes_still_permits_subscription_phrases(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.ALLOW_WRITES)) is None
