# HUMAN_GATE — should `loop-status --strict` fail on out-of-order tick lines?

**Raised:** 2026-09-26 · maker, after at592-loop-status-strict cycle 1 PASS (merged 561dd75)
**Issue:** AT-610 (low, design call) · filed by the checker in qa/verdicts/at592-loop-status-strict.md
**Blocks:** nothing. `--strict` already catches every real outage: asleep now, or ticks with no
credible last tick. This is only about write-order corruption.

## The question

`loop_status.py` counts `out_of_order` over the order lines appear in the file. Liveness is judged
from the credible ticks after sorting them. So a tick file whose lines were written out of
chronological order shows a CORRUPT row, but `--strict` still exits 0 whenever a credible recent
tick exists.

- **A: keep report-only.** This is the checker's recommendation. Out-of-order lines never hide an
  outage, because liveness uses the sorted ticks. Pin the choice with a test and a sentence in the
  loop-status contract (the checker writes that sentence).
- **B: make it gate.** `strict_unhealthy` also becomes true when `out_of_order > 0`. It is stricter,
  but a clock skew between two sessions writing the same file would turn `--strict` red with no
  outage behind it.

## Answer

Append `Answered: <ISO date> — <A|B> — <where>` below BEFORE any unit acts on it.

Answered: 2026-09-26 — A, keep report-only — Umesh via AskUserQuestion in the maker session. Scope: a test pins that --strict exits 0 when out_of_order > 0 and a credible recent tick exists; the checker adds the contract sentence.
