"""An entity handle read as several roles, and what a reading may remember (MP23, MPI1).

One job: `EntityHandle` -- which entity (a student, an invoice, an application) and which of its
fields the consistency oracle reads as each declared role -- plus `FieldReading`, the only thing
kept about one value: its VALUE CLASS (`ValueClass`), never the text. A field can be declared
role-specific (a role is allowed to see a different value there); every other field must read the
same for every role. The handle declares a small `vocabulary` of non-personal labels (statuses such
as "pending"), so two roles disagreeing about a status are reported by label, while a name or an
email is only ever reported as `text` / `email`.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from autotester.schema.leak_evidence import contains_personal_shape, validate_url_template
from autotester.schema.multi_role_finding import parse_repro_step
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN

HANDLE_ID_PATTERN = r"^[a-z][a-z0-9_-]{0,31}$"
MAX_ROLES = 12
MAX_FIELDS = 30
Label = Annotated[str, StringConstraints(min_length=1, max_length=40)]


class ValueClass(StrEnum):
    """What kind of value a role saw. `vocabulary` carries a declared label; the rest do not."""

    VOCABULARY = "vocabulary"
    MISSING = "missing"
    EMPTY = "empty"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    NUMBER = "number"
    TEXT_SHORT = "text_short"
    TEXT_LONG = "text_long"


class EntityField(BaseModel):
    """One field of the entity: where to look, and whether roles may legitimately differ."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=HANDLE_ID_PATTERN)
    selector: str = Field(min_length=1, max_length=200)
    role_specific: bool = Field(
        default=False, description="True = roles are allowed to see different values here")


class EntityHandle(BaseModel):
    """An entity produced in a scenario, to be read as each of `roles`."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=HANDLE_ID_PATTERN)
    platform_id: str = Field(pattern=PLATFORM_ID_PATTERN)
    url_template: str
    open_action: str = Field(min_length=3, max_length=200,
                             description="`<verb> <target>` that shows the entity")
    roles: list[str] = Field(min_length=2, max_length=MAX_ROLES)
    fields: list[EntityField] = Field(min_length=1, max_length=MAX_FIELDS)
    vocabulary: list[Label] = Field(
        default_factory=list, max_length=30,
        description="non-personal labels (statuses) that may be named in a finding")

    @model_validator(mode="after")
    def _closed_and_value_free(self) -> EntityHandle:
        validate_url_template(self.url_template)
        parse_repro_step(self.open_action)
        for text in (self.open_action, *self.vocabulary, *(f.selector for f in self.fields)):
            if contains_personal_shape(text):
                raise ValueError("a handle holds personal-looking text; declare patterns only")
        if not all(re.fullmatch(ROLE_ACCOUNT_ID_PATTERN, r) for r in self.roles):
            raise ValueError("roles must be RoleAccount ids")
        if len(set(self.roles)) != len(self.roles):
            raise ValueError("a role is listed twice")
        names = [f.name for f in self.fields]
        if len(set(names)) != len(names):
            raise ValueError("a field is declared twice")
        return self


class FieldReading(BaseModel):
    """What one role saw in one field, reduced to its class (and a label from the vocabulary)."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(pattern=HANDLE_ID_PATTERN)
    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    value_class: ValueClass
    label: Label | None = None

    @model_validator(mode="after")
    def _label_only_for_vocabulary(self) -> FieldReading:
        if (self.label is not None) != (self.value_class is ValueClass.VOCABULARY):
            raise ValueError("a label belongs to the vocabulary class and to nothing else")
        return self

    def describe(self) -> str:
        """`vocabulary:pending` or `email`: what a finding may print."""
        return f"{self.value_class.value}:{self.label}" if self.label else self.value_class.value
