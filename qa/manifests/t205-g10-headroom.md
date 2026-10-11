# Manifest — t205-g10-headroom
**Contract:** qa/contracts/team-foundation.md (TF1-TF8); also consent.md CN1 (transport assertion) and ui-run.md RU1-RU4 (behaviour to preserve)
**Goal task:** T-205 (plan unit G1 `g10-0-headroom`: headroom and shared seams for Group 10)
**Date:** 2026-10-11
**Fix cycle:** 0
**Dual check:** required (set by the maker at dispatch, 2026-10-11: the diff moves the live-case approval gate, the AT-570 seam, out of `ui/routes_runs.py` into a new module, and a move can drop a gate as easily as a change can. The builder's view was "no": no approval logic, secret handling, login, permission key, tenancy rule or production write is added or changed, and `auth/policy.py` is a pure merge function with no catalogue entries)
dual-trigger: security src/autotester/stages/run_launcher.py:179 (`require_live_case_approval` called from `prepare_run`; the gate itself is at `:134-151`)
**Persona walk:** skip (no screen, route, template or command changes; the route table and `--help` listing are held byte-equal by golden snapshots)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Executor rationale:** single build unit with a full brief; fixtures and fakes only, no browser, model or network call, no approval row minted or edited, no `.env` read.

## Base, branch and stale-brief notes
- Branch `wave/t205-g10-headroom`, worktree `.worktrees/t205-g10-headroom`, cut from master `09828f2d`. Product commit `3ebd2fcaecbdf1c423d550bf55ab8d0a2f6dd69b`; the manifest commit on top changes no product file.
- The brief said T-203 (queue) and T-200a (schedule core) were not yet landed. Both are on master: `routes_runs.trigger_run` already queues through `ui/run_queue.py` (HO15-HO20) and `schema/schedule.py` exists. The launcher is built on that reality: `trigger_run` gates (`run_launcher.prepare_run`), then submits to the queue; the queue's runner `_run_queued` calls `launch_run`, which re-checks every gate (HO19) and runs.
- No older work for this unit: branches matching `*g1*`, `*headroom*`, `*t205*` return only this branch.

## What changed
New modules are in the next section. Edited files first.
- src/autotester/ui/routes_runs.py (263 -> 74 lines): `trigger_run` is a thin caller of `run_launcher.prepare_run`, then `get_queue().submit`; `_run_queued` calls `launch_run`; `_seams()` hands the launcher this module's current `LangChainFallbackProvider`, `plan_parallel_run`, `_free_ram_mb` at call time, so existing tests' `monkeypatch.setattr(routes_runs, ...)` still work; `_execute_with_trace` and `_plan_under_shared_budget` remain as thin shims for tests that call them directly (see Owner decisions).
- src/autotester/ui/app.py (271 lines, was 300): per-router imports and `include_router` lines removed; `routers.include_all(app)` is called once, at the same point in the order.
- src/autotester/ui/helpers.py (292): `_SLUG_RE` now compiled from `SLUG_PATTERN` (imported from `core.paths`), so the slug pattern has one home.
- src/autotester/cli.py (297, was 295): the two `add_typer` lines for `ingest` and `issues` replaced by `cli_subapps.register_subapps(app)`.
- src/autotester/core/paths.py (244, was 287): `RepoDocs` moved to `core/repo_docs.py` and re-exported (lazy import inside `RepoDocs.__init__` avoids the cycle); adds `team_path`, `__all__`.
- src/autotester/store/filestore.py (115): adds `write_text` (temp file + `os.replace`).
- src/autotester/schema/schedule.py (214): `ScheduleKind`-style closed enums relocated to `schema/team_enums.py` and re-imported (same names, same values).
- src/autotester/schema/project.py (213): adds `TrackerConfig`, `Project.schedule` (default `None`) and `Project.tracker` (default `None`); `extra="forbid"` unchanged.
- src/autotester/schema/run.py (134): adds optional `requested_by`, `slot_key`, `via` (default `None`).
- docs/MAP.md: regenerated with `autotester map`.
- Tests, all new, no existing test file touched: tests/test_run_launcher.py (55), tests/test_run_launcher_approval.py (134), tests/test_routers_list.py (78), tests/test_policy_merge.py (61), tests/test_cli_subapp_hook.py (52), tests/test_project_schema_team.py (67), tests/test_team_store.py (127), tests/test_team_enums_home.py (55).
- Goldens, all new: tests/golden/ui_routes.json (262, route table taken from master before the change), cli_commands.json (70, taken from master before the change), project_with_team_keys.json, project_without_team_keys.json, run_pre_t205.json.
- No `.env.example` change (no new env key). `tests/test_cli_advice_resolves.py` not edited: no CLI command or advice message was added or changed, and it passes.

## New modules (owner confirms before merge)
D-072 item 2 authorises the Group 10 split modules; each is still a human gate. Line counts are measured.
- src/autotester/stages/run_launcher.py (285) — the one launcher (`launch_run`, `prepare_run`, `LaunchRefused`, `RunSeams`, `PlanningLedger`). Imports `autotester.ui.run_execution` (a stage-to-ui upward dependency; see Owner decisions).
- src/autotester/ui/routers.py (67) — `ROUTERS` + `STUBS` + `include_all`.
- src/autotester/cli_subapps.py (24) — `SUBAPPS`, `register_subapps`.
- src/autotester/auth/__init__.py (1) and src/autotester/auth/policy.py (63) — `merge_route_policies`, `PolicyError`, `PUBLIC`.
- src/autotester/schema/team_enums.py (51) — the Group 10 vocabulary home (TF8).
- src/autotester/core/safe_names.py (66) — hostile-name validator and slot-key encoder.
- src/autotester/core/repo_docs.py (78) — `RepoDocs`, moved out of `core/paths.py`.
- src/autotester/store/team_store.py (50) — `write_model`, `read_model`, `create_marker` under `<repo_root>/.work/team/`.

## Overlap with T-204 (`wave/t204-team-login`, head 6ea9b688) — what the later merger must reconcile
T-204 and this branch share a merge base of `6c98a378`. Files changed on both: `docs/MAP.md`, `src/autotester/auth/__init__.py`, `src/autotester/auth/policy.py`, `src/autotester/cli.py`, `src/autotester/ui/app.py`, `src/autotester/ui/routers.py`. Not copied, not depended on; names align where the contract allows.
- `ui/routers.py` (add/add): same names (`ROUTERS`, `include_all(app)`), one concept. T-204's list is a tuple of 20 routers with auth/admin first; mine is 17 old routers in the old order plus `*STUBS.values()`. Merge: keep T-204's tuple order (it is the new route order) and append the eight stubs.
- `ui/app.py`: both remove the per-router imports and call `include_all`. Take either side's removal; keep T-204's auth middleware wiring, keep one `include_all` call.
- `auth/__init__.py` and `auth/policy.py` (add/add): T-204's `policy.py` is 107 lines with the central table and the catalogue; mine is a 63-line `merge_route_policies(*dicts)` + `PolicyError` + `PUBLIC`. The contract (TF4) says whoever lands second extends in place: keep T-204's file and fold my merge function and its fail-at-import cases in; if T-204 keys routes by a `"<METHOD> <path>"` string, mine does too, but if it uses a `(method, path)` tuple or a `RouteRule` mapping, adapt `tests/test_policy_merge.py` to that shape.
- `cli.py`: T-204 adds `from autotester.cli_auth import app as auth_app` and `app.add_typer(auth_app, name="auth")`. After merge, put `("auth", cli_auth.app)` in `cli_subapps.SUBAPPS` and drop that `add_typer` line; update `tests/golden/cli_commands.json` to include `auth`.
- `docs/MAP.md`: regenerate with `autotester map` after the merge; do not hand-merge.
- `tests/golden/ui_routes.json` is compared as an ordered subsequence, so T-204's new routes do not break it, but its reordered auth-first position must keep the old routes in relative order.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: M (a behaviour-preserving refactor across several files; TF2 treated as L by the contract because it sits on the approval gate)
Gate answers: no new gate. `qa/gates/write-policy-tier.md` and D-018 are untouched.
Affected tests / full-suite trigger: `full-suite trigger: router/CLI seam` (TF8). The new tests plus `tests/test_ui_runs*.py` (six files), `test_cli_surface.py`, `test_cli_advice_resolves.py`, `test_cli_issues.py`, `test_schedule_model.py` were run (177 passed). The single full suite is the orchestrator's pre-push step, not the builder's (about 3 GB RAM, other agents are testing).
Pre-check[TF1]: 3ebd2fcaecbdf1c423d550bf55ab8d0a2f6dd69b uv run pytest tests/test_run_launcher.py -p no:xdist -o addopts= -> 4 passed (one `Run(` call site and one executor call site outside tests, both in `stages/run_launcher.py`; no fastapi import; `trigger_run` is 20 lines or fewer and calls `prepare_run` only); tests/test_ui_runs*.py (6 files) with zero changed assertions -> passed in the 177-test run below
Pre-check[TF2]: 3ebd2fcaecbdf1c423d550bf55ab8d0a2f6dd69b uv run pytest tests/test_run_launcher_approval.py -p no:xdist -o addopts= -> 8 passed ({manual, schedule, ci} x {no approval: 403, byte-identical data root, 0 browser sessions, 0 judge calls; covering approval: proceeds, records trigger/requested_by/slot_key/via}; no launcher parameter named skip/bypass/force/unchecked/approved/trusted; pre-change run.json loads)
Pre-check[TF3]: 3ebd2fcaecbdf1c423d550bf55ab8d0a2f6dd69b uv run pytest tests/test_routers_list.py -p no:xdist -o addopts= -> 4 passed (route table equals golden in order; the eight stubs add zero routes; a throwaway router is reachable without editing app.py); `wc -l src/autotester/ui/app.py` -> 271 (<= 300)
Pre-check[TF4]: 3ebd2fcaecbdf1c423d550bf55ab8d0a2f6dd69b uv run pytest tests/test_policy_merge.py -p no:xdist -o addopts= -> 8 passed (two fake unit dicts merge; duplicate route, unknown permission key, `public` outside the AU16 set and a route that does not exist each raise at import naming the offender). HELD part: see Held.
Pre-check[TF5]: 3ebd2fcaecbdf1c423d550bf55ab8d0a2f6dd69b uv run pytest tests/test_cli_subapp_hook.py -p no:xdist -o addopts= -> 4 passed (`--help` names and one-line help equal the golden; a throwaway sub-app answers `--help` without editing cli.py); `wc -l src/autotester/cli.py` -> 297
Pre-check[TF6]: 3ebd2fcaecbdf1c423d550bf55ab8d0a2f6dd69b uv run pytest tests/test_project_schema_team.py -p no:xdist -o addopts= -> 6 passed (every committed `projects/*/project.json` loads; golden with and without the new keys round-trips; unknown key rejected; `Source.id` stable). HELD part: `Source` provenance fields, see Held.
Pre-check[TF7]: 3ebd2fcaecbdf1c423d550bf55ab8d0a2f6dd69b uv run pytest tests/test_team_store.py -p no:xdist -o addopts= -> 50 passed (21 hostile names refused everywhere with a sentinel untouched and no directory made; slot-key encoding; kill-mid-write keeps old content; marker created once; no POSIX-only import or `os.fork`; `.work/` ignored by git and `.dockerignore`)
Pre-check[TF8]: 3ebd2fcaecbdf1c423d550bf55ab8d0a2f6dd69b uv run pytest tests/test_team_enums_home.py -p no:xdist -o addopts= -> 3 passed; uv run ruff check src tests scripts -> All checks passed!; uv run autotester doctor -> doctor: clean
Pre-check: 3ebd2fcaecbdf1c423d550bf55ab8d0a2f6dd69b uv run pytest <8 new test files> <6 tests/test_ui_runs*.py files> tests/test_cli_surface.py tests/test_cli_advice_resolves.py tests/test_cli_issues.py tests/test_schedule_model.py -p no:xdist -o addopts= ; uv run ruff check src tests scripts ; uv run autotester doctor -> 177 passed in 326 s, ruff All checks passed!, doctor clean (aggregate line for the lint: `tick.mjs` CRIT_RE only recognises C<n> ids, so it cannot see the tagged TF lines above)
Falsify[TF1..TF8]: see Capability coverage (throwaway copies, green before, red after, copies deleted)
mutant-cap-raise: the contract (team-foundation.md) names a mutation for each of TF1-TF8 and several rows name two (TF2 approval removed and escape-hatch parameter added, TF4 last-wins and unknown-key, TF6 required-field and id-fold, TF7 in-place write and hostile name); 11 mutants over 8 criteria, one per contract Mutation clause, none extra.
Metrics: start=2026-10-11T00:00Z end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=11 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=11 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
Run one pytest process at a time with `-p no:xdist -o addopts=` (no CLI `-q` otherwise).
- `uv run pytest tests/test_run_launcher.py tests/test_run_launcher_approval.py tests/test_routers_list.py tests/test_policy_merge.py tests/test_cli_subapp_hook.py tests/test_project_schema_team.py tests/test_team_store.py tests/test_team_enums_home.py` -> 4 + 8 + 4 + 8 + 4 + 6 + 50 + 3 = 87 passed
- `uv run pytest tests/test_ui_runs.py tests/test_ui_runs_live_case_approval.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_queue.py tests/test_ui_runs_serial_entry_mix_live.py` -> pass, assertions unedited (`git diff master..HEAD -- tests/` shows only added files)
- `uv run ruff check src tests scripts` -> All checks passed!
- `uv run autotester doctor` -> doctor: clean
- `wc -l src/autotester/ui/app.py src/autotester/cli.py` -> 271 and 297
- Pre-push (orchestrator): the single full `uv run pytest`, trigger `full-suite trigger: router/CLI seam`.

## Capability coverage (each criterion -> its isolating falsification)
Throwaway copy of the worktree sources in a uniquely named scratch directory outside the repo; anchor asserted unique, bytes asserted changed; copy deleted afterwards. Driver in the scratchpad, discarded.

| Criterion | falsifying edit in the copy | observed |
|---|---|---|
| TF1 | a `Run(...)` call pasted back into `trigger_run` in `routes_runs.py` | `tests/test_run_launcher.py`: 4 passed before, 2 failed after (single-call-site test and the thin-caller test) |
| TF2a | the `covering_approval(...)` call in the launcher replaced by a hand-built always-covering `RunApproval` | `test_run_launcher_approval.py`: 8 passed before, 3 failed after (every refusal row) |
| TF2b | a `skip_approval: bool = False` parameter added to `launch_run` | 8 passed before, 1 failed after (the no-escape-hatch AST test) |
| TF3 | `routes_cases.router` and `routes_project_edit.router` swapped in `ROUTERS` | `test_routers_list.py`: 4 passed before, 1 failed after (route-table snapshot) |
| TF4a | the duplicate-route check (`if route in table`) disabled | `test_policy_merge.py`: 8 passed before, 1 failed after (duplicate route) |
| TF4b | the catalogue membership check disabled | 8 passed before, 1 failed after (catalogue case) |
| TF5 | the `issues` registration dropped from `SUBAPPS` | `test_cli_subapp_hook.py`: 4 passed before, 2 failed after (command snapshot and `--help` listing) |
| TF6a | the `default=None` removed from `Project.schedule` (field required) | `test_project_schema_team.py`: 6 passed before, 3 failed after (old-file loads) |
| TF6b | `Source.notes` folded into the id derivation (stands in for a provenance field) | 6 passed before, 1 failed after |
| TF7a | `filestore.write_text` writes in place with `path.write_text` instead of temp file + `os.replace` | `test_team_store.py -k "not ignored_by_git"` (the git-ignore test needs `.git`, absent in the copy): 49 passed before, 1 failed after (kill-mid-write) |
| TF7b | the separator check in `safe_names` disabled | 49 passed before, 13 failed after (hostile-name rows) |
| TF8 | a `SlotOutcome` enum defined in `schema/enums.py` (a second vocabulary home) | `test_team_enums_home.py`: 3 passed before, 1 failed after |

All reds are assertion failures, none an import or setup error. The red counts are the number of tests that failed in each run; several tests can share one cause.

## Held (built what does not depend on it; nothing guessed)
- **TF6 Source provenance** (`uploaded_by`, `uploaded_at`, `origin` on `Source`): not built. `Source` is T-198's open ruling 1 (the provenance fields and the closed `origin` set are decided by G3/T-198, whose branch is in checking and may define them). Adding them here would define the concept twice. `Project.schedule`, `Project.tracker`, and the `Run` fields are done. The `Source.id` stability test passes over the current model and will catch a provenance field folded into the id.
- **TF4 catalogue golden and central-table wiring**: the closed permission catalogue and the central table arrive with T-204 (unmerged). G1 lands only the merge function and its tests, as TF4 allows. The "key set equals the catalogue's" golden and wiring `ROUTE_POLICY` dicts from each stub wait for T-204.
- **TF8 vocabularies**: `schema/team_enums.py` is the home and holds only the relocated schedule enums plus `RunVia`. Delivery status and source origin are not defined (their owners are G6/T-198).
- **TF8 documentation**: `docs/ARCHITECTURE.md` rows for the new modules need a DECISIONS entry naming the section first (Lab Protocol); the builder may not write `docs/DECISIONS.md`. Not done.
- **TF2 stale note**: the T-201 note calling AT-570 "open" in `.goal/goal.json` / `docs/plan.md` is not corrected: `.goal/goal.json` is orchestrator state (modified in the root checkout) and the builder is told not to edit root files. Proposed text: "closed in code, re-verified by G1 (T-205)".

## Open items and owner decisions
- **Test shims (open ruling 2).** `routes_runs.py` keeps `_execute_with_trace` and `_plan_under_shared_budget` as two-line shims, and `__all__` exports `_is_entry_case`, only so existing tests that reach those names keep their assertions unedited, as TF1 requires. Moving those tests to the launcher's names and deleting the shims is a later, small, owner-approved change.
- **Stage-to-ui dependency.** `stages/run_launcher.py` imports `autotester.ui.run_execution` for serial/parallel execution (an upward dependency). It has no FastAPI import, as TF1 requires, but a clean layering would move `run_execution.py` under `stages/`. Not done here: it would touch every test that patches `run_execution`.
- `docs/SNAPSHOT.md` was not regenerated (orchestrator-owned).
- No `qa/issues.jsonl` row appended (builder instruction); PROPOSED-ISSUE: `core/paths.py` `__all__` plus the lazy `RepoDocs` import is a seam to watch for a future circular import. Low.

## Live browser evidence
Not UI-touching in behaviour: no route, template, command or page changed. Changed paths: src/autotester/stages/run_launcher.py, src/autotester/ui/routes_runs.py, src/autotester/ui/routers.py, src/autotester/ui/app.py, src/autotester/ui/helpers.py, src/autotester/cli.py, src/autotester/cli_subapps.py, src/autotester/auth/__init__.py, src/autotester/auth/policy.py, src/autotester/core/paths.py, src/autotester/core/repo_docs.py, src/autotester/core/safe_names.py, src/autotester/store/filestore.py, src/autotester/store/team_store.py, src/autotester/schema/team_enums.py, src/autotester/schema/schedule.py, src/autotester/schema/project.py, src/autotester/schema/run.py, docs/MAP.md, tests/ (8 new files, 5 goldens).

## Status: ready-for-check
