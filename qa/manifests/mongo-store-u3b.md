# Manifest - mongo-store-u3b

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29), unit U3b. **Criticality:** normal (not dual). Seam sweep only: no Mongo code, no driver import, no new `src/` module.
**Authority:** D-120, D-121, D-122 (edit in place; the D-122 file list is untouched)
Round cap: normal unit, D-014 cap of 2 fix cycles applies.
**Branch:** `feat/mongo-store-u3b` (contains master `61691ec7` = U1, U2, U6a, U3a, U5a, merged with `feat/mongo-store-u4` at `9b884ac9`). Not merged to master, not pushed.
**Base SHA:** `9b884ac9`
**Code SHA:** `4e2966100d8b8b901fe28683a9366d43d2a162d5` (the only code commit; this manifest is a second commit on top of it)
**Criteria judged by U3b:** M16 (the listing / exists / stat sites of `core/env.py`, `ui/credential_guard.py`, `ui/helpers.py`, `ui/project_view.py`, `stages/schedule_wiring.py`).

## What changed

| File | Kind | Change (line numbers at the code SHA) |
|---|---|---|
| `src/autotester/core/env.py` | E in place | `project_credentials` `:65-85`: `(root/"projects").glob("*/project.json")` + `read_text` + `json.loads` became `list_children` / `exists_path` / `read_json(config, SecretDeclarations)` (`:68-80`). The store import is function-local (`:69`) because `store/mongo_routes.py` imports `core.env` at module level (a top-level import would be a cycle). `import json` removed (unused now). |
| `src/autotester/schema/project.py` | E in place | `SecretDeclarations` `:66-71` (296 lines): a lenient view of a `project.json` (`extra="ignore"`, `secrets: list[object]`). `read_json` needs a model; the full `Project` would reject a project the old raw-dict read accepted, so the read keeps its tolerance. Regenerated `docs/MAP.md` carries the one new row. |
| `src/autotester/ui/helpers.py` | E in place | `_project_slugs` `:159-162` (299 lines): `iterdir` + `exists` became `list_children` + `exists_path`. Import `:32`. |
| `src/autotester/ui/credential_guard.py` | E in place | `refuse_foreign_key` `:65-67`: its private copy of the same listing now calls `_project_slugs` (one concept, one place; function-local import `:65` because `helpers` imports this module). `repo_root` import removed (unused). |
| `src/autotester/ui/project_view.py` | E in place | `_last_change` `:158-159` (`mtime_path` for config and cases), `_has_corrupt_run` `:167-168` (`list_children` + `exists_path`). Import `:17`. |
| `src/autotester/stages/schedule_wiring.py` | E in place | `scheduled_projects` `:105-113`: glob + `config.stat()` became `list_children` + `exists_path` + `mtime_path`; a config that vanished between the listing and the stat is still named `invalid` (`FileNotFoundError` inside the existing `try`, `:111-113`). Import `:41`. **Note:** `stages/` is sibling-owned (U3a/U3d), but the task and the U3c baseline both name this file as U3b's (`stages/schedule_wiring.py:104:glob | U3b`); no other file under `stages/` was touched. |
| `tests/test_state_sweep_u3b.py` | N (tests) | 7 tests, see below. |
| `docs/MAP.md` | regenerated | `autotester map`, one row. |
| `qa/evidence/mongo-store-u3b/{mutations.json,mutation-run.txt,regression-pairs.txt}` | N | evidence |

No `src/` module added. No credential value is read, printed, logged or moved: `project_credentials` still returns only namespaces and key names; the only access path changed.

## Criteria map (M16)

| Site (was) | Now | Test (falsifier it kills) |
|---|---|---|
| `core/env.py:71 glob`, `:75 read_text` | `env.py:74-80` | `test_declared_credentials_are_read_from_the_store` (mongo areas, nothing on disk, extra field in the document, junk and key-less rows); `test_file_mode_credentials_tolerate_every_shape_of_project_json` (file mode: garbage JSON, list root, `secrets` an object, key-less row, dir without `project.json`, a stray file, missing `projects/`) |
| `ui/credential_guard.py:67 iterdir`, `:68 exists` | `credential_guard.py:65-67` | `test_a_foreign_namespace_is_found_through_the_store` |
| `ui/helpers.py:160 exists`, `:162 iterdir` | `helpers.py:159-162` | `test_the_project_list_comes_from_the_store` |
| `ui/project_view.py:165 exists`, `:167 iterdir` (+ `:157 stat`/`exists`, not in the baseline) | `project_view.py:158-168` | `test_last_change_reads_the_store_mtime`, `test_a_corrupt_run_is_found_through_the_store` |
| `stages/schedule_wiring.py:104 glob` (+ `:108 stat`, not in the baseline) | `schedule_wiring.py:105-113` | `test_scheduled_projects_are_listed_from_the_store` (includes a `projects/stray/` with no `project.json`) |

Each mongo test sets `AUTOTESTER_STORE_AREAS=projects=mongo,runs=mongo` over `fake_mongo`, writes state only through `filestore`/`ProjectStore`, and asserts `<root>/projects` does not exist on disk afterwards; a site that still touches the filesystem sees an empty directory and fails.

