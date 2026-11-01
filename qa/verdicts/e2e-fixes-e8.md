# Verdict - e2e-fixes-e8 (E5 hardening: projects guard + DEPLOY.md)

**Cycle checked:** 0
**Verdict:** PASS (2 warnings, none blocking)
**Checker:** fresh, independent. Code under test: branch `feat/e2e-e8` at `e2c5b1ea` (base `6eb21a54`). Contract: `qa/contracts/e2e-fixes.md` E8.1-E8.3. Manifest: `qa/manifests/e2e-fixes-e8.md`.

I re-ran everything below myself (TMP/TEMP and `--basetemp` under `.work`, `env -u ANTHROPIC_BASE_URL`, two test files per call at most, no full suite). I did not read any other checker's verdict. No `.env` value was read or printed; the only URI used is the canary `mongodb://canary-user:canary-pass@h/`. The worktree was byte-identical to `e2c5b1ea` before and after my mutations (cmp against saved copies; `git status` clean).

## Commands and outputs

| Command | Result |
|---|---|
| `pytest tests/test_container_entrypoint_behaviour.py tests/test_storage_warning.py -o addopts=` | 59 passed, 1 skipped (the pre-existing Windows non-executable-python case) |
| `pytest tests/test_mongo_deploy_u10.py -o addopts=` | 32 passed |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor > .work/chk_doctor.txt` | `doctor: clean` (rc 0; only advisory decision-citation lines) |
| `git diff 6eb21a54..HEAD --name-only` filtered to `src/` and `qa/contracts/` | empty (no code, no contract edit) |

## E8.1 (docker/entrypoint.sh)

- The guard is `docker/entrypoint.sh:60-66` (loop at :61): `for proj in "$root"/projects/*/project.json; do if [ -f "$proj" ]` then one `echo` and `return 0`. `root` is `${AUTOTESTER_ROOT:-/app}`, the same expression as the auth path (`:55`). It sits after the blank-URI (`:50`), operator-choice (`:51-54`) and auth-file (`:56-59`) checks. Presence only (a glob and `-f`); no `cat`, no `ls`; the function still ends `return 0` and is called `|| true` (`:72`).
- The message prints the data root path, "Mongo not auto-selected", "(migrate them first, docker/DEPLOY.md)". It carries no slug, no URI, no file content. I ran the extracted function directly in a sandbox with slug `secretslug` and the canary URI: output was one line naming only the root; `AUTOTESTER_STORE` and `AUTOTESTER_STORE_AREAS` stayed unset; rc 0. With an auth file AND a project: exactly one line (the SQLite one, first match), both unset. With no `projects/` directory: both exported, rc 0. With a whitespace-only URI: rc 0, nothing exported.
- Cases (a)-(h), each in `tests/test_container_entrypoint_behaviour.py:230-299`: (a) and (f) `test_e8_a_project_file_blocks_the_selection_with_one_line[zeta|with space]` (one line, both vars unset); (b) `test_e8_auth_file_and_project_together_print_exactly_one_line`; (c)(d)(e)(g) `test_e8_only_a_direct_project_json_counts[empty-projects|slug-dir-only|too-deep|wrong-level|no-projects-dir]`, each asserting the nine `<area>=mongo` items against `store.mongo_routes.AREAS` read from the module; an extra "directory named project.json" case; (h) `_no_leak` in every case plus `test_e8_the_real_script_keeps_files_for_a_project_and_leaks_nothing` (real script, stub-recorded argv, `SEEN=[]`). All pass.

### Mutations (I re-ran each; restored and cmp'd after every one)

| Mutation | Result |
|---|---|
| M1 delete the project loop (`entrypoint.sh`) | 3 failed: both (a)/(f) params and the real-script test |
| M2 `-d projects/*` instead of `projects/*/project.json` | 3 failed: `slug-dir-only`, `too-deep`, directory-named-`project.json` (the empty-`projects/` case passes because the literal glob is not a directory; correct, not a hole) |
| M3 print the matched path in the line | 2 failed: the `zeta` param and the real-script test (see W1) |
| M4 auth branch no longer returns (two lines) | 1 failed: the (b) test |
| DEPLOY.md: delete each of the five new paragraphs | each kills its own pin(s): entrypoint-selects -> 2 failed; fresh-root -> 2 failed; bad-URI -> 1 failed; escape-hatch -> 2 failed; first-admin -> 1 failed |
| DEPLOY.md: append `mongodb+srv://u:p@h/db` | 1 failed (`test_guide_states_fail_closed_and_plain_storage_and_never_a_uri_value`, the `:72` check, verbatim) |
| DEPLOY.md: reword sentence (f) | 1 failed (the (f) pin) |

## E8.2 sentences against the code (docker/DEPLOY.md:254-295)

