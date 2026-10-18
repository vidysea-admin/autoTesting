"""A cross-role scenario and the result of running it (MP13-MP15).

One job: `CrossRoleScenario` -- the roles taking part, the role-tagged steps in order, and the timed
assertions -- and `ScenarioResult`, the runner's record: step outcomes, assertion outcomes, the
oracle summary and the findings the oracles returned. A scenario that names a role it does not list,
an assertion that observes as an unlisted role, or an `after_step` that does not exist fails at
load, not mid-run. Product-specific roles, URLs and labels never appear here: the role ids are
whatever the onboarder gave the `RoleAccount`s.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.cross_role_assertion import (
    AssertionOutcome,
    AssertVerdict,
    CrossRoleAssertion,
)
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleRunSummary
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN
from autotester.schema.role_step import STEP_ID_PATTERN, RoleStep, StepOutcome, StepState


def _unique(values: list[str], what: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{what} must be unique")


class CrossRoleScenario(BaseModel):
    """Role A acts, role B (or a mailbox, or an API) is expected to show it, within a window."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=STEP_ID_PATTERN)
    title: str = Field(min_length=1, max_length=200)
    roles: list[str] = Field(min_length=1, max_length=16, description="RoleAccount ids taking part")
    steps: list[RoleStep] = Field(min_length=1, max_length=200)
    assertions: list[CrossRoleAssertion] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def _references_resolve(self) -> CrossRoleScenario:
        _unique(self.roles, "roles")
        _unique([s.id for s in self.steps], "step ids")
        _unique([a.id for a in self.assertions], "assertion ids")
        for rid in self.roles:
            if not re.fullmatch(ROLE_ACCOUNT_ID_PATTERN, rid):
                raise ValueError("roles must be RoleAccount ids")
        for step in self.steps:
            if step.role_id not in self.roles:
                raise ValueError(f"step {step.id} names a role the scenario does not list")
        step_ids = {s.id for s in self.steps}
        for a in self.assertions:
            if a.observer_role_id not in self.roles:
                raise ValueError(f"assertion {a.id} observes as a role the scenario does not list")
            if a.after_step is not None and a.after_step not in step_ids:
                raise ValueError(f"assertion {a.id} starts after an unknown step")
        return self


class ScenarioResult(BaseModel):
    """Everything one scenario run recorded; `passed` = every step ok and every assertion met."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    steps: list[StepOutcome]
    assertions: list[AssertionOutcome]
    oracle_summary: OracleRunSummary
    findings: list[MultiRoleFinding] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True only when no step failed or was skipped and every assertion passed."""
        return (all(s.state is StepState.OK for s in self.steps)
                and all(a.verdict is AssertVerdict.PASSED for a in self.assertions))
