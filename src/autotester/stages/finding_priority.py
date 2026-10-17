"""Finding priority as a pure function of the finding class (MP7).

One job: say how urgent a class of finding is. Data leaks and privilege escalations are always P0.
There is no model input and no override argument: the only parameter is the class, and
`MultiRoleFinding` stores no priority a caller could set lower. The table names every class, so a
new `FindingClass` without a row fails `tests/test_finding_priority.py` instead of defaulting.
"""

from __future__ import annotations

from autotester.schema.multi_role_enums import FindingClass, Priority
from autotester.schema.multi_role_finding import MultiRoleFinding

PRIORITY_BY_CLASS: dict[FindingClass, Priority] = {
    FindingClass.DATA_LEAK: Priority.P0,
    FindingClass.PRIVILEGE_ESCALATION: Priority.P0,
    FindingClass.ROLE_INCONSISTENCY: Priority.P1,
    FindingClass.STATE_NOT_PERSISTED: Priority.P1,
    FindingClass.HIDDEN_API_ERROR: Priority.P1,
    FindingClass.REQUEST_BUDGET: Priority.P1,
    FindingClass.NEGATIVE_INPUT: Priority.P1,
    FindingClass.ANSWER_MISMATCH: Priority.P1,
    FindingClass.COPY_OR_BRANDING: Priority.P2,
    FindingClass.RESPONSIVE_LAYOUT: Priority.P2,
    FindingClass.WEAK_CREDENTIAL_POLICY: Priority.P1,
    FindingClass.PAYMENT_PATH: Priority.P1,
    FindingClass.MAIL_NOT_DELIVERED: Priority.P1,
    FindingClass.LINK_FAILURE: Priority.P1,
    FindingClass.OFF_PLATFORM_HOP: Priority.P1,
}

LEAK_CLASSES: frozenset[FindingClass] = frozenset(
    cls for cls, level in PRIORITY_BY_CLASS.items() if level is Priority.P0)


def priority_for(finding_class: FindingClass) -> Priority:
    """The priority of `finding_class`; read from the table at call time, nothing else."""
    return PRIORITY_BY_CLASS[FindingClass(finding_class)]


def is_release_blocking(finding: MultiRoleFinding) -> bool:
    """True for a P0 finding (a leak or a privilege escalation)."""
    return priority_for(finding.finding_class) is Priority.P0
