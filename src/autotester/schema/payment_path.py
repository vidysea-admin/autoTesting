"""The paid paths a project declares, and what the payment oracle reports about each (MP28).

One job: `PaymentPath` (how to reach the checkout, an optional coupon, the step that opens the
gateway page, and the marker that proves the gateway page is showing), `PaymentDeclaration`
(the paths) and `PathReport` (reached / not reached / unobserved per path, the coupon outcome, and
the step the oracle stopped after). The oracle stops the moment the gateway marker is seen. The only
things allowed after that are `test_mode_steps`, which a path may carry ONLY when it declares
`provider_test_mode` (a provider sandbox where no real charge exists); a real-money charge is never
completed (MPI4). Values are selectors, repro steps and `{{SECRET:KEY}}` placeholders only.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.schema.leak_evidence import contains_personal_shape
from autotester.schema.multi_role_finding import parse_repro_step
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN
from autotester.schema.role_step import STEP_ID_PATTERN

MAX_PATHS = 12
MAX_PHASE_STEPS = 20
PAYMENT_FILE = "payment_paths.json"


class GatewayState(StrEnum):
    """`unobserved` is never read as "not reached": the page could not be looked at."""

    REACHED = "reached"
    NOT_REACHED = "not_reached"
    UNOBSERVED = "unobserved"


class CouponState(StrEnum):
    """`not_reached` means the path never got as far as the coupon step."""

    NOT_DECLARED = "not_declared"
    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    UNOBSERVED = "unobserved"
    NOT_REACHED = "not_reached"


def _replayable(steps: list[str]) -> list[str]:
    for step in steps:
        parse_repro_step(step)
    return steps


class PaymentPath(BaseModel):
    """One paid path, declared as four phases that the oracle performs in order."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=STEP_ID_PATTERN, max_length=30)
    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    platform_id: str | None = Field(default=None, pattern=PLATFORM_ID_PATTERN)
    steps: list[str] = Field(default_factory=list, max_length=MAX_PHASE_STEPS,
                             description="reach the page that offers payment")
    coupon_steps: list[str] = Field(default_factory=list, max_length=MAX_PHASE_STEPS)
    coupon_marker: str | None = Field(default=None, min_length=1, max_length=150)
    gateway_steps: list[str] = Field(min_length=1, max_length=MAX_PHASE_STEPS,
                                     description="the step(s) that open the gateway page")
    gateway_marker: str = Field(min_length=1, max_length=150,
                                description="selector or URL pattern of the gateway page")
    provider_test_mode: bool = False
    test_mode_steps: list[str] = Field(default_factory=list, max_length=MAX_PHASE_STEPS)
    within_s: float = Field(default=5.0, gt=0, le=60)

    @field_validator("steps", "coupon_steps", "gateway_steps", "test_mode_steps")
    @classmethod
    def _steps_replay(cls, steps: list[str]) -> list[str]:
        return _replayable(steps)

    @field_validator("coupon_marker", "gateway_marker")
    @classmethod
    def _marker_is_not_personal(cls, marker: str | None) -> str | None:
        if marker is not None and contains_personal_shape(marker):
            raise ValueError("a marker looks like personal data; name the element instead")
        return marker

    @model_validator(mode="after")
    def _coupon_and_test_mode_are_consistent(self) -> PaymentPath:
        if bool(self.coupon_steps) != (self.coupon_marker is not None):
            raise ValueError("coupon_steps and coupon_marker go together")
        if self.test_mode_steps and not self.provider_test_mode:
            raise ValueError("test_mode_steps need provider_test_mode: no step runs on a gateway "
                             "page outside a provider sandbox")
        return self


class PaymentDeclaration(BaseModel):
    """The project's declared paid paths."""

    model_config = ConfigDict(extra="forbid")

    paths: list[PaymentPath] = Field(max_length=MAX_PATHS)

    @model_validator(mode="after")
    def _unique_ids(self) -> PaymentDeclaration:
        if len({p.id for p in self.paths}) != len(self.paths):
            raise ValueError("path ids must be unique")
        return self


class PathReport(BaseModel):
    """What the oracle saw on one path. Counts and states, no URL, page text or value."""

    model_config = ConfigDict(extra="forbid")

    path_id: str = Field(pattern=STEP_ID_PATTERN)
    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    gateway: GatewayState
    coupon: CouponState
    performed_steps: int = Field(ge=0)
    stopped_at_gateway: bool
    test_mode_steps_run: int = Field(default=0, ge=0)