- (a) both variables, all nine areas, `auth=mongo` and `credentials=mongo`, "the operator does not set them": true against `entrypoint.sh:67-68`; the nine-area list equals `AREAS` (pinned by the passing E5.1 test).
- (b) fresh data root only; store variable set, SQLite auth file, or `projects/*/project.json` each keep files with one line; migrate path `autotester store migrate`, dry run unless `--apply`: true against `entrypoint.sh:50-66` and `cli_store.py:6-7`. G1 wording is now "the first `--apply` and every flip of existing data".
- (c) a wrong or unreachable URI stops start-up, no file fallback: true. `ui/app.py:66` runs `validate_store_env()` in the lifespan, which is `store/filestore.py:152-154` -> `ping_backends` (`store/mongo_routes.py:253-264`), re-raising a `StoreDown` with fixed text. The Cloud Run clause ("a revision that fails to start does not take traffic, so the previous revision keeps serving") is platform behaviour, not checkable in code or here; accepted as stated by the contract.
- (d) `AUTOTESTER_STORE=file` in the process environment turns selection off: true, `entrypoint.sh:51-54` (a set value, even `file`, returns before any export).
- (e) `AUTOTESTER_FIRST_ADMIN_EMAIL` first: true. `auth/config.py:23` defines `FIRST_ADMIN_ENV`; `auth/accounts.py:_becomes_first_admin` (about `:44-53`) returns False on a public-facing server when unset (D-074 (d)); `cli_auth.py:21` is `bootstrap-admin`.
- (f) data-root `.env` store choice does not beat the platform URI: true. The loader guard is `if not key or not value or os.environ.get(key): continue` at `src/autotester/core/env.py:213` (the contract's `:188-189` is now the docstring saying existing variables win; the maker's correction is right). The entrypoint exports `AUTOTESTER_STORE=mongo` before Python starts, so a `.env` `AUTOTESTER_STORE=file` is skipped. The sentence is scoped to "when the URI comes from the platform environment", which is also true (the entrypoint reads only the process environment).
- Reworded: "A fully flipped service sets both" is gone; "Flipping is a human gate (G1)" is now the migration path only; "volume stays required until G1" is "while any area is on files" in both **Persistent storage** (`:241`) and the MONGO section; D-125 and `scratch only` are kept. `grep` for `until G1|fully flipped|G1 is complete` finds none; `grep` for `mongodb://` or `mongodb+srv` finds none.
- Pins: the two old assertions removed in `tests/test_mongo_deploy_u10.py` each have a replacement for the same fact (`auth=mongo` plus "moves only with its own entry ... global value"; the volume is now pinned in MONGO and in CLOUD_RUN). `--max-instances 1`/CAS, D-125, G1, fail-closed, "plain" and the `mongodb(+srv)://...@` absence check are untouched.

## E8.3

`git diff --numstat 6eb21a54..HEAD` on the two test files: `tests/test_container_entrypoint_behaviour.py` +72/-0, `tests/test_storage_warning.py` absent (unchanged). The E5.1-E5.3 cases are unmodified and pass. `all_state_on_mongo` and `warn_if_ephemeral` are not in the diff (only `select_mongo_store` plus a comment changed in `entrypoint.sh`).

## D-048 sidecar (`qa/evidence/mongo-store-u10/mutations.stale.json`)

Legitimate. Same shape as the existing `qa/evidence/mongo-store-u6bf/mutations.stale.json`. It tags exactly the one node id that vanished (`..._required_until_g1_and_cites_d125`), `moved_to` resolves to the renamed test (which pins the same property: the GCS volume stays required, with D-125), and the spec `mutations.json` is byte-unchanged (not in the diff). `evidence_specs.py:check_stale_evidence_specs` accepts it and doctor is clean. Repo hygiene: the 299-line test file is under the 300 cap.

## Warnings (non-blocking)

- W1: `_no_leak` (test file `:243-245`) greps only for the slug `zeta` and "canary". The `with space` param therefore cannot catch a slug leak (under my M3 variant it passed, whereas the manifest's `mutation-run.txt` says M3 failed it too). The mechanism is still covered by the `zeta` param and the real-script test, so the contract hint (print the slug -> (h) fails) holds. Consider adding the second slug to `_no_leak`.
- W2: the U10 spec `qa/evidence/mongo-store-u10/mutations.json` mutation D4 (`guide drops the own auth entry`) now names DEPLOY.md text that no longer exists, like D3, but its kill node id still resolves (that test name was kept), so doctor cannot flag it and the sidecar cannot tag it. Re-running that old spec would report D3 and D4 as not applying. The manifest's "Limits" mentions this; it is a known cosmetic debt, not a defect in E8.

## Out of scope / not verified

No real container or Cloud Run run (sandbox only, as the manifest says). The full suite was not run (memory). Nothing was pushed or merged; push is held per D-130.
