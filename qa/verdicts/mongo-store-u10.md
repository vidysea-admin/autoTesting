# Verdict - mongo-store-u10 (deploy + docs)

**Checker:** checker-A (fresh, independent; no other verdict read)
**Cycle checked:** 0
**Branch / head:** `feat/mongo-store-u10` @ `ce99efee` (code commit `5eb6b54f`, base `717aa180`)
**Contract:** `qa/contracts/mongo-store.md`, unit U10, criteria M28 and M48
**Verdict: PASS** (M28 met; M48 met for every section D-122 authorizes; one M48 falsifier clause stays OPEN on a HUMAN_GATE, see finding 2)

## Findings

1. **Entrypoint (`docker/entrypoint.sh:42-57, :63-68`) - PASS, no false-quiet found.** I extracted `all_state_on_mongo` verbatim (lines 42-57) and ran 27 cases in real bash 5.2 under `set -euo pipefail`. Quiet only for: global `mongo` AND every listed entry `=mongo` AND an `auth=mongo` entry of its own.
   - warn (correct): empty areas; `projects=mongo` only; STORE=`file`/empty/`Mongo` with `auth=mongo`; `auth=mongo,projects=file` and reversed order; `auth=file`; `auth`; `auth=`; `=mongo`; `authx=mongo`; `credentials=sqlite,auth=mongo`.
   - quiet (correct): `auth=mongo`; `auth=mongo,` (trailing comma); `,auth=mongo,,runs=mongo,`; ` auth = mongo , runs = mongo `; duplicate `auth=mongo,auth=mongo`; `credentials=mongo,auth=mongo`.
   - Divergences from `store_selection()` (`store/mongo_routes.py:235-250`), all on the conservative side: python is last-entry-wins, bash returns on the first non-mongo entry (`auth=file,auth=mongo`, `projects=file,projects=mongo` warn although python would resolve to mongo). `auth=Mongo`, `AUTH=mongo`, `auth=mongo=x`, `;` and inner-space forms all warn; python refuses `Mongo`/`AUTH` at startup (`StoreSelectionError`).
   - Only non-conservative edge: bash strips all inner spaces (`au th=mongo` counts as `auth`) while python only trims ends; python then raises "unknown area" so the process does not start. Harmless, noted.
   - The helper only reads two variables and echoes a fixed string; run with `PATHLYNKS_MONGO_URI` set to a canary, nothing printed it. No `exit` in the function; the empty-array / empty `AUTOTESTER_STORE_AREAS` case survived `set -u`. The script never exited in any of the 27 cases.
   - `UNROUTED` is `{}` (`mongo_routes.py:28`), so global `mongo` routes all 9 areas; `credentials` is the single area for secrets and sessions (`core/env.py:242`, `browser/profiles.py:63`). That meets M28's "credential and session stores are on".
   - WARNING (test gap, low): `tests/test_mongo_deploy_u10.py:106-122` has no lookalike area case (`authx=mongo`, `xauth=mongo`); a mutant that matches `*auth*` would survive. Safe in practice because startup refuses an unknown area, but add one row.
   - WARNING (claim vs code): the quiet notice says "every state area is on Mongo; the data root holds scratch only" from configuration alone. Rows still in the state-bypass baseline (`pyproject.toml` `[tool.autotester.doctor.state-bypass]`, 33 rows now: 17 U11 `.env` presence/read, U5b media, 2 U9 mkdir) and unverified READ-SIDE sites mean files can still be written. This is inside the G1 gate (M52), not a U10 defect, but the notice must not be read as proof; the G1 packet needs the readiness table. U10's manifest has none (the U3d manifest has "Per-area readiness", `qa/manifests/mongo-store-u3d.md:75`); M52 does not list U10 in `judges:`, so not a failure.

