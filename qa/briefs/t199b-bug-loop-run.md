# Brief - t199b-bug-loop-run: T-199 second slice (run directory to bug events, store hardening, sheet DRY RUN plan)

Policy-Version: proportional-verification/2026-10-10.9
Tier: **L** (concurrency: racing writers on the event store; the sheet plan is an outward-facing write PLAN).
Base: master `4e0903cd` (t199a merged at `d55bec37`). Branch `wave/t199b-bug-loop-run`. Predecessors: `qa/briefs/t199a-bug-loop-core.md`,
`qa/briefs/t199-bug-loop-dry-run.md` (copied here from the main checkout, where it is untracked).

## Hard boundary

The owner has not approved any write to the real Pathlynks Tracker sheet (`qa/gates/t199-first-live-write.md`, OPEN; D-081 item 7;
D-083 item 3 is the maker's unconfirmed reading and is not acted on). This slice builds a DRY RUN: no Google API call, no `gws`, no
network. `SheetClient` is an interface; the only implementation is a test fake. The write path refuses a live client outright.

## What it builds (modules named by job)

| Module | Job |
|---|---|
| `schema/bug_run.py` | shapes: `BugSnapshot` (one read of the log), `BadEventFile`, `RunReport` |
| `stages/bug_run.py` | `process_run`: a finished run's verdicts to bug events through `kind_of_verdict`; changed or deleted case to `case_changed` |
| `schema/sheet_plan.py` | shapes of the plan: `SheetColumns`, `SheetPlan` (self-hashing), `PlanRow`, `SyncMemory`, `PlanConfirmation` |
| `stages/sheet_plan.py` | pure plan from open bugs plus one sheet read, and its human rendering |
| `stages/sheet_write.py` | `SheetClient` Protocol (no delete), `dry_run`, `write_confirmed_plan` (refuses live, needs confirmation of the exact hash) |

Edited in place: `store/bug_store.py` (snapshot, file name with time, bad files, clock), `stages/bug_loop.py` (`storable(now)`,
`Refusal.IMPLAUSIBLE_TIME`, `order_key` rank, `trace` keeps first result), `schema/tracked_bug.py` (`bug_key` length and control
characters, `LIVE_STATUSES`, public `no_control`), `schema/verdict.py` (`Criterion.fingerprint`).

## Held clauses closed (contract `qa/contracts/team-bug-loop.md`)

TB3 reading verdicts off a run directory; TB4 detecting a deleted case or changed criterion, and the pinned-case test; TB6
`process_run` idempotent and convergent. Checker findings folded in: P3, P4, P8, P9 (verdict `qa/verdicts/t199a-bug-loop-core.md`).

## Not built

TB7 tracker page and any route (needs T-204 login); the live sheet client; stored `close_passes` (P6); TB8 mapping proposal and
confirmation; persistence of `SyncMemory`; the `project.edit` check on a confirmer. Two product questions are left as they are and
pinned by tests named `test_p1_*` and `test_p2_*`: (a) a new FAIL on a stale key (P1), (b) an uncited FAIL and a pass streak (P2).
