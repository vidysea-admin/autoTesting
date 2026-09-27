# GATE — meeting-user-persona-ux-judging

**Opened:** 2026-09-26 (by /checker, from the 2026-09-25 counselor-tool meeting review)
**Blocks:** AT-583 (no user-persona model), AT-584 (no UX/comprehension judging on live runs)
**Approver:** Umesh (Lab Protocol)

## The question in one line

Should AutoTester test "as a specific kind of user" (e.g. an average counselor in a tier-2 city, or a first-time
government-school staffer) and judge whether each screen is understandable and easy to navigate for that user?

## Why it needs you

This changes what AutoTester's verdict means. Today the judge is deliberately functional-only
(`schema/verdict.py:15-22`: "if it can be argued about, it is not a criterion"). The default rubric even excludes message
wording (`stages/run_case_pipeline.py:34-43`). Letting subjective clarity into the PASS/FAIL line would soften the
north star's false-positive metric. So the checker will not decide this by amending a contract.

## Options

- **A — Advisory UX track (checker's recommendation).**
  - Add a `UserPersona` (role, tech literacy, language, device, goals) beside `PortalPersona`.
  - A separate UX pass produces **advisory, severity-scored findings** (navigation confusion, unclear copy, a hidden or
    unreachable control), reported beside the functional verdict. It never changes PASS/FAIL.
  - Persona-driven case generation plugs into T-166.
- **B — Persona-aware case generation only.** Personas shape which cases get generated (e.g. an India-bound student
  never sees a Visa step), with no UX judging.
- **C — Not now.** Keep AutoTester functional-only; UX stays a human job.

## How to answer

Add a line `Answered: YYYY-MM-DD — A | B | C (+ any constraints)` below, or tell the checker or maker session. Once
answered, the maker turns it into a goal task and the checker folds a contract criterion for it.

Answered: 2026-09-26T22:34:22+05:30 — A — Umesh via AskUserQuestion in the checker session. Advisory UX track: a UserPersona (role, tech comfort, locale, device) and a separate, severity-scored UX/comprehension findings list per screen that NEVER changes the functional PASS/FAIL (schema/verdict.py rule untouched); a persona is never a way to soften a criterion. Maker: goal task(s) for AT-583/AT-584; checker: contract criterion.
