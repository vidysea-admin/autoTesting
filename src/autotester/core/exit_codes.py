"""The one exit-code table for machine-facing commands (T-174, CM1).

One job: define `ExitCode`, the codes CI acts on, and `exit_code_table()`, the text
`--help` mirrors. `doctor`'s own contract (0 clean, 1 violation) is unchanged and lives in cli.py.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """What a pipeline can tell apart. Never collapse two of these to one value."""

    OK = 0
    TEST_FAILED = 1   # the run finished and at least one case was graded FAIL
    USAGE = 2         # bad input: unknown project, no cases, missing credential value, no provider
    REFUSED = 3       # no valid RunApproval (consent gate, D-018): nothing started
    INFRA = 4         # provider/network/browser failure or a timeout: retry, do not triage
    INTERNAL = 5      # an AutoTester bug: report it


_MEANING = {
    ExitCode.OK: "run finished, no case failed (or a dry run listed what would run)",
    ExitCode.TEST_FAILED: "run finished and at least one case failed",
    ExitCode.USAGE: "usage or validation error (unknown project, no cases, missing credential)",
    ExitCode.REFUSED: "run refused: no valid approval covers it, nothing was started",
    ExitCode.INFRA: "infrastructure failure or timeout (provider, network, browser)",
    ExitCode.INTERNAL: "internal error in AutoTester",
}


def exit_code_table() -> str:
    """One line per code, for `--help` and the docs."""
    return "Exit codes: " + "; ".join(f"{c.value} {_MEANING[c]}" for c in ExitCode)
