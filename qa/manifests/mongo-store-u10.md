# Manifest - mongo-store-u10

**Status:** checked-PASS (cycle 0, checker A 815d93f1; config audit A 100)
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE), unit U10 (docs and deploy). **Criticality:** normal (U10 row has no dual mark). No `src/` code, no new `src/` module, no dependency.
**Authority:** D-120 and D-122 (`docs/DECISIONS.md:2939`, `:2986`: "ARCHITECTURE.md storage and security prose" and "CLAUDE.md Credentials" may change in the docs unit), D-123 (plain storage), D-125 (GCS `/data` volume stays until Mongo replaces it). See "Authority checks and judgement calls".
Round cap: normal unit, D-014 cap of 2 fix cycles applies.
**Branch:** `feat/mongo-store-u10`, cut from master `717aa180`. Not merged to master, not pushed.
**Base SHA:** `717aa180`
**Code SHA:** `5eb6b54f52878a515fd0d9f858e405bef8ec1282` (the only code commit; this manifest and the final evidence files are a second commit on top of it)
**Criteria judged by U10:** M28, M48 (`docs/ARCHITECTURE.md` and `CLAUDE.md` prose only; the `core-invariants.md` C5/C6 amendment is the checker's, wording delivered below).

## What changed

| File | Kind | Change |
|---|---|---|
| `docker/DEPLOY.md` | E in place | `--max-instances 1` added to the Cloud Run command (`:235`); Persistent-storage paragraph says the volume stays until every area is on Mongo (`:241`); new `## State store on MongoDB (D-120 to D-123)` section (`:254-292`): env-name table (`:261-264`), `auth` own entry, flip order and G1 gate, `--max-instances 1` until `queue`/CAS is on Mongo, GCS volume required until G1 (D-125), fail closed, plain storage |
| `docker/entrypoint.sh` | E in place | `all_state_on_mongo()` (`:42-57`) and its use in `warn_if_ephemeral` (`:63-68`): the "storage is not persistent" warning is replaced by a one-line notice only when `AUTOTESTER_STORE=mongo`, no `AUTOTESTER_STORE_AREAS` entry sends an area to a non-mongo backend, and `auth=mongo` is present as its own entry. Every other combination keeps the warning (conservative). Still never exits. |
| `.env.example` | E in place | documents `AUTOTESTER_STORE` and `AUTOTESTER_STORE_AREAS` (blank = files). Needed because `tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads` was **already red on master** (it scans `src/` and U2 added the two names there). Not in the task's file list; flagged below. |
| `CLAUDE.md` | E in place | Credentials section, see "CLAUDE.md lines changed" |
| `docs/ARCHITECTURE.md` | E in place | Security item 1 (`:105-109`) and the whole Storage section (`:115-125`); 149 lines (cap 150, `ledger/render.py:22`) |
| `tests/test_mongo_deploy_u10.py` | N (test) | 26 tests: guide names and areas pinned to the code (`MONGO_URI_ENV`, `mongo_routes.AREAS`), entrypoint behaviour matrix run in real bash, CLAUDE.md and ARCHITECTURE.md prose lints |
| `qa/evidence/mongo-store-u10/` | N | `mutations.json`, `run_mutations.py`, `mutation-run.txt`, `verify.txt`, `architecture-proposal.md` |
| `qa/feedback-inbox.md` | appended | proposed wording for `core-invariants.md` C5 and C6 (checker amendment; I did not touch the contract) |

## CLAUDE.md lines changed (for the config audit)

Only the "Credentials (hard boundary)" section. Diff against `717aa180`:
- `:57-66` (was `:57-59`): bullet 1 rewritten. Values live in the repo-root `.env` (file backend, local/test default); with the `credentials` store area on `mongo` (D-122, D-123) UI-entered values and `storage_state` sessions live in `secrets` / `browser_sessions`, stored plain, no second copy in `.env`; protection named; the Mongo URI, `AUTOTESTER_APPROVAL_KEY` and provider keys are never put in the store. "no `projects/<slug>/.env`" and the key-namespacing sentence kept (`:67-69`).
- `:73-76` (was `:65-66`): the `_host_matches` note corrected from "suffix match" to "exact-host match (AT-651, D-087)" (source: `src/autotester/browser/secrets.py:104-112`).
- No other CLAUDE.md line changed (`git diff 717aa180 HEAD -- CLAUDE.md` is these two hunks; +15/-5).
- Not changed and worth the auditor's eye: Lab Protocol, Maker-checker and Commands blocks are untouched; no hook, `settings.json` or rule file touched.

## Criteria map

| Crit | Where | Test (falsifier it kills) |
|---|---|---|
| M28 DEPLOY.md note | `DEPLOY.md:274-277` (`--max-instances 1` stays until `queue`/CAS on Mongo), `:235` (flag in the command), `:261-264` (the four env names), `:278-281` (volume stays required until G1, D-125) | `test_cloud_run_command_pins_one_instance_and_the_guide_says_until_when`, `test_guide_names_every_switch_the_code_reads`, `test_guide_keeps_the_gcs_volume_required_until_g1_and_cites_d125`, `test_guide_lists_every_store_area_the_code_routes_in_the_areas_row`, `test_guide_says_auth_moves_only_with_its_own_entry`, `test_guide_states_fail_closed_and_plain_storage_and_never_a_uri_value` |
| M28 entrypoint stops claiming state is lost only when every area is mongo and credentials/sessions are on | `entrypoint.sh:42-57, :63-68` (`credentials` is one area for secrets and sessions, `browser/profiles.py:66`, `core/env.py:242`) | `test_entrypoint_still_warns_while_any_area_is_on_files` (9 cases), `test_entrypoint_is_quiet_once_every_area_is_on_mongo` (5 cases), `test_entrypoint_never_prints_the_uri`, `test_entrypoint_syntax_is_valid_and_the_helper_cannot_exit`; existing `tests/test_storage_warning.py` entrypoint tests unchanged and green |
| M48 prose follows the contract | `ARCHITECTURE.md:105-109, :115-125`; `CLAUDE.md:57-66, :73-76` | `test_claude_md_*` (2), `test_architecture_security_and_storage_name_the_mongo_backend_and_stay_in_budget` |
| M48 C5/C6 amendment | not edited; wording in `qa/feedback-inbox.md` (last entry, Status unfolded) | n/a (checker) |

## Authority checks and judgement calls (read these)

1. **ARCHITECTURE.md edit authority.** `grep Changes-authorized docs/DECISIONS.md` names the storage and security sections only in D-120 (`:2939`, "once the contract has passed") and D-122 (`:2986`, "Later, under the docs unit"). U8 (migrate, dual) is still open, so "the contract has passed" is not literally true; I relied on D-122's text (docs unit after U11/U12, which are merged with U11f/U12f). If the checker reads D-120's condition as binding, revert the two hunks; nothing else depends on them. **Not edited** (no entry names them): the Pipeline line "no new DB (D-036)" (M48 names this phrase as a falsifier), the Concept-to-file "Persistence" row and the "Docker ... local dev only" row. Proposed replacement text is in `qa/evidence/mongo-store-u10/architecture-proposal.md`. Consequence: **M48's falsifier "prose still says no new DB (D-036)" is still true after U10 until Umesh authorizes the Pipeline section.** I flag it rather than work around it.
2. **M28 vs D-125 conflict.** M28 says DEPLOY.md "drops the GCS-volume request (D-120 Result)" and its falsifier is "still asks for a GCS volume". D-125 (2026-10-30, later than D-120) mounts the bucket now, and the task brief says the volume stays required until G1. I followed D-125/the brief: the guide says the volume stays required until every area is on Mongo, then is not needed. The checker should decide whether M28's wording needs a checker amendment for this.
3. **Admin banner not changed.** `core/env.py::storage_warning` (and the `/admin/users`, `/admin/groups` banner it feeds, `tests/test_storage_warning.py`) still reports "not persistent" on a hosted server even after every area is on Mongo. Fixing that is a code change in `core/env.py` (U11's file), outside U10's scope (docs/deploy). The DEPLOY.md text says only the entrypoint warning is replaced. Follow-up for the checker/G1.
4. **`all_state_on_mongo` is bash, a second reading of `store_selection()`.** It is deliberately conservative (only "quiet" when it can prove all areas are mongo) and cannot drift into hiding a real problem; the Python (`mongo_routes.py:235-250`, `auth/store.py:92-98`) stays the source of truth and still refuses a bad value at startup. It does not require `PATHLYNKS_MONGO_URI` to be set (the value may be in `/data/.env`, which the script never reads); startup ping (M27) refuses a missing URI.
5. **`.env.example`** edit is outside the stated file list, justified above (pre-existing red test).
6. **`autotester store migrate` is described in DEPLOY.md** as the migration step (U8's CLI). U8 is a sibling worktree and not on master; the guide says what it does per the contract (dry run unless `--apply`). If U8 renames the command, this paragraph needs a one-word edit.
7. **Agent review.** The `senior-software-engineer` review dispatch was refused by the PreToolUse hook ("Compact agent handoff required") and the task says not to dispatch checkers, so no independent review ran. I self-checked the bash under `set -euo pipefail` with an empty array, empty `AUTOTESTER_STORE_AREAS`, spaces and empty entries (outputs in the session, behaviour pinned by the tests). The checker is the independent read.
8. **No `shellcheck`** on this host (`which shellcheck` empty); `bash -n docker/entrypoint.sh` is clean and is a test.

## Verify (run in `D:/autoTesting/.claude/worktrees/mongo-u10`, `-o addopts=`, 2 files per call, `env -u ANTHROPIC_BASE_URL`)

```
pytest tests/test_mongo_deploy_u10.py tests/test_storage_warning.py          -> 44 passed
pytest tests/test_hosting_deploy.py tests/test_container_entrypoint_behaviour.py -> 18 passed, 1 skipped
pytest tests/test_auth_deploy_files.py tests/test_doctor.py                  -> 43 passed
pytest tests/test_committed_fresh.py tests/test_container_ci_workflow.py     -> 33 passed
pytest tests/test_container_redaction.py tests/test_container_supervision.py -> 81 passed, 1 skipped
pytest tests/test_container_writable_root.py tests/test_env_loading.py       -> 15 passed
pytest tests/test_hosting_config.py tests/test_hosting_gaps.py               -> 44 passed
pytest tests/test_ledger.py tests/test_approval_signing.py                   -> 42 passed
ruff check src tests scripts                                                 -> All checks passed!
autotester doctor (redirected to .work/doctor-u10.txt, exit 0)               -> doctor: clean (only non-blocking D-087 advisories)
python qa/evidence/mongo-store-u10/run_mutations.py qa/evidence/mongo-store-u10/mutations.json --repo . -> 23/23 mutations killed
```

Full outputs: `qa/evidence/mongo-store-u10/verify.txt`, `mutation-run.txt`. Not run: the full suite (low-memory rule) and `tests/test_role_port_authz.py` (5 known environmental failures, unrelated). Red-first: before the guide and entrypoint edits the new file failed at collection (no `## State store on MongoDB` heading) and `test_guide_says_auth_moves_only_with_its_own_entry` failed once on wording, fixed in the guide.

## Mutation evidence

`scripts/mutation_check.py` copies only `scripts/ tests/ src/` into its sandbox, so docs and shell mutants cannot be reached with it as shipped. `qa/evidence/mongo-store-u10/run_mutations.py` imports that tool unchanged and widens only the sandbox copy (`docker/`, `docs/`, `CLAUDE.md`, `.env.example`, `Dockerfile`); the kill logic is the stock one (named test must fail, red baseline refused). 23 mutants: E1-E9 entrypoint (global flag, area pinned to file, missing auth entry, wrong area name, blanks, empty entry, quiet path never taken, every entry read as mongo, notice text), D1-D8 DEPLOY.md, C1-C3 CLAUDE.md, A1-A3 ARCHITECTURE.md. First run killed 22/23; E9 survived because the old assertion `"Mongo" in out` matched "MongoDB" elsewhere in the message; the assertion was tightened to `"every state area is on Mongo"` and the whole spec rerun: **23/23 killed**.

## Things the checker should look at

- Whether the D-120/D-122 reading in item 1 is acceptable, and whether Umesh should authorize the Pipeline/Concept-to-file edits (M48 falsifier).
- The M28/D-125 wording conflict (item 2).
- That the new DEPLOY.md text claims nothing the code does not do: `STORE_DOWN` text `ui/error_pages.py:130`, area list `store/mongo_routes.py:25`, own-entry rule `auth/store.py:92-98`, flip order from the contract's wave table (G1 row), `/healthz` stays 200 and start-up refusal from M26/M27 (U9).
- `CLAUDE.md` diff for the config audit (section above).
