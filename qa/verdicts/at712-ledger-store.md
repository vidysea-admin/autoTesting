# Verdict - at712-ledger-store

Date: 2026-10-17 · Cycle checked: 0 · Bound to: D:/autoTesting/.worktrees/at712-ledger-store · Policy-Version: proportional-verification/2026-10-15.12
Checked head: 161aeffb (code head 81970378) · Base: fcedc9f4 (= git merge-base HEAD master)

## Check plan
Tier M (new read-only ledger helper + one CLI command; no security/auth/tenancy/prod-write trigger; lane off, `lane=normal`).
Criterion C1 = AT-712 issue text: at close-out, open ledger rows AND `qa/gates/` files naming a path the fix changed must be listed (report only; rows stay history; "a rule that stops at issues.jsonl and does not reach qa/gates/ is incomplete").
Steps: re-run verify commands; run the command on the real repo; one falsification in a copy; step 4c diff read.

VERDICT: PASS
SCOREBOARD: 1/1 criteria met, core-invariants not contradicted (no schema change, no new file over 300 lines, no function over 50 lines, edit in place)
TIER: M (new shared ledger helper + one public CLI command; no L trigger)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 rows reproduced

## Evidence (all produced by this checker)
- `uv run pytest tests/test_ledger_backref.py tests/test_ledger.py` -> 33 passed (5.0 s). `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> clean (2 advisory D-087 findings, non-blocking).
- Real-data run: `uv run autotester ledger-backref b2d6558f --exclude AT-660` (a real run_budget.py fix commit) listed 10 open rows (AT-681, AT-712, AT-775, AT-804, AT-807 for run_budget.py; others for run_case_pipeline.py / run_launcher.py) and 3 gate lines, including `qa/gates/at674-approval-key-and-live-case-grant.md:260 names src/autotester/stages/run_budget.py`, the exact gate AT-712 describes. Weak basename-only hits are marked. `ledger-backref HEAD` on the unit's own commit prints "no open row or gate names a path this commit changed", exit 0. `git status` clean afterwards (no row or gate edited).
- Falsification (copy outside the worktree, PYTHONPATH-shadowed, `autotester.__file__` confirmed to resolve in the copy): `tests/test_ledger_backref.py::test_a_run_budget_fix_lists_the_three_stale_rows_and_the_gate_that_cites_them`. Green before: `1 passed`. Edit: `store.py` `for name, text in sorted(gates.items()):` -> `for name, text in []:` (the gate scan). Red after: `AssertionError: assert 'qa/gates/at674-approval-key.md:4' in 'AT-675 [open] ...'`, `1 failed`. The assertion that fired is the gate-reach assertion the test is named for, not an import error.
- Step 4c: `git diff fcedc9f4..HEAD --stat`: store.py +100, cli_loop.py +19, tests/test_ledger_backref.py +129 (new), manifest +52; 0 deleted lines in src/tests; every file is in "What changed"; cli.py untouched. store.py 229 lines, cli_loop.py 78 lines.
- Read of the changed code (store.py:136-229): git called with an argv list, no shell; `changed_paths` read-only; suffix match is component-bounded with `(?<![\w./\-])...(?!\w)`; bookkeeping paths skipped; closing row and non-open rows excluded; unreadable ledger lines reported, not fatal; nothing writes to qa/.

## EXPLANATION
C1 is met: the helper lists open rows and gate lines that name a path the closing commit changed, the gate case (the sharper point of AT-712) is reached and falsified, and the command is report-only. Findings below are non-blocking.

## Non-blocking observations (PROPOSED-ISSUE, low; not written to the worktree ledger to avoid a tail-append merge conflict, the maker/orchestrator may mint them)
- P1 low: the remedy is a command the closing agent must remember to run; nothing in the maker close-out step or a hook invokes `ledger-backref` yet (the maker SKILL is outside this repo's contract). AT-712's "expected" asks for the mechanism, which exists; wiring it into close-out is a follow-up.
- P2 low: `ledger-backref -- --output=<file>` passes `rev` to `git diff-tree` as a positional that git would read as an option; `changed_paths` (store.py:149-152) has no `--` separator. Local-only CLI run by the operator, so no security FAIL; a `--end-of-options`/`--` fix is cheap.
- P3 low: only the first matching line per gate file and the first matching field per row are reported (store.py:195-205), which is enough for a shortlist but hides further hits in a long gate.

ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (manifest Executor: claude-sonnet-subagent; checker: claude-sonnet-subagent)
Metrics: start=2026-10-17T11:20:00Z end=2026-10-17T11:32:00Z wall_min=12 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
