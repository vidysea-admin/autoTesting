"""One role-tagged step of a cross-role scenario, and how it went (MP13).

One job: `RoleStep` -- which role account performs one action -- and `StepOutcome`, the runner's
record of it. The action is the repro vocabulary of `schema/multi_role_finding.py::ReproVerb`
(`<verb> <target>`), so a scenario step and a finding's repro step are the same concept and a step
log can be pasted into a finding. Secrets appear only as `{{SECRET:KEY}}` placeholders; text that
looks like an email or a phone number is refused. Which browser context performs the step is the
session port's business (`schema/oracle_context.py::RoleSessionPort`), not this model's.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autotester.schema.leak_evidence import contains_personal_shape
from autotester.schema.multi_role_finding import parse_repro_step
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN

STEP_ID_PATTERN = r"^[a-z][a-z0-9_-]{0,63}$"


class StepState(StrEnum):
    """How one step ended. `not_run` is a step skipped because an earlier one failed."""

    OK = "ok"
    FAILED = "failed"
    NOT_RUN = "not_run"


class RoleStep(BaseModel):
    """An action performed as one named role account."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=STEP_ID_PATTERN)
    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN, description="the RoleAccount that acts")
    action: str = Field(min_length=3, max_length=200, description="`<verb> <target>`")

    @field_validator("action")
    @classmethod
    def _replayable_and_value_free(cls, action: str) -> str:
        parse_repro_step(action)
        if contains_personal_shape(action):
            raise ValueError("a step action looks like personal data; use a {{SECRET:KEY}} key")
        return action


class StepOutcome(BaseModel):
    """What the runner recorded for one step: the error is an exception type, never its message."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(pattern=STEP_ID_PATTERN)
    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    state: StepState
    error: str | None = Field(default=None, max_length=200)
