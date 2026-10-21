"""Which doctor findings are advisory warnings and which block (L10, D-087)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autotester.doctor import Violation

# D-087 item 3: T-196 merges in ADVISORY mode. Coverage and declaration findings are warnings
# and do not turn doctor red; wrong-subject, subject-unavailable and dangling citations stay
# blocking (they are simply not listed here). To promote the check to blocking by a later
# decision, empty ADVISORY_CITATION and the blocking() filter will count them again.
ADVISORY_CITATION = frozenset({"decision-citation-coverage", "decision-citation-declaration"})
NON_BLOCKING = ADVISORY_CITATION | {"decision-citation-sealed", "decision-citation-known-disputed",
                                      "committed-leg-skipped",
                                      "env-dollar-literal"}


def blocking(violations: list[Violation]) -> list[Violation]:
    """The violations that make doctor exit nonzero."""
    return [v for v in violations if v.rule not in NON_BLOCKING]


def warning_summary(violations: list[Violation], first: int = 5) -> list[str]:
    """Advisory rows as a count per rule plus the first few items, never every line."""
    soft = [v for v in violations if v.rule in NON_BLOCKING]
    lines = []
    for rule in sorted({v.rule for v in soft}):
        rows = [v for v in soft if v.rule == rule]
        lines.append(f"warning: {rule}: {len(rows)} advisory finding(s) (D-087, non-blocking)")
        lines.extend(f"  {v}" for v in rows[:first])
        if len(rows) > first:
            lines.append(f"  ... and {len(rows) - first} more")
    return lines
