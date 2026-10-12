# d088-followups manifest

Status: ready-for-check
Fix cycle: 0
Ids: ISS-t200-schedule-wiring-3 (fail-open queue file), AT-891 / AT-654 (Pathlynks production)
Authority: D-088 (docs/DECISIONS.md, master 99cff7e3). Not waived: the unreadable-queue fail-open; Pathlynks IS production.

## Fix 1 - fail closed
`ui/run_queue.py::persisted_entries` now raises RuntimeError on an unreadable or corrupt queue file (absent file stays empty). `scheduler._fire` already records that as `failed` with a scrubbed reason before the gate or enqueue, so nothing starts. Tests: tests/test_schedule_failclosed.py (missing, corrupt x4, unreadable, tick-level).

## Fix 2 - Pathlynks production
The Project schema had no production field (production lived only on approvals). Added `Project.production: bool = False`; `projects/pathlynks/project.json` sets it true.
Readers: `core/consent.py::prepare_account_grant` mints `production=project.production` and checks against it; `stages/explore_consent.py` `_require` passes it to `require_approval` (a dev-signed row no longer covers; superseded appr_ce61e4420ac9 is refused) and `require_consent` refuses typing if project or row is production; `stages/orchestrate_gate.py` passes it. Tests: tests/test_explore_consent.py, tests/test_consent.py.
Not touched: approvals.jsonl / any approval row, agents/ (agents/guards.py still calls require_approval without production; follow-up for the agents owner), browser/secrets.py, ledgers.
Note: qa/contracts/consent.md says production is inert for CRAWL; this now makes it effective per project (D-088). Contract edit left to the maker.

Checks: per-file pytest 107 passed, ruff clean, doctor clean. No full suite.
