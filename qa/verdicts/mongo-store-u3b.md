# Verdict - mongo-store-u3b (checker A, functional/contract)
Verdict: PASS
Cycle checked: 0
Head tested: 0c8e86c7 (feat/mongo-store-u3b; code commit 4e296610, base 9b884ac9). Unit U3b, normal (not dual). Criterion judged: M16, the listing / exists / stat / read sites of `core/env.py`, `ui/credential_guard.py`, `ui/helpers.py`, `ui/project_view.py`, `stages/schedule_wiring.py`. M16 as a whole (doctor rule, other sweeps) is U3c's and is not closed by this PASS.
Class: all LOCAL. No Mongo connection; no `.env` value read or printed. Worktree venv, `PYTHONPATH=<worktree>/src`, `env -u ANTHROPIC_BASE_URL`, `-o addopts=`, at most 2 test files per pytest call. I did not read any other checker's verdict on this unit. Every command below was run by me.

## Result per check
| Check | Result | Evidence |
|---|---|---|
| Moved sites use the public filestore API only | PASS | `git diff 9b884ac9..HEAD -- src`: `core/env.py:69` imports `exists_path, list_children, read_json`; `helpers.py:32`, `project_view.py:17`, `schedule_wiring.py:41` import `exists_path, list_children, mtime_path` (all defined at `store/filestore.py:214,285,291,297`). `grep -n "_route"` over the five touched files: no match. No hand-rolled listing helper added (`credential_guard.py:65-67` reuses `helpers._project_slugs`, one concept one place). |
| Identical behaviour with `AUTOTESTER_STORE` unset | PASS (two declared deltas only) | Differential below. |
| No credential VALUE logged, printed or moved | PASS | `git diff 9b884ac9..HEAD -- src tests` grep for `print(`, `logging`, `logger`: none. `project_credentials` still returns namespaces and key names only. `tests/test_state_sweep_u3b.py` uses key names (`DEMO_PASSWORD`, `ALPHA_OWN_TOKEN`) and no values. The `ValueError` from `read_json` (`filestore.py:223`, may quote a malformed row) is swallowed by `continue` at `env.py:81-82` and never logged. |
| Remaining raw sites are host config | PASS | Finding 6. |
| Doctor's `repo_redactor` duplicate is not U3b's | CONFIRMED | Finding 7. |
| Tests / lint / mutation | PASS | Commands below. |

## Differential, old vs new (scratch tree under `.work/u3b-check/`, deleted afterwards)
The old bodies were copied verbatim from the diff into a harness and run against the new functions over the same scratch data root (`AUTOTESTER_ROOT` set, `AUTOTESTER_STORE` and `AUTOTESTER_STORE_AREAS` unset). Project dirs: three valid projects, `garbage` (bad JSON), `listroot` (`[1,2]`), `secobj` (`secrets` an object), `keyless` (rows without `key`, a string row), `nonlist` (`secrets` a string), `nonstr` (`key: 5`), `good`, `emptydir`, a stray file, `.hidden`, `x.lock`, `secnull` (`secrets: null`).
```
project_credentials  (secnull removed)  -> same prefixes except old also lists X_LOCK_ (the x.lock dir); same declared keys
_project_slugs       (clean tree)       -> SAME;  with x.lock present: old lists 'x.lock', new does not
refuse_foreign_key listing              -> SAME
refuse_foreign_key ALPHA_PW / ALPHA_TWO_PW / ALPHA_TWO_X / BETA_X -> ok / 400 other-namespace / 400 other-namespace / 400 must-start-with
_last_change  alpha / nonexistent / cases-only / after cases write -> SAME x4
_has_corrupt_run none / corrupt run.json / clean (plus stray file, empty run dir, r.lock dir) -> SAME x3
scheduled_projects(None) and scheduled_projects(<root outside AUTOTESTER_ROOT>), with a scheduled, a manual, a broken and a stray dir -> SAME (items equal, invalid == ['broken'])
scheduled_projects(<root with no projects/>) -> ([], []) both
project_credentials with secnull: old RAISE TypeError, new returns (namespace reserved, no keys)
```
Deltas found: (a) `secrets: null` (declared in the manifest); (b) a directory named `*.lock` or `.tmp-*` under `projects/` is no longer listed because `FileBackend.children` skips them (`filestore.py:104-108`; manifest judgement call 4). Slugs cannot have that shape. Both accepted.

