# Manifest - t200b-scheduled-test

**Unit:** T-200 phase B, the part that is buildable on master 09828f2d: the TS5 credential-derived gate, the stateless tick runner (heartbeat write, `--dry-run`, exit codes 0/2/3, JSON report), purge of a deleted project's claims and records, and the TS6 import guard. **This unit does NOT close goal task T-200**: routes, `Project.schedule`, the CLI shell, the card, the single launcher, HO24 `refused` and inbox delivery are HELD (list below).
**Brief:** `qa/briefs/t200-scheduled-test.md` (phase B rows; shipped phase A is `qa/verdicts/t200a-schedule-core.md`, PASS, cycle 0).
**Branch / base:** `wave/t200b-scheduled-test` on master 09828f2d, master merged again at b0dad777 for cycle 1.
**Code commit (pre-check sha):** 6d6bc318 (cycle 1; cycle 0 was e4e1b3a9). The commit after it adds this manifest only; no source file changes after 6d6bc318.
Repair base: 0d9a3b56
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (the credential-derived run approval, TS5, is the brief's named L trigger for phase B; plus the timing/concurrency core of phase A that this unit extends)
Dual check: required
dual-trigger: security src/autotester/stages/schedule_gate.py:74
Why dual: the gate calls `covering_approval(...)` (line 74), which mints a signed approval row and, with no key, writes `AUTOTESTER_APPROVAL_KEY` to the repo-root `.env`. Cycle 0 said "dual check: no, it writes nothing", and that was wrong (see "Correction" below). Cycle 1 also adds `signing_key_available` in `explore_consent.py`, a read-only twin of `ensure_approval_key`'s refusal.
Fix cycle: 1
Executor: claude-sonnet-subagent (maker build subagent)
Status: ready-for-check
Full-suite trigger: none (the existing modules touched are `explore_consent.py`, +1 read-only function, and `TickDeps` in `scheduler.py`, whose only constructor is `tests/schedule_fakes.py`; the 64 + 64 neighbour tests below ran green).
UI surface: none changed (no route, screen or card), so no browser walk is owed.

## Correction to the cycle-0 manifest

Cycle 0 claimed the gate "writes nothing to production" and that no dual-trigger applied. That is false. What the first mint of a covering approval does, through the real `covering_approval` -> `ensure_approval_key`:

1. If `AUTOTESTER_APPROVAL_KEY` is in neither the environment nor the repo-root `.env`, and no signed approval row exists yet, it **generates a key and writes it to the repo-root `.env`** (the single gitignored file shared by every project), leaving `.env.lock` behind.
2. It **appends a signed `RunApproval` row** to `projects/<slug>/approvals.jsonl`.
3. It **exports the key into `os.environ`** of the calling process (the gate tests neutralise this with `monkeypatch.setenv(APPROVAL_KEY_ENV, "")` in the `world` fixture).

Only the refusal paths and `--dry-run` write nothing. Hence the dual check and the `dual-trigger` line above, pointing at the `covering_approval` call.

## Open criteria after phase A, and what this unit did with each

| Criterion | Status here | Reason |
|---|---|---|
| TS5 credential-derived approval, `blocked_no_credentials`, no trace | BUILT (gate, records, zero-trace tests) except the owner-visible surfaces | `covering_approval` is on master. Owner inbox and project-page display are HELD (below) |
| TS7 tick side: heartbeat write at tick end, `--dry-run`, exit codes 0/2/3, JSON, failed-with-cause, a project that crashes | BUILT as `run_tick` + `TickReport` | The `autotester schedule tick` shell is HELD: it must enumerate `Project.schedule`, which is not on master |
| TS1 clause "deleting the project removes its markers and records" | PURGE FUNCTION BUILT (`purge_project`), cycle 1 rebuilt | Wiring needs a project-delete path; none exists on master |
| TS6 import guard (AST) | BUILT (partial), cycle 1 rebuilt | The one-launcher half needs `stages/run_launcher.py` (T-205) |
| TS1 `Project.schedule`, save/pause/resume/delete routes, `schedule.manage` | HELD | `schema/project.py` is T-205's; `schedule.manage` and `auth/policy.py` are on unmerged `wave/t204-team-login`; no `auth/` on master |
| TS6 one launcher, `Run.trigger=SCHEDULE`, `slot_key` on `Run`, queue idempotency key | HELD | `stages/run_launcher.py`, `Run.slot_key` (T-205/G1) not on master; the T-203 queue on master has no slot key on `QueueEntry` |
| HO24 owner disabled / deleted / no `project.run` -> `refused` | HELD | needs the auth module (T-204), not on master |
| TS7 schedule card "scheduler stale since", persona walk | HELD | no schedule UI without the routes; `scheduler_health` (phase A) is ready for it |
| TS5 / TS7 owner inbox + email | HELD | needs `wave/t201a-report-delivery` / the email sender (`qa/gates/email-sender-credentials.md`), not on master; real email is out of scope for this unit |

## What changed (cumulative, against master 09828f2d; cycle 1 deltas marked)

| Path | Lines | One job |
|---|---|---|
| `src/autotester/stages/schedule_gate.py` (NEW) | 79 | `credential_state` (read-only classification), `refusal_for` (cycle 1: also refuses when the signing key is unavailable), `credential_gate` (the `TickDeps.gate`; calls `covering_approval` at line 74 only for a provisioned project) |
| `src/autotester/stages/schedule_tick.py` (NEW) | 72 | `run_tick`: one pass over every scheduled project, heartbeat at the end, `--dry-run`, exit code. Unchanged in cycle 1 |
| `src/autotester/schema/schedule.py` | 241 -> 269 | + `CredentialState` closed vocabulary, + `TickReport` (the `--output json` document). Unchanged in cycle 1 |
| `src/autotester/stages/scheduler.py` | 284 -> 285 | `TickDeps.gate` (required, no default allow) and the gate call in `_fire`; cycle 1: `TickDeps.scrub` also required, the identity `_same` default removed |
| `src/autotester/stages/schedule_store.py` | 109 -> 149 | + `project_records_path`, + `purge_project` (cycle 1: two-phase staged purge, shared-file refusal) |
| `src/autotester/stages/explore_consent.py` | 133 -> 150 | cycle 1: + `signing_key_available(store)`, read-only, no side effect |
| `tests/schedule_fakes.py` | 87 | `make_deps(gate=..., scrub=...)`; defaults allow / identity (a test seam, not production) |
| `tests/test_schedule_gate.py` (NEW) | 212 | TS5: 12 tests through the real `tick_project`, real gate, real `ProjectStore` (cycle 1: + scrub x2, + preview parity x2) |
| `tests/test_schedule_tick.py` (NEW) | 252 | TS7 tick side, TS6 transitive AST import guard + 8 self-tests of the guard |
| `tests/test_schedule_marker.py` | 248 | phase A file; cycle 1: purge tests (shared-file refusal, mid-way failure, two-process append-while-purge) |
| `.env.example` | +10 -1 | AT-920 keys; cycle 1 P7: `AUTOTESTER_TIMEZONE` comment now says exactly `UTC` or `IST`, upper case; blank, other values and lowercase `ist`/`utc` fall back to UTC |
| `docs/MAP.md` | regenerated | `uv run autotester map` |

### New modules (owner confirms before merge; no new file added in cycle 1)

- `src/autotester/stages/schedule_gate.py`: the TS5 gate, one job. Could instead live in `stages/explore_consent.py` (150 lines) if the owner prefers one consent file.
- `src/autotester/stages/schedule_tick.py`: the tick runner, one job. `scheduler.py` has 15 lines of headroom, so it could not take it.

## Design decisions for the checker to rule on

1. `TickDeps.gate` is a required field (no default): a caller that forgets the gate is a type error, not a silent allow. TS5 is CRITICAL.
2. The gate runs after the "my own queue entry already exists" check and before the overlap check and the enqueue, so a refused slot touches neither the queue nor the run directory. A gate that raises ends as a `failed` record (fail closed, nothing enqueued).
3. The refusal outcome is `blocked_no_credentials` for all states and for a missing approval; the state is the first word of `detail` (`no_secretref`, `secretref_without_value`, `target_outside_domains`, `approval_required`).
4. `--dry-run` never evaluates the gate (it would mint a signed row and may write the key); it takes an optional read-only `preview` (`refusal_for`) and lists a would-be-blocked slot under `would_block`, exit 2. The heartbeat is not written by a dry run. Cycle 1 (P5): `refusal_for` now also reports `approval_required: the approval signing key is unavailable` exactly when the real gate would be refused by `ensure_approval_key`, via the read-only `signing_key_available`. A first-ever slot with no key and no signed history is NOT a refusal (the real gate would mint the key).
5. `bounds` for the covering approval default to `CrawlBounds()`; the wiring slice passes the real run bounds.
6. **F2 design (replaces cycle-0 decision 6).** Records are kept one file per project (`project_records_path(records_dir, project)` = `<records_dir>/<quoted project>.jsonl`). `purge_project` is two-phase: (a) it first refuses (`ValueError`, nothing changed) if the records file holds a row of another project; (b) it moves this project's claim markers and its records file into a hidden `.purge-<uuid>` stage directory with `os.replace`, and only then `shutil.rmtree`s the stage. If any move fails, the already moved files are moved back and the stage is removed, so markers and records are never left half purged and no temp file leaks. There is no rewrite of a shared file, so an append by another process to another project's file cannot be lost, and `os.replace` of a closed file works on Windows. Known residual: if the rollback itself fails, the second error escapes and the stage directory is left holding the files (kept on purpose, nothing is deleted when unsure). Not covered: a concurrent append to the SAME project's records during its own purge (the project is being deleted; the wiring slice may hold the project-delete lock).
7. **F1 design.** The TS6 guard is a static import-closure walk over the five scheduler-side modules (scheduler, schedule_store, schedule_time, schedule_gate, schedule_tick), `ast.walk` so lazy imports inside functions count, handling `import a.b`, `from a import b` (counting `a.b` when it is a module), `from . import x` relative forms, and flagging `import_module` / `__import__` calls. The closure is transitive: every repo module reached is parsed in turn. Outside `core/`, `schema/`, `store/` only an allow-list (`stages`, `explore_consent`, `browser.secrets`, `ui.env_editor` and the scheduler-side modules) may be reached; anything else (a runner, a pipeline stage, `browser.session`, a provider) fails. The gate legitimately needs `browser.secrets` and `explore_consent`, so the guard allows exactly those and names them. A `sys.modules` closure was rejected because `autotester/__init__.py` imports the CLI, so it always holds the browser. 8 self-tests inject a leak of each shape and require a violation.
8. **P3.** `TickDeps.scrub` has no default. A caller cannot forget it. The wiring slice must pass a real redactor (e.g. `SecretStore.redactor().scrub`). A test proves a value inside a gate exception message is scrubbed before it is recorded.
9. **P7.** `.env.example` documents the timezone values exactly as `schedule_time` resolves them.
10. Left alone, as instructed: P4 and P6 (checker's non-blocking notes).

## Pre-check (code sha 6d6bc318, worktree clean; no full suite, no directory-wide run; one pytest process at a time)

Pre-check[TS5]: 6d6bc318 uv run pytest -p no:xdist -o addopts= tests/test_schedule_gate.py -> 12 passed
Pre-check[TS7]: 6d6bc318 uv run pytest -p no:xdist -o addopts= tests/test_schedule_tick.py tests/test_schedule_failures.py -> 39 passed
Pre-check[TS6]: 6d6bc318 uv run pytest -p no:xdist -o addopts= tests/test_schedule_tick.py -> 20 passed (includes the transitive guard and its 8 self-tests)
Pre-check[TS1]: 6d6bc318 uv run pytest -p no:xdist -o addopts= tests/test_schedule_marker.py -> 10 passed (includes the three purge tests and the two-process append-while-purge test)
Pre-check: 6d6bc318 uv run pytest -p no:xdist -o addopts= tests/test_schedule_model.py tests/test_schedule_due.py tests/test_schedule_marker.py tests/test_schedule_catchup.py tests/test_schedule_overlap.py tests/test_schedule_failures.py tests/test_schedule_gate.py tests/test_schedule_tick.py -> 148 passed
Pre-check: 6d6bc318 uv run pytest -p no:xdist -o addopts= tests/test_explore_consent.py tests/test_credential_run_approval.py tests/test_consent.py -> 64 passed (the module that gained `signing_key_available`)
Pre-check: 6d6bc318 uv run ruff check src tests scripts -> All checks passed
Pre-check: 6d6bc318 uv run autotester doctor -> clean (after `autotester map`)

Also run: tests/test_env_loading.py, test_hosting_deploy.py, test_approval_signing.py, test_cli_advice_resolves.py -> 64 passed (the `.env.example` readers and the advice-site registry; no CLI command or message was added, so no `EXPECTED_SITES` change).

## Falsifications (one per built criterion; green before, red after; each in a throwaway copy of src, tests, scripts and pyproject under the scratchpad, copy deleted)

### Cycle 0 (on e4e1b3a9, carried; the cycle-0 TS6 guard row is superseded by the F1 row below)

| Criterion | Edit in the copy | Red node(s) after |
|---|---|---|
| TS5 | `credential_state`: `if not project.secrets:` -> `if False:` | `test_a_refused_credential_state_is_a_blocked_slot_with_no_trace[False-False-no_secretref]`, `test_credential_state_is_read_only_and_never_returns_a_value` |
| TS7 | `run_tick`: `if not dry_run:` heartbeat -> `if True:` | `test_dry_run_prints_what_would_fire_and_changes_nothing` |
| TS1 purge | `key.startswith(f"{project}:")` -> `key.startswith(project)` | purge test (the cycle-0 test is replaced; see F2 rows) |

## Fix cycle 1

Findings repaired, each with one falsification (edit in a throwaway copy of the repaired tree at 6d6bc318, run the named node(s), green before and red after):

| Finding | Edit in the copy | Red node(s) after | Before / after |
|---|---|---|---|
| F1 TS6 guard | `scheduler.py`: add `from autotester.stages import explore  # noqa` | `test_the_scheduler_side_reaches_no_browser_or_pipeline_module_even_transitively` | 1 passed / 1 failed |
| F2 shared file refused | `purge_project`: `if records_path.is_file() and any(` -> `if False and any(` | `test_purge_refuses_a_records_file_shared_with_another_project_and_changes_nothing` | marker file: 10 / 1 failed, 9 passed |
| F2 no partial state | `purge_project`: the rollback `os.replace(held, src)` -> `pass` | `test_a_purge_that_fails_part_way_leaves_markers_and_records_together_and_no_temp_file` | 10 / 1 failed, 9 passed |
| F2 append-while-purge | `project_records_path` returns one shared `all.jsonl` for every project | `test_every_acknowledged_append_by_a_neighbour_survives_purges_of_another_project` and `test_purge_removes_only_that_projects_markers_and_record_file_and_is_idempotent` | 10 / 2 failed, 8 passed |
| P3 scrub required | `TickDeps.scrub` given the default `lambda t: t` | `test_scrub_is_a_required_field_so_a_caller_cannot_forget_it` | gate file: 12 / 1 failed, 11 passed |
| P5 preview parity | `signing_key_available` made to return True at once | `test_the_dry_run_preview_agrees_with_the_real_gate_when_the_signing_key_is_lost` | gate file: 12 / 1 failed, 11 passed |

Not falsified (said plainly): the stage-directory removal itself (covered by the no-temp-file assertions of the mid-way failure test, not by a dedicated mutation); `run_tick`'s exit-3 branch; the `would_block` preview line for non-key refusals (cycle 0).

## HELD, with the dependency each waits on

1. `Project.schedule` field, then `cli_schedule.py` (`autotester schedule tick [--project] [--dry-run] [--output json]`) as a thin shell over `run_tick` (loads schedules, builds `TickDeps` with a real redactor for `scrub`, prints `TickReport`, exits with `exit_code`), and registering its advice sites in `tests/test_cli_advice_resolves.py`: waits on T-205.
2. Routes `GET/POST/DELETE` schedule with `schedule.manage`, owner = `requested_by`, `resume` bumping `since`, HO24 `refused` for a disabled/deleted/unauthorised owner: wait on `wave/t204-team-login` (auth, policy table).
3. One launcher (`stages/run_launcher.py`), `Run.trigger=SCHEDULE`, `Run.slot_key`, queue idempotency key (HO23): waits on T-205 and the T-203 queue landing with a slot key.
4. Schedule card with "scheduler stale since", persona walk (Mode D): waits on 1 and 2.
5. Inbox/email delivery of `failed` and `blocked_no_credentials` to the owner: waits on `wave/t201a-report-delivery` and the email sender seam; real email is out of scope here.
6. Wiring `purge_project` and `run_tick` to callers: no delete-project path and no CLI shell exist on master. Both are called only from tests today.

## Owner decisions

- Add `Project.schedule` in this slice instead of waiting for T-205 (a 2-line field plus import; it would unblock the CLI shell now) or keep it with T-205 as the brief says.
- Keep `schedule_gate.py` as a separate module or fold it into `stages/explore_consent.py`.
- Whether the one-file-per-project records layout (F2) is acceptable for the wiring slice, or the owner prefers a single shared file with a cross-process lock.

Metrics: start=2026-10-11T01:59:32Z end=2026-10-11T03:20:00Z wall_min=80 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=10 cycle=1 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=0 mutants=0 defects_unit=2 defects_6c=0
Metrics-note: cycle 0 branch created 2026-10-11T01:59:32Z, cycle-0 manifest committed 2026-10-11T02:40:04Z (about 40 min; the cycle-0 manifest's own "70 min, start 01:30" was an estimate and is replaced by these timestamps). Cycle 1 started about 2026-10-11T03:01Z; the code commit 6d6bc318 landed at 2026-10-11T03:10:04Z.
