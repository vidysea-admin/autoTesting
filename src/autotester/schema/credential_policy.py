"""What a project declares about its password rules and its credential mail (MP27).

One job: the shapes the credential-policy oracle (`stages/oracle_credential_policy.py`) reads --
`PasswordRules` (the rules the product says it enforces), `PolicyFlow` (one create or reset form to
probe: how to reach it, which field takes the new password, what shows it was accepted) and
`CredentialPolicy` (rules, flows, and which mailbox assertions may legitimately carry a token).
Every value here is a selector, a repro step or a KEY NAME: no password, address or token value is
a field, and a reuse probe names the key of the previous password, never its value. The closed
vocabularies live here, not in `schema/multi_role_enums.py` (MPI3).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.schema.leak_evidence import contains_personal_shape, validate_url_template
from autotester.schema.mailbox_ref import SecretKey
from autotester.schema.multi_role_finding import parse_repro_step
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN
from autotester.schema.role_step import STEP_ID_PATTERN

MAX_FLOWS = 8
MAX_PROBES = 40
MAX_FLOW_STEPS = 20
POLICY_FILE = "credential_policy.json"


class PasswordRule(StrEnum):
    """The rule names a finding reports. The value is what the report says, never a password."""

    MIN_LENGTH = "min_length"
    REQUIRE_UPPER = "require_upper"
    REQUIRE_LOWER = "require_lower"
    REQUIRE_DIGIT = "require_digit"
    REQUIRE_SYMBOL = "require_symbol"
    NO_REUSE = "no_reuse"


class MailRule(StrEnum):
    """The rule a credential-bearing mail breaks."""

    CREDENTIAL_IN_PLAIN_MAIL = "credential_in_plain_mail"


class FlowKind(StrEnum):
    """Which password form is probed."""

    CREATE = "create"
    RESET = "reset"


class PasswordRules(BaseModel):
    """The password rules the product declares; a rule left at its default is not probed."""

    model_config = ConfigDict(extra="forbid")

    min_length: int | None = Field(default=None, ge=4, le=128, strict=True)
    require_upper: bool = False
    require_lower: bool = False
    require_digit: bool = False
    require_symbol: bool = False
    previous_password_key: SecretKey | None = Field(
        default=None, description="KEY of a password the product must refuse to accept again")

    @model_validator(mode="after")
    def _a_short_password_can_still_meet_every_class(self) -> PasswordRules:
        classes = sum((self.require_upper, self.require_lower, self.require_digit,
                       self.require_symbol))
        if self.min_length is not None and self.min_length <= classes:
            raise ValueError("min_length must exceed the number of required character classes, "
                             "or a too-short probe cannot meet them")
        return self

    def declared(self) -> list[PasswordRule]:
        """The declared rules, in a fixed order."""
        out = [PasswordRule.MIN_LENGTH] if self.min_length is not None else []
        flags = ((self.require_upper, PasswordRule.REQUIRE_UPPER),
                 (self.require_lower, PasswordRule.REQUIRE_LOWER),
                 (self.require_digit, PasswordRule.REQUIRE_DIGIT),
                 (self.require_symbol, PasswordRule.REQUIRE_SYMBOL))
        out += [rule for on, rule in flags if on]
        if self.previous_password_key is not None:
            out.append(PasswordRule.NO_REUSE)
        return out


class PolicyFlow(BaseModel):
    """One create or reset form: reach it, type a candidate password, submit, look for success."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=STEP_ID_PATTERN, max_length=30)
    kind: FlowKind
    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    platform_id: str | None = Field(default=None, pattern=PLATFORM_ID_PATTERN)
    page: str = Field(default="/", description="URL template of the form, ids as placeholders")
    open_steps: list[str] = Field(default_factory=list, max_length=MAX_FLOW_STEPS)
    password_field: str = Field(min_length=1, max_length=60, description="selector")
    submit_step: str = Field(min_length=3, max_length=200, description="`<verb> <target>`")
    accepted_marker: str = Field(min_length=1, max_length=150,
                                 description="selector that appears only when the form succeeded")
    restore_steps: list[str] = Field(default_factory=list, max_length=MAX_FLOW_STEPS,
                                     description="put the account back after an accepted probe")
    within_s: float = Field(default=3.0, gt=0, le=60)

    @field_validator("page")
    @classmethod
    def _page_is_a_template(cls, page: str) -> str:
        return validate_url_template(page)

    @field_validator("open_steps", "restore_steps")
    @classmethod
    def _steps_replay(cls, steps: list[str]) -> list[str]:
        for step in steps:
            parse_repro_step(step)
        return steps

    @field_validator("password_field", "accepted_marker")
    @classmethod
    def _selector_is_not_personal(cls, selector: str) -> str:
        if contains_personal_shape(selector):
            raise ValueError("a selector looks like personal data; name the element instead")
        return selector

    @field_validator("submit_step")
    @classmethod
    def _submit_replays(cls, step: str) -> str:
        parse_repro_step(step)
        return step


class CredentialPolicy(BaseModel):
    """Everything the credential-policy oracle needs, declared by the project."""

    model_config = ConfigDict(extra="forbid")

    rules: PasswordRules = Field(default_factory=PasswordRules)
    flows: list[PolicyFlow] = Field(default_factory=list, max_length=MAX_FLOWS)
    token_allowed_assertions: list[str] = Field(
        default_factory=list, max_length=50,
        description="mailbox assertion ids whose mail legitimately carries a one-time token")

    @model_validator(mode="after")
    def _bounded_and_unique(self) -> CredentialPolicy:
        if len({f.id for f in self.flows}) != len(self.flows):
            raise ValueError("flow ids must be unique")
        if len(self.flows) * len(self.rules.declared()) > MAX_PROBES:
            raise ValueError(f"more than {MAX_PROBES} password probes planned")
        return self
