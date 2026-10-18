"""A timed cross-role assertion and the evidence the runner records for it (MP13, MP14).

One job: `CrossRoleAssertion` -- an observer role, a channel (`ui | mailbox | api`), `present |
absent` and `within_s` -- plus `Observation` (what one look at the channel returned) and
`AssertionOutcome` (the verdict, the observed time, the window and the last observation).
An `absent` assertion is a claim about the whole window, so it can only pass after the window
elapsed with no match; a `present` one fails with its window and the last thing seen. The
closed vocabularies are `schema/multi_role_enums.py` (not redefined here); the verdict is local.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autotester.schema.leak_evidence import contains_personal_shape
from autotester.schema.multi_role_enums import AssertChannel, Expectation
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN
from autotester.schema.role_step import STEP_ID_PATTERN

MAX_WINDOW_S = 3600.0
MIN_POLL_S = 0.05
MAX_POLL_S = 60.0
DETAIL_MAX = 200


class AssertVerdict(StrEnum):
    """`not_run` means an earlier step failed, so the assertion was never looked at."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not_run"


class CrossRoleAssertion(BaseModel):
    """What one role must (or must not) see, on one channel, within a window."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=STEP_ID_PATTERN)
    observer_role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    channel: AssertChannel
    expectation: Expectation
    target: str = Field(min_length=1, max_length=200,
                        description="selector, mail subject pattern or API route pattern")
    within_s: float = Field(gt=0, le=MAX_WINDOW_S)
    poll_interval_s: float = Field(default=0.5, ge=MIN_POLL_S, le=MAX_POLL_S)
    after_step: str | None = Field(
        default=None, pattern=STEP_ID_PATTERN,
        description="start looking once this step is done; None = after the last step")

    @field_validator("target")
    @classmethod
    def _no_personal_text(cls, target: str) -> str:
        if contains_personal_shape(target):
            raise ValueError("an assertion target looks like personal data; name a pattern")
        return target


class Observation(BaseModel):
    """One look at a channel: did the target match, and a short description of what was seen."""

    model_config = ConfigDict(extra="forbid")

    matched: bool
    detail: str = Field(default="", max_length=DETAIL_MAX)


class AssertionOutcome(BaseModel):
    """The verdict for one assertion. `observed_s` is seconds from the start of its window."""

    model_config = ConfigDict(extra="forbid")

    assertion_id: str = Field(pattern=STEP_ID_PATTERN)
    observer_role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    channel: AssertChannel
    expectation: Expectation
    within_s: float
    verdict: AssertVerdict
    observed_s: float | None = None
    last_observation: str | None = Field(default=None, max_length=DETAIL_MAX)
    reason: str | None = Field(default=None, max_length=DETAIL_MAX)
