"""A state probe: what to read, as whom, and what change the action must leave behind (MP33).

One job: `StateProbe` -- a counter, list or status reader (a selector or a first-party API route
pattern), the action that should change it, the roles that read it and the expected change -- plus
the two closed vocabularies only this probe uses: `ReaderKind` and `StateFault`. A counter or list
carries an integer `expected_delta`; a status carries a `schema/flowspec.py::ExpectedState`
(`visible_text` must show, `absent_text` must not). The reader URL is a placeholder template and no
free-text field may look like personal data, so a probe can be committed and a finding built from
it never holds a reader's page (MPI1). The enums are local on purpose: `multi_role_enums.py` is
T-207's alone (MPI3).
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.schema.flowspec import ExpectedState
from autotester.schema.leak_evidence import contains_personal_shape, validate_url_template
from autotester.schema.multi_role_enums import AssertChannel
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN
from autotester.schema.role_step import STEP_ID_PATTERN, RoleStep


class ReaderKind(StrEnum):
    """`counter` and `list` read a number (a count of items for a list); `status` reads a state."""

    COUNTER = "counter"
    LIST = "list"
    STATUS = "status"


class StateFault(StrEnum):
    """How a change failed. The values appear verbatim in the finding title."""

    MISSING = "missing"
    WRONG_SIZE = "wrong_size"
    NOT_PERSISTED = "not_persisted"
    UNREADABLE = "unreadable"


class StateProbe(BaseModel):
    """One state reader, the action that changes it, and who must see the change."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=STEP_ID_PATTERN)
    platform_id: str = Field(pattern=PLATFORM_ID_PATTERN)
    kind: ReaderKind
    reader_channel: AssertChannel = Field(description="`ui` selector or `api` route pattern")
    reader_target: str = Field(min_length=1, max_length=200)
    reader_url: str = Field(min_length=1, description="page readers open; ids as {x}")
    action: RoleStep = Field(description="the step, as the actor role, that should change it")
    reader_role_ids: list[str] = Field(min_length=1, max_length=20)
    expected_delta: int | None = Field(default=None, strict=True)
    expected_state: ExpectedState | None = None

    @field_validator("reader_channel")
    @classmethod
    def _not_a_mailbox(cls, channel: AssertChannel) -> AssertChannel:
        if channel is AssertChannel.MAILBOX:
            raise ValueError("a state reader reads a page or an API, not a mailbox")
        return channel

    @field_validator("reader_target")
    @classmethod
    def _no_personal_text(cls, target: str) -> str:
        if contains_personal_shape(target):
            raise ValueError("a reader target looks like personal data; name a pattern")
        return target

    @field_validator("reader_url")
    @classmethod
    def _template(cls, url: str) -> str:
        return validate_url_template(url)

    @field_validator("reader_role_ids")
    @classmethod
    def _roles(cls, roles: list[str]) -> list[str]:
        if len(set(roles)) != len(roles):
            raise ValueError("reader_role_ids must be unique")
        if not all(re.fullmatch(ROLE_ACCOUNT_ID_PATTERN, r) for r in roles):
            raise ValueError("reader_role_ids must be RoleAccount ids")
        return roles

    @model_validator(mode="after")
    def _expectation_matches_kind(self) -> StateProbe:
        if self.kind is ReaderKind.STATUS:
            state = self.expected_state
            if self.expected_delta is not None or state is None:
                raise ValueError("a status probe takes expected_state and no expected_delta")
            if not (state.visible_text or state.absent_text):
                raise ValueError("a status probe's expected_state needs visible or absent text")
        else:
            if self.expected_state is not None or not self.expected_delta:
                raise ValueError("a counter or list probe takes a non-zero expected_delta only")
        return self
