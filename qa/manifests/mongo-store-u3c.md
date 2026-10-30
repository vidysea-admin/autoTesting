# Manifest - mongo-store-u3c

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29), unit U3c (sweep of trace / orchestrate checkpoint / audit log / delivery inbox / schedule store, plus the M16 doctor rule). **Criticality:** normal.
**Authority:** D-120, D-121, D-122/D-123 (no new `src/` module; see judgement call 1)
Round cap: normal unit, D-014 cap of 2 fix cycles applies.
**Branch:** `feat/mongo-store-u3c` (cut from master `0a2cbe45`). Not merged to master, not pushed.
**Base SHA:** `0a2cbe45`
**Code SHA:** `15079067d171f64a6d6c6bf7aeb6fb172b3000fd` (the only code commit; this manifest is a second commit on top of it)
**Criteria judged by U3c:** M16 (rule + baseline), and the "identical with `AUTOTESTER_STORE` unset" half of M14 for the touched modules. M19/M20 (`create_exclusive`, `put_if`) for the claim and checkpoint-CAS sites are NOT done here: the public store API cannot express them yet (see "Deferred sites").

## Scope said plainly

The public `filestore` API today is write_text / write_bytes / write_json / read_json / read_jsonl / append_jsonl / delete_jsonl_row / upsert_jsonl plus `backend_for`. It has no exists-by-path, list-children, mtime, raw append, create-exclusive-by-path or delete-by-path. Per the coordinator's note I added no path-to-key helper of my own and did not import the private `_route` or `_atomic_write`. So the sweep reroutes only what the public wrappers can express (checkpoint flush, heartbeat) and every other raw site is on a baseline row tagged `U3c-deferred, needs <API>`, so it cannot be forgotten and the rule keeps the list from growing.

## What changed

| File | Kind | One job / change |
|---|---|---|
| `src/autotester/ledger/committed_fresh.py` (209 lines) | E in place | hosts the new rule `check_state_bypass(root)` `:186`; constants `STATE_BYPASS` `:99`, `STATE_BYPASS_STALE` `:100`, `_STATE_MODULES` `:102`, `_METHODS` `:108`, `_OS_CALLS` `:110`; helpers `_is_state :118`, `_bindings :126` (module-wide taint fixpoint), `_writes :144`, `_kind :151`, `_sites :167`, `_allowed :177`. Scans `src/autotester/**/*.py` except `store/` and `browser/`. |
| `src/autotester/doctor.py` (300 lines, cap 300) | E in place | imports `check_state_bypass` (multi-line import) and runs it in `run()` `:298`. |
| `pyproject.toml` | E in place | `[tool.autotester.doctor.state-bypass]` `:78`: `baseline` (83 rows, each `path:line:kind \| owner or reason`) and `permanent` (4 rows). |
| `src/autotester/stages/orchestrate_checkpoint.py` | E in place | `flush()` `:248-257` writes through the public `write_text` (`:24` import) instead of the private `_atomic_write`. |
| `src/autotester/stages/schedule_store.py` | E in place | `write_heartbeat` `:245-247` writes through `write_text` (`:32` import); module docstring heartbeat bullet `:13` updated. |
| `tests/test_state_bypass_rule.py` | N (test) | 29 tests of the rule. |
| `tests/test_state_sweep_u3c.py` | N (test) | 3 tests: flush and heartbeat land in the in-memory backend, not on disk; with the file backend the heartbeat is the same file as before. |
| `qa/evidence/mongo-store-u3c/` | N | `mutations.json`, `mutation-run.txt`, `regression-pairs.txt`, `doctor.txt` |

