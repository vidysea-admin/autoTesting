# GATE — at597-cycle5

**Opened:** 2026-09-26
**Blocks:** merging at597-pin-issue-caller (AT-597, AT-604)
**Evidence:** `qa/verdicts/at597-pin-issue-caller.md` cycle 4 (2e57296); Mode D is on master as a9eb1f1

## The question in one line

Should the maker get a second gated cycle (cycle 5) to register one CLI advice string in the AT-210 guard test?

## Why

- **Every claimed behaviour passes cycle 4**, including a live browser check:
  - pin gives 303 with the expect stored;
  - deleting a pinned case gives 409;
  - an identical re-pin gives 400, and a different-steps re-pin gives 409;
  - on the CLI, pin exits 0, while a re-pin and a navigate-with-value both exit 2.
- **The only red is one full-suite test:** `tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed`. The advice string "try `autotester issues list {project}`" was added at cli_issues.py:223 in cycle 1 and never registered in `EXPECTED_SITES`. Cycles 1–3 ran only targeted tests, so nothing caught it.

## Options

- **A — cycle 5 (the maker recommends this).**
  - Change: add `("cli_issues.py", "issues list")` to `EXPECTED_SITES`, plus any count assertion, the same pattern as at575's 6b66de5.
  - Scope: one test-registry line. No src change, so no Mode D repeat is needed.
- **B — STALL.** Leave the unit unmerged. The UI pin, the CLI guard, the parser and AT-604 all stay off master.

Answered: 2026-09-26 — A, cycle 5 — Umesh via AskUserQuestion in the maker session. Scope: one EXPECTED_SITES registry line, no src change.