2. **Lab Protocol authority for `docs/ARCHITECTURE.md` and `CLAUDE.md` - RULING: authorized, no revert.** `docs/DECISIONS.md:2986` (D-122, status ACTIVE `:2960`) `Changes-authorized` names, verbatim, "Later, under the docs unit, CLAUDE.md Credentials and ARCHITECTURE.md storage and security prose." The edited text is the Security item 1 and the Storage section only (`git diff 717aa180 HEAD -- docs/ARCHITECTURE.md`: hunks at `:102-112` and `:114-125`). D-123 (`:2988`) supersedes only item 4's encryption, and D-122's "Later ... docs unit" clause is not item 4. The docs unit follows U11/U12, whose manifests are `checked-PASS` (u11, u11f, u12, u12f), and U9 is merged (`30db1b7a`). D-120's "once the contract has passed" wording (`:2939`) is therefore not needed. `wc -l docs/ARCHITECTURE.md` = 149 (cap 150). Doctor clean.
   - **Residual, OPEN on a HUMAN_GATE (not a maker defect):** `docs/ARCHITECTURE.md:20` still says "no new DB (D-036)", which M48's falsifier names (`mongo-store.md:372-377`), and the Concept-to-file "Persistence" (`:42`) and "Docker ... local dev only" (`:63`) rows are stale. No DECISIONS entry names the Pipeline or Concept-to-file sections, so the maker correctly did not edit them; proposed text is at `qa/evidence/mongo-store-u10/architecture-proposal.md`. M48 stays open for that clause until Umesh appends a D-entry whose `Changes-authorized` names those rows (or supersedes D-036's wording). I do not FAIL cycle 0 because no maker action can lawfully cure it; failing would only burn a fix cycle. The sweep should hold M48 as "partial, gated".

3. **CLAUDE.md - PASS.** `git diff 717aa180 HEAD -- CLAUDE.md` is two hunks (+15/-5), both inside "Credentials (hard boundary)"; Lab Protocol, Maker-checker, Commands and Design rules untouched. The exact-host claim matches `src/autotester/browser/secrets.py:104-112` (`_host_matches`: "EXACT host match (AT-651, D-087)", case-insensitive, one trailing dot ignored, `include_subdomains` no longer widens). The new Mongo sentence matches D-122/D-123 (plain, IP allowlist, write fence, `browser/db.py` refusal; URI, `AUTOTESTER_APPROVAL_KEY` and provider keys never stored). No hook, `settings.json` or rule file touched. Run `/aios-config-auditor` before the merge commit as the lifecycle requires (CLAUDE.md changed).

4. **M28 vs D-125 - RULING: implementation correct; contract wording needs a checker amendment.** `docker/DEPLOY.md:235` adds `--max-instances 1` to the Cloud Run command; the new section states it stays until `queue`/CAS is on Mongo; the four env names are in the table; fail-closed and plain storage are stated; no URI value appears. The guide keeps the `/data` GCS volume until G1 (D-125, `DECISIONS.md:3028`, later than D-120 and ACTIVE). M28's text "drops the GCS-volume request" and its falsifier "still asks for a GCS volume" (`mongo-store.md:164-167`) conflict with D-125 and with reality (the live service mounts the bucket). Amendment for the contract owner (not made here): "DEPLOY.md keeps the GCS `/data` volume requirement until every area is on Mongo (G1), then states it is no longer needed (D-125)". Criticality is normal, so a non-gated amendment. Claim checks: `STORE_DOWN` text at `ui/error_pages.py:130`; area list matches `mongo_routes.py:25-26`; own-entry rule matches `auth/store.py:92-98`; startup ping `ui/app.py:63-64` -> `validate_store_env` -> `ping_backends`; `/healthz` stays 200 (`ui/routes_live.py:127-135`).
   - WARNING: the guide describes `autotester store migrate` but `src/autotester/cli_store.py` does not exist on this branch (U8 open). Forward reference, disclosed in the manifest (item 6); recheck the command name when U8 merges.
   - WARNING: `core/env.py::storage_warning` (line 146) still feeds the `/admin/users` and `/admin/groups` banner "not persistent" after G1 (manifest item 3). Follow-up code change for G1, outside U10's file list; DEPLOY.md only claims the entrypoint warning is replaced.