No other `src/` module was added or touched. Files owned by siblings (`store/*`, `core/safe_names.py`, `stages/` sweep files other than the two above, `sources/`, `core/env.py`, `ui/*`) are untouched.

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| M16 doctor rule fails a raw write on a state path | `committed_fresh.py:186` (`check_state_bypass`), wired `doctor.py:298` | `test_state_bypass_rule.py::test_the_falsifier_write_text_on_a_projectpaths_path_turns_doctor_red` (runs `doctor.run`), `::test_every_listed_call_on_a_project_path_in_stages_is_flagged` x 11 call kinds (write_text, write_bytes, unlink, glob, rglob, iterdir, exists, stat, open, os.replace, shutil.rmtree) |
| M16 reads vs writes, exemptions, non-state | `_writes :144`, `_EXEMPT_DIRS`, `_is_state :118` | `::test_a_read_is_not_flagged_a_write_mode_is`, `::test_store_and_browser_are_exempt[store/browser]`, `::test_a_path_that_is_not_state_is_not_flagged`, `::test_repo_root_is_state_only_under_work_or_projects` (4 forms), `::test_taint_follows_a_derived_name` |
| M16 state-persisting modules (paths come from callers) | `_STATE_MODULES :102` | `::test_state_persisting_modules_flag_any_path_a_caller_hands_them` x 6 modules (and a non-listed module with the same code is not flagged) |
| M16 explicit baseline allowlist, `file:line`, owner-tagged; list only shrinks | `_allowed :177`, `check_state_bypass :186`, `pyproject.toml:78` | `::test_a_baseline_row_allows_exactly_that_site_and_a_stale_row_is_reported` (a moved line gives violation + stale; an extra row gives stale), `::test_a_permanent_row_allows_a_host_check` |
| doctor clean on this branch | whole tree | `::test_this_repo_is_clean`; `uv`-free `autotester doctor` exit 0 (below) |
| Behaviour identical with `AUTOTESTER_STORE` unset | `orchestrate_checkpoint.py:257`, `schedule_store.py:247` | `test_state_sweep_u3c.py::test_with_the_file_backend_the_heartbeat_is_the_same_file_as_before` (same path, same body, no leftover temp), plus the existing tests of every touched module (regression below) |
| flush / heartbeat go through the store | same | `test_state_sweep_u3c.py::test_the_checkpoint_flush_writes_through_the_store`, `::test_the_heartbeat_writes_through_the_store` (in-memory backend swapped in; a disk write fails the test) |

## Baseline allowlist (83 baseline rows, 4 permanent)

Tags by owner: U3a (stages/, sources/ sites) 40 rows; U3b 8 rows; U3c-deferred 25 rows; U11 6 rows; UNOWNED 4 rows.

