"""One multi-role finding with the repro that survives masking (MP7, MP10).

One job: `MultiRoleFinding` -- class, role, platform, URL template, ordered action steps and the
count, enough for a second run to reproduce it without any third-party data. There is no priority
field: the priority is a pure function of the class (`stages/finding_priority.py`), so no caller can
store a lower one. A step is `<verb> <target>` with the verb from the closed `ReproVerb` set; free
text that looks like an email or a phone number is refused.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from autotester.schema.leak_evidence import (
    LeakEvidence,
    contains_personal_shape,
    validate_url_template,
)
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.platform import PLATFORM_ID_PATTERN

FINDING_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{1,63}$"


class ReproVerb(StrEnum):
    """The actions a recorded repro step may start with."""

    LOGIN = "login"
    GOTO = "goto"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    SUBMIT = "submit"


def parse_repro_step(step: str) -> tuple[ReproVerb, str]:
    """Split `<verb> <target>`; raise ValueError for an unknown verb or an empty target."""
    verb, _, target = step.strip().partition(" ")
    try:
        parsed = ReproVerb(verb)
    except ValueError:
        raise ValueError(f"unknown repro verb: {verb!r}") from None
    if not target.strip():
        raise ValueError("a repro step needs a target")
    return parsed, target.strip()


Step = Annotated[str, StringConstraints(min_length=3, max_length=200)]


class MultiRoleFinding(BaseModel):
    """A defect found across roles. Leak evidence is required for a data-leak finding."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    finding_id: str = Field(pattern=FINDING_ID_PATTERN)
    finding_class: FindingClass
    title: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=64)
    platform_id: str = Field(pattern=PLATFORM_ID_PATTERN)
    url_template: str
    steps: list[Step] = Field(min_length=1, max_length=50, description="ordered repro actions")
    count: int = Field(ge=0, strict=True)
    oracle: OracleName | None = None
    leak_evidence: LeakEvidence | None = None

    @model_validator(mode="after")
    def _repro_is_replayable_and_value_free(self) -> MultiRoleFinding:
        validate_url_template(self.url_template)
        for step in self.steps:
            parse_repro_step(step)
        for text in (self.title, self.role, *self.steps):
            if contains_personal_shape(text):
                raise ValueError("finding text looks like personal data")
        if self.finding_class is FindingClass.DATA_LEAK:
            if self.leak_evidence is None:
                raise ValueError("a data-leak finding needs leak_evidence")
            if self.count != self.leak_evidence.foreign_row_count:
                raise ValueError("count must equal the leak evidence's foreign row count")
        return self
