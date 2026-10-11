# Manifest - t200b-scheduled-test

**Unit:** T-200 phase B, the part that is buildable on master 09828f2d: the TS5 credential-derived gate, the stateless tick runner (heartbeat write, `--dry-run`, exit codes 0/2/3, JSON report), purge of a deleted project's claims and records, and the TS6 import guard. **This unit does NOT close goal task T-200**: routes, `Project.schedule`, the CLI shell, the card, the single launcher, HO24 `refused` and inbox delivery are HELD (list below).
**Brief:** `qa/briefs/t200-scheduled-test.md` (phase B rows; shipped phase A is `qa/verdicts/t200a-schedule-core.md`, PASS, cycle 0).
**Branch / base:** `wave/t200b-scheduled-test` on master 09828f2d.
**Code commit (pre-check sha):** e4e1b3a9 (the commit after it adds this manifest and one regenerated `docs/MAP.md` line only).
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (the credential-derived run approval, TS5, is the brief's named L trigger for phase B; plus the timing/concurrency core of phase A that this unit extends)
Dual check: no (the diff adds no auth, tenancy or production-write code: the gate only reads which declared keys have a value and calls the existing `covering_approval`; it writes nothing to production; no `dual-trigger` applies)
Fix cycle: 0
Executor: claude-sonnet-subagent (maker build subagent)
Status: ready-for-check
Full-suite trigger: none (no existing module's behaviour changes except one required field on `TickDeps`, whose only constructor is `tests/schedule_fakes.py`).
UI surface: none changed (no route, screen or card), so no browser walk is owed.

## Open criteria after phase A, and what this unit did with each

| Criterion | Status here | Reason |
|---|---|---|
| TS5 credential-derived approval, `blocked_no_credentials`, no trace | BUILT (gate, records, zero-trace tests) except the owner-visible surfaces | `covering_approval` is on master. Owner inbox and project-page display are HELD (below) |
| TS7 tick side: heartbeat write at tick end, `--dry-run`, exit codes 0/2/3, JSON, failed-with-cause, a project that crashes | BUILT as `run_tick` + `TickReport` | The `autotester schedule tick` shell is HELD: it must enumerate `Project.schedule`, which is not on master |
| TS1 clause "deleting the project removes its markers and records" | PURGE FUNCTION BUILT (`purge_project`) | Wiring needs a project-delete path; none exists on master |
| TS6 import guard (AST) | BUILT (partial) | The one-launcher half needs `stages/run_launcher.py` (T-205) |
| TS1 `Project.schedule`, save/pause/resume/delete routes, `schedule.manage` | HELD | `schema/project.py` is T-205's; `schedule.manage` and `auth/policy.py` are on unmerged `wave/t204-team-login`; no `auth/` on master |
| TS6 one launcher, `Run.trigger=SCHEDULE`, `slot_key` on `Run`, queue idempotency key | HELD | `stages/run_launcher.py`, `Run.slot_key` (T-205/G1) not on master; the T-203 queue on master has no slot key on `QueueEntry` |
| HO24 owner disabled / deleted / no `project.run` -> `refused` | HELD | needs the auth module (T-204), not on master |
| TS7 schedule card "scheduler stale since", persona walk | HELD | no schedule UI without the routes; `scheduler_health` (phase A) is ready for it |
| TS5 / TS7 owner inbox + email | HELD | needs `wave/t201a-report-delivery` / the email sender (`qa/gates/email-sender-credentials.md`), not on master; real email is out of scope for this unit |

## What changed

| Path | Lines | One job |
|---|---|---|
| `src/autotester/stages/schedule_gate.py` (NEW) | 73 | `credential_state` (read-only classification), `refusal_for`, `credential_gate` (the `TickDeps.gate`; calls `covering_approval` only for a provisioned project) |
| `src/autotester/stages/schedule_tick.py` (NEW) | 72 | `run_tick`: one pass over every scheduled project, heartbeat at the end, `--dry-run`, exit code |
| `src/autotester/schema/schedule.py` | 241 -> 269 | + `CredentialState` closed vocabulary, + `TickReport` (the `--output json` document) |
| `src/autotester/stages/scheduler.py` | 284 -> 289 | `TickDeps.gate` (required field, no default allow) and the gate call in `_fire`, before any queue work |
| `src/autotester/stages/schedule_store.py` | 109 -> 124 | + `purge_project` |
| `tests/schedule_fakes.py` | 86 | `make_deps(gate=...)`; default allows (a test seam, not production) |
| `tests/test_schedule_gate.py` (NEW) | 152 | TS5: 8 tests through the real `tick_project`, real gate, real `ProjectStore` |
| `tests/test_schedule_tick.py` (NEW) | 180 | TS7 tick side, purge, TS6 import guard: 13 tests |
| `.env.example` | +7 -1 | documents `AUTOTESTER_SCHEDULE_GRACE_MINUTES` and `AUTOTESTER_TICK_INTERVAL_S` (AT-920, phase A feature) and corrects the stale `AUTOTESTER_TIMEZONE` comment (it said IANA zone; D-078 allows UTC or IST) |
| `docs/MAP.md` | regenerated | `uv run autotester map` |

### New modules (owner confirms before merge)

- `src/autotester/stages/schedule_gate.py`: the TS5 gate, one job. Could instead live in `stages/explore_consent.py` (133 lines) if the owner prefers one consent file.
- `src/autotester/stages/schedule_tick.py`: the tick runner, one job. `scheduler.py` has 11 lines of headroom, so it could not take it.

## Design decisions for the checker to rule on

1. `TickDeps.gate` is a required field (no default): a caller that forgets the gate is a type error, not a silent allow. TS5 is CRITICAL.
2. The gate runs after the "my own queue entry already exists" check and before the overlap check and the enqueue, so a refused slot touches neither the queue nor the run directory. A gate that raises ends as a `failed` record (fail closed, nothing enqueued).
3. The refusal outcome is `blocked_no_credentials` for all three states and for a missing approval; the state is the first word of `detail` (`no_secretref`, `secretref_without_value`, `target_outside_domains`, `approval_required`).
4. `--dry-run` never evaluates the gate (it would mint a signed row); it takes an optional read-only `preview` (`refusal_for`) and lists a would-be-blocked slot under `would_block`, exit 2. The heartbeat is not written by a dry run.
5. `bounds` for the covering approval default to `CrawlBounds()`; the wiring slice passes the real run bounds. The brief says a run uses the approval's own bounds, which the existing `covering_approval` already does.
6. `purge_project` rewrites the shared records file with `os.replace`; an append racing that rewrite could be lost. Acceptable for a project being deleted; the wiring slice may call it under the project-delete lock.
7. Contract text TS7 "heartbeat at the end of every tick": a real tick that exits 2 or 3 still writes it ("stale" means the scheduler stopped, not that it had bad news).

## Pre-check (final code commit e4e1b3a9, worktree clean; no full suite, no directory-wide run)

Pre-check[TS5]: e4e1b3a9 uv run pytest -p no:xdist -o addopts= tests/test_schedule_gate.py -> 8 passed
Pre-check[TS7]: e4e1b3a9 uv run pytest -p no:xdist -o addopts= tests/test_schedule_tick.py tests/test_schedule_failures.py -> 32 passed
Pre-check[TS6]: e4e1b3a9 uv run pytest -p no:xdist -o addopts= tests/test_schedule_tick.py -> 13 passed (includes the AST import guard)
Pre-check[TS1]: e4e1b3a9 uv run pytest -p no:xdist -o addopts= tests/test_schedule_tick.py -> 13 passed (includes the purge test)
Pre-check: e4e1b3a9 uv run pytest -p no:xdist -o addopts= tests/test_schedule_model.py tests/test_schedule_due.py tests/test_schedule_marker.py tests/test_schedule_catchup.py tests/test_schedule_overlap.py tests/test_schedule_failures.py tests/test_schedule_gate.py tests/test_schedule_tick.py -> 133 passed
Pre-check: e4e1b3a9 uv run ruff check src tests scripts -> All checks passed
Pre-check: e4e1b3a9 uv run autotester doctor -> clean (after `autotester map`)

Also run: tests/test_env_loading.py, test_hosting_deploy.py, test_approval_signing.py, test_cli_advice_resolves.py -> 64 passed (the `.env.example` readers and the advice-site registry; no CLI command or message was added, so no `EXPECTED_SITES` change).

## Falsifications (one per built criterion; green before, red after; each in a throwaway copy of src, tests and scripts under the scratchpad, copy deleted)

| Criterion | Edit in the copy | Red node(s) after |
|---|---|---|
| TS5 | `credential_state`: `if not project.secrets:` -> `if False:` | `test_a_refused_credential_state_is_a_blocked_slot_with_no_trace[False-False-no_secretref]` and `test_credential_state_is_read_only_and_never_returns_a_value` (8 passed before, 6 after) |
| TS7 | `run_tick`: `if not dry_run:` heartbeat -> `if True:` | `test_dry_run_prints_what_would_fire_and_changes_nothing` (13 before, 12 after) |
| TS1 purge | `key.startswith(f"{project}:")` -> `key.startswith(project)` | `test_deleting_a_project_purges_its_claims_and_records_and_only_its_own` (13 before, 12 after) |
| TS6 guard | `import BrowserSession` added to `scheduler.py` | `test_the_tick_modules_import_no_browser_or_pipeline_code` (13 before, 12 after) |

Not falsified: the contract mutation "check approval after `enqueue`" (the zero-queue assertions cover it by construction, since the gate precedes `deps.enqueue` in `_fire`); the exit-code 3 branch; the `would_block` preview.

## HELD, with the dependency each waits on

1. `Project.schedule` field, then `cli_schedule.py` (`autotester schedule tick [--project] [--dry-run] [--output json]`) as a thin shell over `run_tick` (loads schedules, builds `TickDeps`, prints `TickReport`, exits with `exit_code`), and registering its advice sites in `tests/test_cli_advice_resolves.py`: waits on T-205.
2. Routes `GET/POST/DELETE` schedule with `schedule.manage`, owner = `requested_by`, `resume` bumping `since`, HO24 `refused` for a disabled/deleted/unauthorised owner: wait on `wave/t204-team-login` (auth, policy table).
3. One launcher (`stages/run_launcher.py`), `Run.trigger=SCHEDULE`, `Run.slot_key`, queue idempotency key (HO23): waits on T-205 and the T-203 queue landing with a slot key.
4. Schedule card with "scheduler stale since", persona walk (Mode D): waits on 1 and 2.
5. Inbox/email delivery of `failed` and `blocked_no_credentials` to the owner: waits on `wave/t201a-report-delivery` and the email sender seam; real email is out of scope here.
6. Wiring `purge_project` to project delete: no delete-project path exists on master.

## Owner decisions

- Add `Project.schedule` in this slice instead of waiting for T-205 (a 2-line field plus import; it would unblock the CLI shell now) or keep it with T-205 as the brief says.
- Keep `schedule_gate.py` as a separate module or fold it into `stages/explore_consent.py`.

Metrics: start=2026-10-11T01:30:00Z end=2026-10-11T02:40:00Z wall_min=70 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=0 mutants=0 defects_unit=0 defects_6c=0