U3b rows (coordinator's list, with the lines the rule actually flags): `core/env.py:71` glob (`:72-74` are not separate calls), `ui/credential_guard.py:67` iterdir and `:68` exists, `stages/schedule_wiring.py:104` glob, `ui/project_view.py:165` exists and `:167` iterdir, `ui/helpers.py:160` exists and `:162` iterdir (the coordinator quoted `:157-168` / `:158`; the flagged lines are the ones listed).

Permanent rows (never state): `core/env.py:98` and `:197` exists (repo-root `.env` presence; U11 owns credential moves), `core/env.py:119` exists and `:121` stat (host `st_dev` probe). `core/env.py:155` (`/proc/mounts`) is not flagged by the rule, so it needs no row.

### Deferred sites (U3c-deferred, with the API each needs)

| Site | Needs |
|---|---|
| `core/trace.py:70` open | raw append / create_exclusive / delete on the backend (U4/U7) |
| `core/trace.py:142`, `:156` exists | `exists_path` (U4) |
| `auth/audit.py:23` open | raw append / create_exclusive / delete (U4/U7) |
| `delivery/inbox.py:85` write_text, `:87` os.link, `:92` unlink | raw append / create_exclusive / delete (U4/U7) |
| `delivery/inbox.py:122` iterdir | `list_children` (U4) |
| `stages/orchestrate_checkpoint.py:173`, `:204` exists | `exists_path` (U4). The `put_if` CAS on `flush` is also not done: `_digest`/`_load` read the path directly. |
| `stages/schedule_store.py:45`, `:96` os.open (claim O_EXCL, `_append_line`) | `create_exclusive` / raw append (U4/U7) |
| `stages/schedule_store.py:59`, `:144`, `:195` glob | `list_children` (U4) |
| `stages/schedule_store.py:171`, `:189`, `:242` shutil.rmtree; `:185`, `:237` os.replace; `:233` write_text; `:235` os.rename; `:238` unlink | raw delete / rename (U4/U7) |
| `stages/schedule_store.py:180`, `:183` exists | `exists_path` (U4) |

When a sibling lands the API and removes a site, its baseline row turns into `state-bypass-stale` and doctor goes red until the row is deleted, so the list only shrinks.

## Things the checker should look at (judgement calls)

1. **Rule host module.** D-122/D-123 list no doctor-rule module, `doctor.py` and the other ledger check modules are at the 300-line cap, and a new file is a STOP. I put the rule in the existing `ledger/committed_fresh.py` (209 lines) and said so in its docstring. If you want it in its own module that needs a D-entry first; moving it is mechanical.
2. **Exact-line baseline.** Rows match on `file:line:kind`, so any edit that shifts a deferred site's line turns doctor red until the row is re-pinned. That is deliberate (contract wants `file:line`) but it costs sibling units a row edit each; U3a/U3b will hit this.
3. **Heuristic taint, not a type check.** The rule is AST-based: a name is state if assigned from `ProjectPaths` / `team_path` / `paths` or from `repo_root()`/`root`/`base` joined with `.work`, `projects` or `.env`, propagated to a fixpoint (4 passes, `_bindings :126`). It can miss a path built through a call it does not know (e.g. a helper that returns a project path), and it counts every flagged call in the six `_STATE_MODULES` because those take paths from callers. Consequence: false negatives are possible outside those modules; the baseline protects what is known, not what is hidden.
4. **`core/env.py` is a state-persisting module** (`_STATE_MODULES`), so its `.env` accesses are flagged; hence the four permanent rows. U11 owns moving credentials.
5. **UNOWNED and U11 tags are mine.** No unit row covers `ui/app.py`, `ui/routes_settings.py`, `ui/intake_upload.py`, `ui/routes_bench_inputs.py` (4 rows tagged `UNOWNED (no unit row covers ui/)`); the 6 `ui/routes_role_accounts.py` / `routes_credentials.py` rows are tagged U11 on the same reasoning. The contract owner should assign them.
6. **Mode detection** (`_writes :144`): a call counts as a write only if a short string literal (<= 4 chars) in the positional args or `mode=` contains one of `w a x +`. A mode passed as a variable is read as a read. Pinned by `test_a_read_is_not_flagged_a_write_mode_is`.
7. **Equivalence with the store unset** relies on `write_text` being the same atomic temp+replace the old private `_atomic_write` did (U2 manifest, judgement call 3); I did not diff bytes of an old-vs-new run beyond the heartbeat test.

## Verify (run in `D:/autoTesting/.claude/worktrees/mongo-u3c`, worktree `.venv`, `PYTHONPATH=src`, `-o addopts=`, at most 2 files per call)

```
pytest tests/test_state_bypass_rule.py tests/test_state_sweep_u3c.py   -> 33 passed
pytest tests/test_committed_fresh.py tests/test_doctor.py              -> 48 passed
ruff check src tests scripts                                           -> All checks passed!
autotester doctor  (redirected, qa/evidence/mongo-store-u3c/doctor.txt) -> exit 0, "doctor: clean"
mypy (3 touched src files)                                             -> 2 errors, both pre-existing (below)
python scripts/mutation_check.py qa/evidence/mongo-store-u3c/mutations.json --repo .  -> 14/14 mutations killed
```

Mutants: m1-m11 on the rule (flagged-method set, browser exemption, read-as-write, stale reporting, empty baseline, empty permanent list, `.work` state part, bare `repo_root`, `core/trace.py` module list, taint propagation, doctor wiring), s1-s3 on the sweep (flush direct disk write, heartbeat direct disk write, heartbeat key rename). Full output: `qa/evidence/mongo-store-u3c/mutation-run.txt`.

**Regression of the touched modules' existing tests** (`qa/evidence/mongo-store-u3c/regression-pairs.txt`, two files per call): schedule_purge_crash+schedule_gaps 26, schedule_failures+schedule_wiring 35, schedule_catchup+schedule_overlap 28, schedule_advisories+schedule_inbox 7, schedule_routes+orchestrate 45, cli_orchestrate+cli_orchestrate_resume 8, orchestrate_downstream+generic_acceptance 17, doctor_oracle_exempt+schedule_tick 34 passed / 1 failed.

## Pre-existing failures (not caused by U3c)

- `tests/test_schedule_tick.py::test_the_scheduler_side_reaches_no_browser_or_pipeline_module_even_transitively` fails with `autotester.auth.access -> autotester.auth.store` and `-> auth.store_sqlite`. It fails on master `0a2cbe45` too: `git show 0a2cbe45:src/autotester/auth/access.py` already imports `autotester.auth.store`, and the test's `ALLOWED_OUTSIDE` lacks `autotester.auth.store` and `autotester.auth.store_sqlite`. Not touched.
- mypy: `stages/schedule_store.py:31` (`SlotOutcome` not exported by `schema.schedule`) and `stages/orchestrate_checkpoint.py:256` (`SerializerProtocol` has no `redactor`). Both on lines I did not change.

## Not run

The full suite in one invocation (low-memory rule); no reviewer or checker dispatched (checker's job).