**Identical behaviour with `AUTOTESTER_STORE` unset:** every touched module's existing tests pass unedited (regression pairs below). One deliberate widening: `project_credentials` on a `project.json` whose `secrets` is `null` used to raise `TypeError` (uncaught); it is now treated as unreadable (namespace reserved, no keys). Every other shape gives the same result as before.

## Raw filesystem access left on purpose (reason per site)

| Site (at code SHA) | Reason |
|---|---|
| `core/env.py:104` `exists` (`dollar_value_keys`), `:203` `exists` (`load_repo_env`) | the repo-root `.env` itself: host config, not state (U11 owns credential moves) |
| `core/env.py:125` `exists`, `:127` `stat` (`_device`) | host filesystem probe (`st_dev` walk), not state |
| `ui/app.py:125`, `ui/env_editor.py:132,165`, `ui/routes_settings.py:34`, `ui/routes_credentials.py:213`, `ui/routes_role_accounts.py:151,196-211` | `.env` read/write; outside the four named modules; UNOWNED / U11 in the U3c baseline, not touched |
| `ui/routes_live.py:103` (`_SRC_ROOT.rglob`) | the source tree, not state |

## For U3c (baseline in `pyproject.toml [tool.autotester.doctor.state-bypass]`, not edited here)

I ran U3c's `_sites` (from `15079067:src/autotester/ledger/committed_fresh.py`, AST part only) over my five files: it reports **no site** in `ui/credential_guard.py`, `ui/helpers.py`, `ui/project_view.py`, `stages/schedule_wiring.py`, and only `core/env.py` `[(104,exists),(125,exists),(127,stat),(203,exists)]`.

- **Delete** these baseline rows (they would be reported stale): `core/env.py:71:glob | U3b`, `stages/schedule_wiring.py:104:glob | U3b`, `ui/credential_guard.py:67:iterdir | U3b`, `ui/credential_guard.py:68:exists | U3b`, `ui/helpers.py:160:exists | U3b`, `ui/helpers.py:162:iterdir | U3b`, `ui/project_view.py:165:exists | U3b`, `ui/project_view.py:167:iterdir | U3b`.
- **Renumber** the `permanent` rows of `core/env.py` (my edit moved them): `:98:exists` -> `:104:exists`, `:119:exists` -> `:125:exists`, `:121:stat` -> `:127:stat`, `:197:exists` -> `:203:exists`.

## Things the checker should look at (judgement calls)

1. **Function-local imports** in `core/env.py:68-69` (cycle: `store.mongo_routes` imports `core.env`) and `ui/credential_guard.py:65` (cycle: `helpers` imports `credential_guard`). Alternative would be a new module; none is on the D-122 list.
2. **`SecretDeclarations`** is a new schema model (not a new module) added only to keep the lenient read. Say so in the verdict if you would rather it sat elsewhere.
3. `refuse_foreign_key` now reuses `ui.helpers._project_slugs` instead of its own copy (a private name used across modules, as `ui/app.py` and `ui/theme.py` already do).
4. A directory entry named like `*.lock` or `.tmp-*` under `projects/` is no longer listed (`FileBackend.children` skips them); slugs cannot have that shape.
5. **Not run:** the full suite in one invocation (low-memory rule). `tests/test_role_port_authz.py` has its 5 known environmental failures (pair 4 below shows `5 failed`; `tests/test_env_loading.py` alone: 9 passed).
6. Doctor reports one violation, `duplicate-concept: store/mongo_routes.py:185 'repo_redactor' also defined in store/blobs.py`. It comes from the merge of U4 and U5a (`store/*`, not mine) and is outside U3b.

## Verify (run in `D:/autoTesting/.claude/worktrees/mongo-u3b`, `PYTHONPATH=<worktree>/src`, `env -u ANTHROPIC_BASE_URL`, `-o addopts=`, at most 2 files per call)

```
pytest tests/test_state_sweep_u3b.py                                      -> 7 passed
regression pairs (qa/evidence/mongo-store-u3b/regression-pairs.txt, 47 two-file calls: every schedule*, test_env_loading, test_approval_prod_gate, test_cli_schedule,
   acceptance ta08/ta11/ta12/ta13, test_state_*, test_teach*, every test_ui_*, test_role_port_authz)  -> all passed except the 5 known in test_role_port_authz
pytest tests/test_env_loading.py                                          -> 9 passed
ruff check src tests scripts                                              -> All checks passed!
autotester map                                                            -> docs/MAP.md regenerated (one row)
autotester doctor  (redirected to .work/doctor-u3b2.txt, exit 1)          -> 1 violation (the pre-existing repo_redactor duplicate, see 6); D-087 advisories only otherwise
python scripts/mutation_check.py qa/evidence/mongo-store-u3b/mutations.json --repo .  -> 14/14 mutations killed
```

Mutation run: `qa/evidence/mongo-store-u3b/mutation-run.txt` (first run killed 13/14: `a10` claimed a file-mode test that cannot reach a key-less dict row; the claim was corrected, nothing else changed).