5. **`.env.example` - PASS.** Adds `AUTOTESTER_STORE=` and `AUTOTESTER_STORE_AREAS=` (both blank, comment only). The base file has no `AUTOTESTER_STORE` (`git grep AUTOTESTER_STORE 717aa180 -- .env.example` is empty) while `src/` reads both (`auth/store.py:98`, `store/mongo_routes.py:237-238`), so `tests/test_hosting_deploy.py:64` was red on base by construction; now green. Value-free; `test_env_example_holds_no_secret_looking_value` passes.

6. **Mutation wrapper - PASS.** `git diff 717aa180 HEAD --stat -- scripts/mutation_check.py src scripts pyproject.toml uv.lock` is empty. `qa/evidence/mongo-store-u10/run_mutations.py` (33 lines) imports the stock tool, replaces only `mc._sandbox` with a wrapper that calls the stock one and copies in `docker/`, `docs/`, `CLAUDE.md`, `.env.example`, `Dockerfile`; kill logic untouched. Worktree `git status` was clean after my run.

7. **Scope.** U10 changed no `src/` and no dependency (only docs, docker, tests, qa files and `.env.example`). The manifest honestly records that the independent review agent was refused; this verdict is the independent read.

## C5/C6 inbox wording
`qa/feedback-inbox.md` last entry (Status: unfolded) is left untouched. It is a contract amendment for the sweep owner (M48 requires the checker to make it in a separate criticality-gated commit, after U10 PASS). The wording is consistent with D-122/D-123 and the exact-host fact; the C6 Verify note ("no database is the primary store" true only for the file backend) is correct.

## Commands run (worktree `D:/autoTesting/.claude/worktrees/mongo-u10`, `env -u ANTHROPIC_BASE_URL`, `-o addopts=`, 2 files per call)
```
pytest tests/test_mongo_deploy_u10.py tests/test_storage_warning.py              -> 44 passed
pytest tests/test_hosting_deploy.py tests/test_container_entrypoint_behaviour.py -> 18 passed, 1 skipped
pytest tests/test_auth_deploy_files.py tests/test_doctor.py                      -> 43 passed
pytest tests/test_committed_fresh.py tests/test_container_writable_root.py       -> 14 passed
pytest tests/test_container_redaction.py tests/test_container_supervision.py     -> 81 passed, 1 skipped
pytest tests/test_hosting_config.py tests/test_hosting_gaps.py                   -> 44 passed
pytest tests/test_ledger.py tests/test_approval_signing.py                       -> 42 passed
pytest tests/test_container_ci_workflow.py tests/test_env_loading.py             -> 34 passed
uv run ruff check src tests scripts                                              -> All checks passed!
uv run autotester doctor > .work/doctor-u10-checkerA.txt (exit 0)                -> doctor: clean
run_mutations.py qa/evidence/mongo-store-u10/mutations.json --repo .            -> 23/23 mutations killed
bash matrix over all_state_on_mongo (27 cases, set -euo pipefail)                -> results in finding 1; script never exited
```
Not run: full suite and `tests/test_role_port_authz.py` (low-memory rule; 5 known environmental failures). No `.env` value was read or printed.

## Required before the merge / for the sweep
- Run `/aios-config-auditor` on the CLAUDE.md change (finding 3).
- Checker amendment of M28 for D-125 (finding 4); fold C5/C6 per the inbox entry.
- HUMAN_GATE: Umesh D-entry naming ARCHITECTURE.md Pipeline line 20 and the two Concept-to-file rows, then apply `architecture-proposal.md` (finding 2); M48 closes only then.
- Optional: add one lookalike-area row to the entrypoint test (finding 1).
