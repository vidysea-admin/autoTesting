# Manifest - e2e-fixes-e8

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/e2e-fixes.md`, unit E8 (E5 hardening). **Criticality:** HIGH.
**Authority:** no new module, no `qa/contracts/` edit, no `src/` edit.
**Branch:** `feat/e2e-e8` (worktree `D:/autoTesting/.claude/worktrees/e2e-e8`), base `6eb21a54`. Not merged, not pushed.
**Code SHA:** the commit that adds this file, `git log -1 feat/e2e-e8`
**Criteria judged by E8:** E8.1, E8.2 (a)-(f), E8.3.

## What changed

| File | Kind | Change |
|---|---|---|
| `docker/entrypoint.sh` | E in place | `select_mongo_store`: after the auth-file branch, `for proj in "$root"/projects/*/project.json; if [ -f "$proj" ]` prints one line (root path only, no slug, no URI) and `return 0`. Same `${AUTOTESTER_ROOT:-/app}` expression as the auth path. Presence only. `all_state_on_mongo` and `warn_if_ephemeral` untouched. |
| `docker/DEPLOY.md` | E | `## State store on MongoDB`: new paragraphs for (a) both variables for all nine areas, (b) fresh data root only, (c) bad URI stops start-up and the previous Cloud Run revision serves, (d) `AUTOTESTER_STORE=file` escape hatch, (e) `AUTOTESTER_FIRST_ADMIN_EMAIL` first; (f) sits in the escape-hatch paragraph. Reworded: "A fully flipped service sets both", "Flipping is a human gate (G1)" (now: the first `--apply` and every flip of existing data), "volume stays required until G1" (now: while any area is on files; also in **Persistent storage**). The URI row notes the auto-selection. No URI shape added. |
| `tests/test_container_entrypoint_behaviour.py` (298 lines) | E, additions only | 6 test functions, 10 cases, E8.1 (a)-(h) |
| `tests/test_mongo_deploy_u10.py` | E | pins moved to the new sentences, see below |
| `qa/evidence/mongo-store-u10/mutations.stale.json` | N | D-048 sidecar for the renamed U10 test (doctor `evidence-spec-stale-unexplained`) |
| `docs/SNAPSHOT.md` | regenerated | one line `D-126` -> `D-131`; pre-existing drift doctor flagged (E7 regenerated it the same way) |
| `qa/evidence/e2e-fixes-e8/mutation-run.txt` | N | mutation runs |

## Criteria map

- **E8.1** `docker/entrypoint.sh` `select_mongo_store`, project loop. Cases: (a),(f) `test_e8_a_project_file_blocks_the_selection_with_one_line[zeta|with space]`; (b) `test_e8_auth_file_and_project_together_print_exactly_one_line`; (c),(d),(e),(g) `test_e8_only_a_direct_project_json_counts[empty-projects|slug-dir-only|too-deep|wrong-level|no-projects-dir]` (each asserts both variables exported and all nine areas against `store.mongo_routes.AREAS`); extra: a directory named `project.json` does not count; (h) `_no_leak` (canary and slug absent) in every case, plus `test_e8_the_real_script_keeps_files_for_a_project_and_leaks_nothing` (real script, stub-recorded argv). rc 0 is asserted by `_select`.
- **E8.2** sentences (a)-(f) pinned by `test_guide_says_the_entrypoint_sets_both_variables_for_every_area`, `test_guide_says_the_selection_is_made_only_on_a_fresh_data_root`, `test_guide_says_a_bad_uri_stops_start_up_and_the_old_revision_serves`, `test_guide_gives_the_escape_hatch_in_the_process_environment`, `test_guide_says_to_set_the_first_admin_before_the_first_start`, `test_guide_says_a_data_root_env_store_choice_does_not_beat_the_platform_uri`.
  Pins moved: `test_guide_says_auth_moves_only_with_its_own_entry` (the old global-value regex became "`auth` moves only with its own entry ... global value"; `auth=mongo` kept); `test_guide_keeps_the_gcs_volume_required_until_g1_and_cites_d125` renamed `..._required_while_any_area_is_on_files_and_cites_d125` (D-125 and G1 kept; "stays required while any area is on files" pinned in MONGO and in CLOUD_RUN; "scratch only"; the `--add-volume` check kept). Unchanged: `--max-instances 1`/CAS, fail-closed ("no file fallback" still present), D-123/"plain", and the `mongodb(+srv)://...@` absence check verbatim.
- **Sentence (f) verified against code:** the loader's guard is `if not key or not value or os.environ.get(key): continue` at `src/autotester/core/env.py:213` (the contract cites :188-189; those lines are now the docstring that says existing environment variables win). The entrypoint exports `AUTOTESTER_STORE=mongo` into the process before Python starts, so `load_repo_env` skips a `.env` `AUTOTESTER_STORE=file`. True as written.
- **E8.3** `git diff` on `tests/test_container_entrypoint_behaviour.py` and `tests/test_storage_warning.py`: 71 added, 0 removed; `test_storage_warning.py` unchanged. The E5.1-E5.3 cases pass unmodified.

## Evidence (exact commands, Windows Git Bash, TMP/TEMP pointed at `.work` because C: is full)

```
env -u ANTHROPIC_BASE_URL uv run pytest tests/test_container_entrypoint_behaviour.py tests/test_storage_warning.py -o addopts= -q   -> 59 passed, 1 skipped
env -u ANTHROPIC_BASE_URL uv run pytest tests/test_mongo_deploy_u10.py -o addopts= -q                                           -> 32 passed
env -u ANTHROPIC_BASE_URL uv run ruff check src tests scripts                                                                  -> All checks passed!
env -u ANTHROPIC_BASE_URL uv run autotester doctor > .work/e8_doctor.txt                                                       -> see below
```

The skipped test is the pre-existing non-executable-python case (Windows). The full suite was NOT run (machine low on memory, per brief).

Doctor: before the commit it reported `1 violation(s)` = `stale-committed: docs/SNAPSHOT.md` (it clears once the regenerated SNAPSHOT is committed, which this commit does). `decision-citation-known-disputed` lines are advisory.

## Mutation evidence

`qa/evidence/e2e-fixes-e8/mutation-run.txt`: M1-M4 on the entrypoint, D1-D3 on DEPLOY.md; all killed, files restored (cmp). Two contract hints differ honestly: (b) is killed by M4 (a second printed line), not by M1 (the auth branch returns first), and the `-d projects/*` mutation does not fail (c) (an empty `projects/` leaves the glob literal) but does fail (d), (e) and the directory-named-`project.json` case.

## Limits

- The U10 mutation spec `qa/evidence/mongo-store-u10/mutations.json` entries D3/D4 name DEPLOY.md text that no longer exists; the sidecar tags the node-id and the spec bytes are untouched (D-048). Re-running that old spec would report those two mutations as not applying.
- No real container or Cloud Run run; the script is exercised in the bash sandbox only.
