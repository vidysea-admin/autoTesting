"""One cell of the per-role negative-input matrix (MP32).

One job: `ProbeCell` -- what happened when one role account submitted one violating (or repeated)
input to one form -- and `InputRule`, the closed set of declared rules a probe can break. A cell
is recorded for every probe whether the product held the line or not, so a test can assert the
whole matrix and not only the failures; a finding is made only from a `breached` cell. A cell
never holds the submitted value: the rule, the field name and the case class are enough to replay.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.enums import CaseClass
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN


class InputRule(StrEnum):
    """The `FieldConstraints` rules (plus required and idempotent submit) a probe can break."""

    REQUIRED = "required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    MIN = "min"
    MAX = "max"
    DOUBLE_SUBMIT = "double_submit"


class ProbeCell(BaseModel):
    """`breached` is True when the product accepted the input, or created a second record."""

    model_config = ConfigDict(extra="forbid")

    form_id: str = Field(min_length=1, max_length=64)
    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    field: str | None = Field(default=None, max_length=64, description="None for a double submit")
    rule: InputRule
    case_class: CaseClass
    breached: bool
