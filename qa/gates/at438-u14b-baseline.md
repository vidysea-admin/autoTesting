# HUMAN_GATE — at438-u14b-baseline: what U14(b)'s "pre-change detector" means when failed cycles land on master

**Opened:** 2026-09-16 · **Status: OPEN** · **Approver:** Umesh
**Blocks:** closing AT-438 (STALLED after 3 cycles) and the AT-453 unit. Related: `qa/gates/commit-before-verdict.md`.
**Evidence:** `qa/debug/at438-display-contents-cycle3.md` · `qa/verdicts/at438-display-contents.md` (cycle 3).

## The question, in one line
Should U14(b) ("must not drop text the pre-change detector reported") be judged against the detector
**before the unit began** (`c687b73^`), not against the unit's own earlier FAILED cycle commits?

## Why it matters
Each cycle was committed before its verdict, so cycles 2 and 3 were charged against the cycle-1 probe,
which itself failed (AT-442, high) and can never ship. Against the real pre-unit detector, cycle 3
(`9fc937d`) misses 0 texts on the 60 layouts where the old detector missed 22; AT-449/AT-453 were
already missed before the unit.

## Options (one decision, three parts; answer any subset)
- **(a)** U14(b) baseline = the pre-unit detector. Contract amendment, applied by `/checker`.
- **(b)** Checker re-rules `9fc937d` under (a) and closes AT-438. AT-453 (`::details-content`
  `display:contents`/`inline` paints) becomes its own unit: max 2 cycles, baseline `9fc937d`, starting
  from the checker's measured candidate `cv==="hidden" && HIDES_ON.test(pseudo.display)` (26/26),
  re-scored on the full cycle-3 corpus, and committed only after its verdict.
- **(c)** AT-454 (text slotted through a CLOSED shadow root is reported though hidden) is accepted into
  U14(c) as a disclosed false-positive class; a real fix needs CDP (a separate unit).

**Maker recommendation:** (a) + (b) + (c).

## How to answer
Reply in chat, e.g. `at438 a b c`, or `at438 none: <why>`. The maker appends
`Answered: <ISO> — <choice> — <where>` below before acting.

Answered: 2026-09-26T22:34:22+05:30 — a + b + c — Umesh via AskUserQuestion in the checker session. (a) U14(b) is judged against the detector as it was BEFORE the unit started, never against the unit's own failed drafts; (b) the checker re-scores cycle 3 under that baseline and AT-438 closes on it, AT-453 splits into its own unit capped at 2 cycles; (c) AT-454 (closed shadow root) is accepted as a documented known limitation.
