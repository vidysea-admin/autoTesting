"""What the network oracles read: captured requests per step and the request budget (MP21, MP22).

One job: the typed input of `stages/oracle_api_error.py` and `stages/oracle_request_budget.py`.
`NetworkSample` is one first-party response (its URL already passed `network_capture`'s redaction),
`StepNetworkLog` is what one role's step produced -- the screen it was on, the repro steps that
lead there, whether the UI showed success and the samples -- and `RequestBudget` is the project's
declared limit. `NetworkLogPort` is the optional seam a role-session port implements to hand the
log over; `network_log_from` is the one place an oracle reads it, and a port without the seam
raises `NetworkLogUnavailable` so the registry reports the oracle `errored` instead of a clean
run that looked at nothing. Nothing here persists: findings carry URL templates, never these URLs.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.schema.leak_evidence import contains_personal_shape
from autotester.schema.multi_role_finding import parse_repro_step
from autotester.schema.oracle_context import OracleContext
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN
from autotester.schema.role_step import STEP_ID_PATTERN

MAX_URL = 500
MAX_INDICATOR = 120


class NetworkLogUnavailable(LookupError):
    """The role-session port does not expose a network log, so the oracle cannot run."""


class RequestBudget(BaseModel):
    """The declared limits: requests per screen and the fastest allowed polling interval."""

    model_config = ConfigDict(extra="forbid")

    max_requests_per_screen: int = Field(gt=0, strict=True)
    min_poll_interval_s: float = Field(gt=0, le=3600)
    min_repeats_for_polling: int = Field(
        default=3, ge=2, strict=True,
        description="the same endpoint requested this often on one screen counts as polling")


class NetworkSample(BaseModel):
    """One first-party response, `t_s` seconds from the start of the run."""

    model_config = ConfigDict(extra="forbid")

    method: str = Field(pattern=r"^[A-Z]{3,7}$")
    url: str = Field(min_length=1, max_length=MAX_URL)
    status: int = Field(ge=100, le=599, strict=True)
    t_s: float = Field(ge=0)


class StepNetworkLog(BaseModel):
    """The requests one role's step made while on one screen."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(pattern=STEP_ID_PATTERN)
    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    platform_id: str = Field(pattern=PLATFORM_ID_PATTERN)
    screen_url: str = Field(min_length=1, max_length=MAX_URL)
    repro_steps: list[str] = Field(min_length=1, max_length=50)
    success_indicator: str | None = Field(
        default=None, min_length=1, max_length=MAX_INDICATOR,
        description="the selector or label of the success element the UI showed; None = no success")
    samples: list[NetworkSample] = Field(default_factory=list)

    @field_validator("repro_steps")
    @classmethod
    def _replayable(cls, steps: list[str]) -> list[str]:
        for step in steps:
            parse_repro_step(step)
        return steps

    @model_validator(mode="after")
    def _no_personal_text(self) -> StepNetworkLog:
        for text in (self.success_indicator or "", *self.repro_steps):
            if contains_personal_shape(text):
                raise ValueError("network log text looks like personal data")
        return self


@runtime_checkable
class NetworkLogPort(Protocol):
    """The seam a role-session port adds so the network oracles can read what it captured."""

    def network_log(self) -> list[StepNetworkLog]:
        """Every step's captured first-party requests, in the order the steps ran."""

    def request_budget(self) -> RequestBudget | None:
        """The project's declared budget, or None when it declared none."""


def network_log_from(context: OracleContext) -> tuple[list[StepNetworkLog], RequestBudget | None]:
    """The log and budget of `context.port`; raise `NetworkLogUnavailable` when it has none."""
    port = context.port
    if not isinstance(port, NetworkLogPort):
        raise NetworkLogUnavailable("the role-session port exposes no network log")
    return port.network_log(), port.request_budget()
