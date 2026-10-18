"""A form to probe with negative input, once per role account that reaches it (MP32).

One job: `NegativeInputForm` -- the flow and fields (reused from `schema/flowspec.py`, so the
declared `FieldConstraints` are the rules), the role accounts whose permitted surface reaches the
form, the page and the controls the oracle drives, and one valid value per field (the oracle
breaks one field at a time). Values are test-account data or `{{SECRET:KEY}}` placeholders; a
value that looks like an email or a phone number is refused (MPI1), as in `RoleStep`.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.flowspec import Flow, InputField
from autotester.schema.leak_evidence import contains_personal_shape, validate_url_template
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN


class NegativeInputForm(BaseModel):
    """`rejection_target` matches while the product shows the form refused the input;
    `duplicate_target` matches only once a second record exists (None = no double-submit probe)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    platform_id: str = Field(pattern=PLATFORM_ID_PATTERN)
    flow: Flow
    fields: list[InputField] = Field(min_length=1)
    role_ids: list[str] = Field(min_length=1, description="roles whose surface reaches the form")
    url_template: str
    submit_target: str = Field(min_length=1, max_length=200)
    rejection_target: str = Field(min_length=1, max_length=200)
    duplicate_target: str | None = Field(default=None, min_length=1, max_length=200)
    valid_values: dict[str, str]

    @model_validator(mode="after")
    def _well_formed(self) -> NegativeInputForm:
        validate_url_template(self.url_template)
        names = [f.name for f in self.fields]
        if len(set(names)) != len(names):
            raise ValueError("field names must be unique")
        if set(self.valid_values) != set(names):
            raise ValueError("valid_values needs exactly one value per field")
        for rid in self.role_ids:
            if not re.fullmatch(ROLE_ACCOUNT_ID_PATTERN, rid):
                raise ValueError("role_ids must be RoleAccount ids")
        if any(contains_personal_shape(v) for v in self.valid_values.values()):
            raise ValueError("a valid value looks like personal data; use a {{SECRET:KEY}} key")
        return self
