# GATE — at597-cycle4

**Opened:** 2026-09-26
**Blocks:** merging at597-pin-issue-caller (AT-597, AT-604): pin an issue as a regression case from the UI and the CLI
**Unit:** `at597-pin-issue-caller`, with 3 of 3 fix cycles spent
**Evidence:** `qa/verdicts/at597-pin-issue-caller.md` cycle 3 (1133e8b on wave/at597-pin-issue-caller)

## The question in one line

Should the maker get a narrow cycle 4 for one CLI parser regression, beyond the 3-cycle cap?

## Why the cap was hit

- **What holds:**
  - The UI route passed in cycle 1.
  - The credential guard, the reachable check and AT-604 (one pin per issue) passed in cycle 2.
  - The port fix passed in cycle 3, with all 6 rows reproduced.
- **The one remaining FAIL is a regression cycle 3 introduced.** The NAVIGATE branch takes the whole remainder as its target, so `navigate:https://x.com/signup::Welcome` stores the target `https://x.com/signup::Welcome` with no expect. Cycle 2 parsed this correctly. A navigate expect is live (execute.py:132, E1).

## Options

- **A — narrow cycle 4 (the maker recommends this).**
  - Change: in `_parse_step`, take navigate's target with the URL-aware `_take_step_field`, then accept the optional `[:value[:expect]]` tail. Refuse a non-empty value and keep the expect.
  - Tests: add `navigate:<ported url>::Welcome` and `<plain url>::Welcome`, each with a falsification row.
  - Scope: the parser only. IPv6 `[::1]` stays a filed follow-up.
- **B — STALL.** Leave the unit unmerged and run the stall diagnosis. The UI pin route, the CLI credential guard and AT-604 all stay off master.

Answered: 2026-09-26 — A, narrow cycle 4 — Umesh via AskUserQuestion in the maker session. Scope: the navigate branch of `_parse_step` only.
