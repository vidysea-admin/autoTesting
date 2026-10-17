"""The Group 11 (multi-role platform) vocabulary file: every closed value set G11 adds.

One job: be the single home of the G11 closed vocabularies (platform link kind, where a role
account came from, finding priority and class, cross-role assertion channel and expectation, the
oracle names). Created and edited by T-207 only (multi-role-platform.md MPI3): a later unit that
needs a new enum defines it in its own schema file. `schema/enums.py` is at its 300-line cap and
is not touched; a value defined in both files, or re-typed as a bare literal in a stage, is a
defect.
"""

from __future__ import annotations

from enum import StrEnum


class LinkKind(StrEnum):
    """How one platform hands a user to another (MP1)."""

    REDIRECT = "redirect"
    SSO = "sso"
    SHARED_ACCOUNT = "shared_account"
    HANDOFF = "handoff"


class AccountOrigin(StrEnum):
    """Who supplied a role account: the onboarder typed it, or a run created it."""

    ONBOARDER = "onboarder"
    CREATED_IN_RUN = "created_in_run"


class Priority(StrEnum):
    """Finding priority. P0 is release-blocking; leak and privilege classes are always P0 (MP7)."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class FindingClass(StrEnum):
    """What kind of defect a multi-role finding is; one class per oracle outcome."""

    DATA_LEAK = "data_leak"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ROLE_INCONSISTENCY = "role_inconsistency"
    STATE_NOT_PERSISTED = "state_not_persisted"
    HIDDEN_API_ERROR = "hidden_api_error"
    REQUEST_BUDGET = "request_budget"
    NEGATIVE_INPUT = "negative_input"
    ANSWER_MISMATCH = "answer_mismatch"
    COPY_OR_BRANDING = "copy_or_branding"
    RESPONSIVE_LAYOUT = "responsive_layout"
    WEAK_CREDENTIAL_POLICY = "weak_credential_policy"
    PAYMENT_PATH = "payment_path"
    MAIL_NOT_DELIVERED = "mail_not_delivered"
    LINK_FAILURE = "link_failure"
    OFF_PLATFORM_HOP = "off_platform_hop"


class AssertChannel(StrEnum):
    """Where a cross-role assertion looks (MP13)."""

    UI = "ui"
    MAILBOX = "mailbox"
    API = "api"


class Expectation(StrEnum):
    """Whether the observed thing must appear or must stay away within the window (MP14)."""

    PRESENT = "present"
    ABSENT = "absent"


class OracleName(StrEnum):
    """Every G11 oracle. The value is the stage module suffix: `stages/oracle_<value>.py` (MP15)."""

    MAILBOX = "mailbox"
    TENANT = "tenant"
    PRIVILEGE = "privilege"
    NEGATIVE_INPUT = "negative_input"
    STATE_AFTER = "state_after"
    API_ERROR = "api_error"
    REQUEST_BUDGET = "request_budget"
    CONSISTENCY = "consistency"
    ANSWER_KEY = "answer_key"
    COPY_LINT = "copy_lint"
    RESPONSIVE = "responsive"
    CREDENTIAL_POLICY = "credential_policy"
    PAYMENT = "payment"
