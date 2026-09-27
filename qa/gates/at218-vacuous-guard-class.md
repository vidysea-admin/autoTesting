# HUMAN_GATE: AT-218 — the recurring vacuous-guard class

**Opened:** 2026-09-09 (carried forward from checker sweeps at 2026-09-08T20:00Z, 2026-09-09T02:15Z, 2026-09-09T04:50Z, 2026-09-09T06:22Z — five consecutive sweeps, unchanged)
**Type:** GRILL (goal-drift) — the sweep explicitly cannot settle this; it is a process decision, not a buildable unit.

## Question

Three consecutive sweeps (now five) have reported the same class of defect: a guard/test built
specifically to close one vacuity (a check that cannot fail) itself turns out to be vacuous in a
new way, discovered by the *next* checker rather than by the maker. Measured: 0 of 23 instances
self-caught by the maker; all 23 found by a checker.

Detection latency is excellent and has improved across the sweeps. **Prevention has not moved.**

## What decision only Umesh can make

The sweep cannot settle this because the countermeasures are the maker's own authorship, and "how
the maker should author guards" is a process/governance decision, not something a checker can
build or a maker can self-legislate.

Three options as the sweep framed them:
1. Keep paying the per-unit checker cost on this class (status quo — detection catches it every
   time, just one cycle later than ideal).
2. Change the maker's guard-authoring rule — e.g. **no guard/test lands without its own
   failing-first sabotage recorded in the same manifest that introduces it** (this would have
   caught AT-210/211/212/213/230-C5/266 before they shipped, since each was "trust the code read"
   rather than "sabotage it and watch it fail").
3. Accept the class as an inherent cost of this design and stop tracking it as a discrete finding
   per sweep (downgrade from a recurring high-severity headline to background noise).

## How to answer

Run `/grill "the recurring vacuous-guard class"` when ready, or answer directly in chat/a
manifest/DECISIONS.md — whichever you prefer. Whatever you decide, append an `Answered:` line to
this file before I act on it.

**Answered:** 2026-09-26T22:34:22+05:30 — Option 2 — Umesh via AskUserQuestion in the checker session. Every new guard or test ships with proof that it fails with the bug present (a recorded falsification run: the manifest's capability-coverage row, red on the named assertion). A guard without that proof is an unenumerated claim and fails check.
