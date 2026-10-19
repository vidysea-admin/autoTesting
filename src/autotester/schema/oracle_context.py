"""The oracle interface: what an oracle is handed, what the run reports about each oracle (MP15).

One job: the contract between the cross-role runner and the G11 oracle builders (T-212..T-220).

HOW TO WRITE AN ORACLE. Create `stages/oracle_<name>.py`, where `<name>` is the value of one
`OracleName` (`schema/multi_role_enums.py`), and expose exactly:

    def run(context: OracleContext) -> list[MultiRoleFinding]: ...

The registry (`stages/oracle_registry.py`) imports the module by name, calls `run` once per
scenario and records the outcome per oracle; nothing else to register, and the registry file is
never edited by an oracle unit. Rules the registry relies on:
  * `run` returns `MultiRoleFinding`s (`schema/multi_role_finding.py`); anything else marks the
    oracle `errored`. Priority is `stages/finding_priority.py::priority_for(finding_class)`, never
    set by the oracle. An exception is reported as its type name only, never its message, so a
    leak oracle cannot spill a page through an error.
  * `context.port` is the live `RoleSessionPort` (perform a step, observe a channel as a role).
    It is excluded from serialisation. Leak/privilege oracles use it deterministically and never
    send a page to a model (MPI1).
  * `context.assertion_outcomes` and `context.steps` are what the scenario already did, so an
    oracle can read the run without re-driving it.
  * `context.declarations` (`schema/oracle_declarations.py`) carries the declaration of an oracle
    that needs one (credential policy, paid paths). Use it first; the run-dir file is the fallback.
A module that is absent is `not built`; one that exists but cannot be imported or has no `run`
is `errored`. Neither is ever dropped from the summary, which must name every `OracleName`.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.cross_role_assertion import AssertionOutcome, CrossRoleAssertion, Observation
from autotester.schema.multi_role_enums import OracleName
from autotester.schema.oracle_declarations import OracleDeclarations
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN
from autotester.schema.role_step import RoleStep


class OracleState(StrEnum):
    """The values are the wording of the contract (MP15, MP31): `not built`, `not run`."""

    RAN = "ran"
    NOT_BUILT = "not built"
    NOT_RUN = "not run"
    ERRORED = "errored"


@runtime_checkable
class RoleSessionPort(Protocol):
    """The seam T-210's `multi_role_session` plugs into; fakes implement it in tests."""

    def perform(self, step: RoleStep) -> None:
        """Do the step as `step.role_id`; raise on failure."""

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        """Look at `assertion.channel` as `assertion.observer_role_id`, once."""


class OracleStatus(BaseModel):
    """One oracle's line in the run summary."""

    model_config = ConfigDict(extra="forbid")

    oracle: OracleName
    module: str
    state: OracleState
    reason: str | None = Field(default=None, max_length=200)
    finding_count: int = Field(default=0, ge=0)


class OracleRunSummary(BaseModel):
    """Every G11 oracle exactly once; an omitted oracle is a validation error (MP15)."""

    model_config = ConfigDict(extra="forbid")

    statuses: list[OracleStatus]

    @model_validator(mode="after")
    def _names_every_oracle(self) -> OracleRunSummary:
        if sorted(s.oracle for s in self.statuses) != sorted(OracleName):
            raise ValueError("the summary must name every oracle exactly once")
        return self


class OracleContext(BaseModel):
    """What one oracle run is handed. Serialisable fields only, plus the live port."""

    # `declarations` may hold a `{{SECRET:KEY}}` placeholder or a canary: a validation error on the
    # context must not echo the offending input.
    model_config = ConfigDict(
        extra="forbid", arbitrary_types_allowed=True, hide_input_in_errors=True)

    project_slug: str = Field(min_length=1, max_length=64)
    run_dir: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1, max_length=64)
    role_ids: list[str] = Field(default_factory=list)
    platform_ids: list[str] = Field(default_factory=list)
    steps: list[RoleStep] = Field(default_factory=list)
    assertion_outcomes: list[AssertionOutcome] = Field(default_factory=list)
    port: RoleSessionPort | None = Field(default=None, exclude=True, repr=False)
    declarations: OracleDeclarations = Field(
        default_factory=OracleDeclarations, exclude=True, repr=False,
        description="typed per-oracle declarations; an oracle falls back to its run-dir file")

    @model_validator(mode="after")
    def _ids_are_ids(self) -> OracleContext:
        for rid in self.role_ids:
            if not re.fullmatch(ROLE_ACCOUNT_ID_PATTERN, rid):
                raise ValueError("role_ids must be RoleAccount ids")
        for pid in self.platform_ids:
            if not re.fullmatch(PLATFORM_ID_PATTERN, pid):
                raise ValueError("platform_ids must be Platform ids")
        return self
