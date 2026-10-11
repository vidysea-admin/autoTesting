# t200b-scheduled-test - checker evidence (cycle 0, head 0d9a3b56, coordinator A)

Sub-checker outputs, condensed. All mutations ran in throwaway copies under the scratchpad; the bound worktree was never edited (`git -C <worktree> status --porcelain` empty before and after).

## Re-run of the builder's pre-check (sha differs: e4e1b3a9 -> 0d9a3b56, diff between them = manifest + docs/MAP.md only)
- tests/test_schedule_gate.py -> 8 passed
- tests/test_schedule_tick.py tests/test_schedule_failures.py -> 32 passed
- wide schedule set (8 files) -> 133 passed
- test_env_loading, test_hosting_deploy, test_approval_signing, test_cli_advice_resolves -> 64 passed
- `uv run --project <worktree> ruff check src tests scripts` -> All checks passed
- `uv run --project <worktree> autotester doctor` -> doctor: clean (no tracked file changed)

## Falsifications (green in copy, one edit, red on the named assertion)
TS5, tests/test_schedule_gate.py (8 passed before each):
- R1 credential_state `if not project.secrets` -> `if False` : RED (2 failed; no_secretref label, read-only test)
- R2 gate moved AFTER deps.enqueue (the contract mutation, not done by the builder): RED (6 failed, `assert 1 == 0` on len(q))
- R3 refusal ignored: RED (5 failed, ENQUEUED != BLOCKED_NO_CREDENTIALS)
- R4 domain-scope condition dropped: RED (1 failed, label only; the real approval gate still blocks)
- R5 raising gate swallowed (fail open): RED (`[ENQUEUED] == [FAILED]`)
TS7, tests/test_schedule_tick.py + test_schedule_failures.py (32 passed before each):
- R1 heartbeat `if not dry_run` -> `if True`: RED  R2 `return 3` -> `return 2` (not done by builder): RED
- R3 `blocked = False` (would_block preview, not done by builder): RED  R4 drop `or report.would_block`: RED
- R5 per-project except removed: RED  R6 skip heartbeat when errors: RED  R7 dry run calls tick_project: RED (2 failed)
TS1 purge (tests/test_schedule_tick.py, 13 passed): R1 `startswith(project)`: RED; R2 filter inverted: RED; R3 claim loop removed: RED.
TS6 AST guard: eager and lazy `import autotester.browser.session` in scheduler.py / schedule_tick.py: RED (R4-R6).
**SURVIVORS (guard holes):** R7 `from autotester.stages import explore` in scheduler.py; R9 `from autotester.browser import session`; R11 `from autotester.stages.agent_loop import ...` (agent_loop imports BrowserSession, so the guard is not transitive); R12 `from autotester.browser.session import BrowserSession` in schedule_gate.py (file not scanned); R8 `importlib.import_module` (string import, expected).

## Coordinator reproduction of the TS6 hole (own run)
Copy r0 = unchanged worktree src/tests/scripts; copy r7 = r0 plus one line `from autotester.stages import explore  # noqa` at scheduler.py:18.
Command (cwd = the copy, PYTHONPATH=<copy>/src;<copy>/tests;<copy>/scripts, interpreter = worktree .venv python):
`python -m pytest -p no:xdist -o addopts= tests/test_schedule_tick.py::test_the_tick_modules_import_no_browser_or_pipeline_code --rootdir <copy>`
-> r0: `1 passed`; r7: `1 passed`. The guard (tests/test_schedule_tick.py:167-180) compares `node.module` to a list of full dotted names and `node.names` to three names only, so a `from autotester.stages import <pipeline module>` passes.

## Coordinator reproduction of the purge race (own run of the sub-checker's probe_race.py, scratchpad s6/race)
```
before purge: ['A:fixed:2026-10-11T09:00Z', 'B:fixed:2026-10-11T09:00Z']
after purge(A): ['B:fixed:2026-10-11T09:00Z']
B's concurrently appended record LOST: True
purge raised: PermissionError [WinError 5] Access is denied: '...\.records.jsonl.58796.tmp' -> '...\records.jsonl'
claims left: ['B:...']  records left: ['A:...', 'B:...']  leftover tmp: ['.records.jsonl.58796.tmp']
```
Two-process stress (sub-checker, 100 B appends against 100 purges of A): 4 B appends raised PermissionError, 4 more of the 96 acknowledged B appends were absent at the end (92/100 present), 81/100 purges failed. `_redrive` consequence: with B's record gone and its queue entry still in the snapshot the slot is re-recorded (no duplicate); with the entry absent from the snapshot `_fire` enqueues again (a re-fire, protected only by T-203's idempotency key, which is not on master).

## Credential handling (fake sentinels in temp roots, real .env never read)
No sentinel in any record, TickReport, log line, exception text or approval row in the four states, the malformed-.env, missing-.env, unreadable-.env and invalid-UTF-8 cases (9 scenarios). Dry run and `credential_state`/`refusal_for` wrote nothing (before/after file listing). Findings: (1) `TickDeps.scrub` defaults to identity, so a non-ApprovalRequired exception whose message holds a value goes into `SlotRecord.detail` and the TickReport (probe: RuntimeError("cannot write <sentinel>") from `store.add_approval`); OSError/ValueError are sanitized upstream, so no realistic path was found, only a synthetic one. (2) On a provisioned project with no signing key, the gate calls `ensure_approval_key`, which writes AUTOTESTER_APPROVAL_KEY into the repo-root `.env` and leaves a `.env.lock` (1 byte) beside it. (3) An approval row is minted before the overlap check, so a `skipped_overlap` slot still leaves a row. (4) With the signing key lost and signed history present, `--dry-run` previews `would_fire` while the real tick blocks.

## Mutants beyond the floor
24 mutations were run (floor 4 criteria plus extras), more than the L cap of 10 (.9-4). `mutant-cap-raise: src/autotester/stages/schedule_tick.py:1 CRITICAL TS5/TS6 breadth probes and the three mutations the builder did not run`.