## Commands run (mine) and outputs
```
pytest tests/test_state_sweep_u3b.py tests/test_env_loading.py        -> 16 passed, 7 warnings in 176.76s   (7 + 9)
pytest tests/test_schedule_wiring.py tests/test_state_selection.py    -> 42 passed
pytest tests/test_ui_credential_safety.py tests/test_ui_credential_safety_project.py -> 29 passed
pytest tests/test_ui_secrets_declaration.py tests/test_ui_env_editor.py -> 22 passed, 1 skipped
pytest tests/test_ui_project_edit.py tests/test_ui_dashboard.py       -> 27 passed
pytest tests/acceptance/test_ta08_schedule_to_report.py tests/acceptance/test_ta11_restart_exactly_once.py -> 8 passed
pytest tests/test_ui_credential_exemption.py tests/test_ui_credential_exemption_scope.py -> 11 passed
pytest tests/test_role_port_authz.py                                   -> 5 failed, 11 passed
   same file against `git archive 9b884ac9 src` (PYTHONPATH=base src, import path printed to confirm) -> the same 5 FAILED, 11 passed
   (2 of the 5 show `getaddrinfo ENOTFOUND a.localhost`; the others are downstream empty-result assertions of the same oracle path). Identical on base: not U3b's.
uv run ruff check src tests scripts                                    -> All checks passed!
autotester doctor > file (exit 1)                                      -> 1 violation: duplicate-concept store/mongo_routes.py:185 'repo_redactor' also in store/blobs.py; the rest are D-087 advisories
python scripts/mutation_check.py qa/evidence/mongo-store-u3b/mutations.json --repo .  -> 14/14 mutations killed (each by the test it claimed)
```
The sampled regression pairs are 7 of the 47 in `qa/evidence/mongo-store-u3b/regression-pairs.txt`, chosen to cover every touched module (schedule wiring, credential guard, env editor / secrets declaration, project view / dashboard, acceptance schedule, env loading). I did not rerun the other 40; the full suite was not run (low-memory rule).

## Findings
1. **PASS, no blocking finding.** All five named sites and `ui/helpers.py::_project_slugs` read through `list_children` / `exists_path` / `mtime_path` / `read_json` (`core/env.py:68-80`, `helpers.py:159-162`, `credential_guard.py:65-67`, `project_view.py:158-168`, `schedule_wiring.py:105-113`). The tests flip `projects` and `runs` to the fake Mongo and assert `<root>/projects` is absent on disk, so a site still touching the filesystem fails; the 14 mutations confirm they are not vacuous.
2. **`SecretDeclarations` (`schema/project.py:66-70`): accepted, Note.** `extra="forbid"` is the rule for domain shapes, but this is a read projection of `project.json`, not a domain shape, and `extra="ignore"` already has precedent in `schema/video_review.py:76,92`. `Project` cannot be reused for the read because it would reject a file the old raw-dict read accepted, and `filestore.py` has no public raw-text read, so `read_json` needs a model. The docstring states why. One concept, one place: the key list is still defined by `SecretRef`; this model only extracts it. `schema/project.py` is 296 lines and `ui/helpers.py` 299 (cap 300), so the next edit to either needs a split.
3. **Function-local imports (`core/env.py:68-69`, `credential_guard.py:65`): accepted.** Cycle verified: `store/filestore.py:23` imports `store/mongo_routes`, which imports `core.env` (`mongo_routes.py:20`); and `ui/helpers.py` imports `ui.credential_guard`. A new module to break either would need a D-122 entry. Each import carries a one-line reason comment.
4. **`"secrets": null` change: accepted.** Old code raised an uncaught `TypeError` out of `project_credentials`; new code treats the file as unreadable and still reserves the namespace (`env.py:81-82`). Strictly safer; confirmed by the harness.
5. **Editing `stages/schedule_wiring.py`: accepted.** The change is confined to `scheduled_projects` plus one import; the U3c baseline row (`schedule_wiring.py:104:glob | U3b`) names it as U3b's. A project config that vanishes between listing and stat is still reported `invalid` (`schedule_wiring.py:111-113`), as the old `OSError` path did. No other `stages/` file is touched (`git diff --stat`).
6. **Remaining raw sites are host config, not state:** `core/env.py:104` and `:203` (`.env` itself), `:125-127` (`st_dev` ancestor walk), `:161` (`/proc/mounts`). The five touched modules contain no other `exists/stat/glob/iterdir/read_text` call (grep). The `.env` editing routes remain with U11, as the manifest says.
7. **Doctor violation not counted.** `repo_redactor` is defined at `store/mongo_routes.py:185` and in `store/blobs.py`; `git diff --stat 9b884ac9..HEAD -- src | grep store/` returns nothing, and `9b884ac9` (the U4 merge, an ancestor of HEAD) already contains both. It is U4 vs U5a and must be fixed where they meet, not here. It is the only reason `autotester doctor` exits 1.
8. **Not judged here:** the manifest's advice about deleting/renumbering `[tool.autotester.doctor.state-bypass]` baseline rows. That rule and table are not on this branch (`grep state-bypass pyproject.toml src` is empty); it belongs to U3c's merge.
